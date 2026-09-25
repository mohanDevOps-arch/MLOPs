"""
MLOps sessions — environment check.

Run from inside your activated virtual environment:
    python verify_setup.py

It checks Python + packages, the CLI tools, then does a 20-second
end-to-end smoke test: train a tiny model, log it to MLflow, register it,
and build an Evidently drift report. Nothing leaves your machine.
"""
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("DO_NOT_TRACK", "true")

OK, WARN, FAIL = "  [OK]  ", "  [WARN]", "  [FAIL]"
problems = []


def section(title):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------- Python
section("Python")
v = sys.version_info
if (v.major, v.minor) >= (3, 11):
    print(f"{OK} Python {v.major}.{v.minor}.{v.micro}")
else:
    print(f"{FAIL} Python {v.major}.{v.minor} found — need 3.11 or 3.12")
    problems.append("python")

if sys.prefix == sys.base_prefix:
    print(f"{WARN} Not running inside a virtual environment (activate .venv first)")

# ---------------------------------------------------------------- Packages
section("Python packages")
packages = {
    "mlflow": "mlflow",
    "dvc": "dvc",
    "evidently": "evidently",
    "scikit-learn": "sklearn",
    "pandas": "pandas",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "prometheus-client": "prometheus_client",
}
for name, module in packages.items():
    try:
        mod = importlib.import_module(module)
        print(f"{OK} {name:<18} {getattr(mod, '__version__', 'installed')}")
    except ImportError:
        print(f"{FAIL} {name:<18} missing  ->  pip install -r requirements.txt")
        problems.append(name)

for name, module in {"boto3": "boto3", "sagemaker": "sagemaker"}.items():
    try:
        mod = importlib.import_module(module)
        print(f"{OK} {name:<18} {getattr(mod, '__version__', 'installed')} (optional)")
    except ImportError:
        print(f"{WARN} {name:<18} not installed (optional, only for SageMaker demo)")

# ---------------------------------------------------------------- CLI tools
section("Command-line tools")
tools = [
    ("git", ["git", "--version"], True),
    ("docker", ["docker", "version", "--format", "{{.Server.Version}}"], True),
    ("kubectl", ["kubectl", "version", "--client"], True),
    ("kind", ["kind", "version"], True),
    ("dvc", ["dvc", "--version"], True),
    ("aws", ["aws", "--version"], False),
]
venv_bin = os.path.join(sys.prefix, "Scripts" if os.name == "nt" else "bin")
search_path = venv_bin + os.pathsep + os.environ.get("PATH", "")
for name, cmd, required in tools:
    exe = shutil.which(cmd[0], path=search_path)
    if exe is None:
        tag = FAIL if required else WARN
        print(f"{tag} {name:<8} not found on PATH" + ("" if required else " (optional)"))
        if required:
            problems.append(name)
        continue
    try:
        out = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=20)
        text = (out.stdout or out.stderr).strip().splitlines()
        first = text[0] if text else ""
        if out.returncode != 0 and name == "docker":
            print(f"{FAIL} docker   installed but the daemon is not running (start Docker Desktop)")
            problems.append("docker-daemon")
        else:
            print(f"{OK} {name:<8} {first}")
    except Exception as exc:  # noqa: BLE001
        print(f"{WARN} {name:<8} could not run: {exc}")

# ---------------------------------------------------------------- Smoke test
section("Smoke test: train -> track -> register -> drift report")
if any(p in problems for p in ("mlflow", "scikit-learn", "pandas", "evidently")):
    print(f"{FAIL} skipped — fix the missing packages above first")
else:
    import warnings
    import logging

    warnings.filterwarnings("ignore")
    logging.getLogger("mlflow").setLevel(logging.ERROR)
    logging.getLogger("alembic").setLevel(logging.ERROR)

    import mlflow
    import pandas as pd
    from sklearn.datasets import load_iris
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    work = tempfile.mkdtemp(prefix="mlops-check-")
    try:
        mlflow.set_tracking_uri("sqlite:///" + os.path.join(work, "mlflow.db").replace("\\", "/"))
        exp_id = mlflow.create_experiment(
            "setup-check", artifact_location=Path(work, "artifacts").as_uri()
        )
        mlflow.set_experiment(experiment_id=exp_id)

        X, y = load_iris(return_X_y=True, as_frame=True)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=42)

        with mlflow.start_run() as run:
            model = LogisticRegression(max_iter=200).fit(X_tr, y_tr)
            acc = accuracy_score(y_te, model.predict(X_te))
            mlflow.log_param("max_iter", 200)
            mlflow.log_metric("accuracy", acc)
            mlflow.sklearn.log_model(
                model, name="model", registered_model_name="iris-setup-check",
                input_example=X_te.head(2),
            )
        print(f"{OK} MLflow run logged (accuracy={acc:.2f}) and model registered")

        loaded = mlflow.pyfunc.load_model("models:/iris-setup-check/1")
        loaded.predict(X_te.head(3))
        print(f"{OK} Model reloaded from the registry and served a prediction")

        from evidently import Report
        from evidently.presets import DataDriftPreset

        drifted = X_te.copy()
        drifted["petal length (cm)"] = drifted["petal length (cm)"] * 1.8
        snapshot = Report([DataDriftPreset()]).run(reference_data=X_tr, current_data=drifted)
        html = os.path.join(work, "drift.html")
        snapshot.save_html(html)
        print(f"{OK} Evidently drift report generated")
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} smoke test failed: {type(exc).__name__}: {exc}")
        problems.append("smoke-test")
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ---------------------------------------------------------------- Summary
section("Result")
if problems:
    print("Fix these before the session: " + ", ".join(sorted(set(problems))))
    print("See 00_Prerequisites_and_Installation.md -> Troubleshooting.")
    sys.exit(1)
print("All good — you're ready for the MLOps sessions.")
