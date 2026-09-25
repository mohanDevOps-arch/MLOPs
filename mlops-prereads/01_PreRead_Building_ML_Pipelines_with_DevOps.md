# Pre-Read — Session 1: Building ML Pipelines with DevOps Practices

**Program:** PPMCAD — Multicloud Architecture in DevOps · **Module:** MLOps
**Reading time:** about 30 minutes
**Before this:** finish `00_Prerequisites_and_Installation.md`

---

## What the session covers

1. Build end-to-end ML pipelines using tools like **MLflow**, **Kubeflow** or **Vertex AI Pipelines**.
2. Automate data preprocessing, training, evaluation and versioning with **Git** and **CI/CD** tools.
3. Manage **experiment tracking**, **artifact storage** and **reproducibility**.

By the end of the session you should be able to take a notebook-style training script and turn it into a versioned, tracked, automatically retrained pipeline, using the DevOps habits you already have.

---

## 1. Why ML needs its own flavour of DevOps

In a normal application, **code** decides behaviour. Change the code, rebuild, redeploy.

In an ML system, behaviour comes from three things that change independently:

```
          ┌──────────┐
          │   CODE   │  training script, feature logic, serving API
          └────┬─────┘
               │
┌──────────┐   ▼   ┌───────────┐
│   DATA   │──────▶│   MODEL   │  weights / artifact produced by training
└──────────┘       └───────────┘
 changes daily       changes whenever code OR data changes
```

So a model can get worse **without anyone touching the code**, simply because the data changed. That one fact explains almost every MLOps practice:

| DevOps habit | MLOps equivalent |
|---|---|
| Version the code in Git | Version code **and data and models** (Git + DVC + model registry) |
| CI: build and test on every commit | CI also **validates data** and **tests model quality** |
| CD: deploy a build artifact | CD deploys a **registered, approved model version** |
| Monitoring: CPU, latency, errors | Also monitor **prediction quality and data drift** |
| Rollback to the previous release | Roll back to the previous **model version** |
| Reproducible builds | Reproducible **training runs** (same data + code + params = same model) |

**MLOps = DevOps + data versioning + experiment tracking + continuous training + model monitoring.**

---

## 2. The ML lifecycle in 60 seconds

For DevOps engineers new to ML, here is the whole lifecycle:

| Stage | What happens | Output |
|---|---|---|
| **Ingest** | Pull raw data from a DB, S3 bucket or API | `data/raw/` |
| **Validate** | Check schema, nulls, ranges. Fail fast on bad data. | pass/fail |
| **Preprocess / feature engineering** | Clean data and turn raw columns into model inputs (scale numbers, encode categories) | `data/processed/` |
| **Split** | Train set (the model learns from it) and test set (the model is graded on it) | train/test files |
| **Train** | Fit an algorithm with chosen **hyperparameters** (settings like `max_depth`, `learning_rate`) | model file (`model.pkl`) |
| **Evaluate** | Score on the test set: accuracy, precision, recall, F1, RMSE… | `metrics.json` |
| **Register** | If good enough, store the model as a numbered version in a registry | `model v7` |
| **Deploy** | Serve predictions: API, batch job or edge | endpoint |
| **Monitor** | Watch latency, errors, **drift** and quality, and retrain when needed | alerts, retrain trigger |

**Useful vocabulary**

- **Feature:** an input column the model uses (e.g. `tenure_months`).
- **Label / target:** what we want to predict (e.g. `will_churn`).
- **Hyperparameter:** a setting chosen *before* training (`n_estimators=100`).
- **Parameter / weights:** what the model *learns* during training.
- **Metric:** a number that says how good the model is (`accuracy=0.93`).
- **Artifact:** any file a run produces: the model, plots, reports, the preprocessor.
- **Experiment:** a group of related training runs you want to compare.

Sessions 1 and 2 split this lifecycle between them: **Session 1 covers Ingest → Register**, and **Session 2 covers Deploy → Monitor, plus Governance**.

---

## 3. MLOps maturity: where are you?

Google's widely used MLOps maturity model describes three levels. It's a useful map:

| Level | What it looks like | Pain |
|---|---|---|
| **0: Manual** | A data scientist trains in a notebook, emails `model.pkl`, and an engineer deploys it by hand | Not reproducible, rare releases, nobody knows which data trained which model |
| **1: Pipeline automation** | Training is a scripted pipeline, and new data triggers **continuous training (CT)**. Metadata and models are tracked. | Pipeline code itself is still deployed manually |
| **2: CI/CD pipeline automation** | Pipeline code goes through CI/CD. Tests, builds and deploys of the *pipeline itself* are automated. | Needs mature tooling and culture |

In Session 1 you'll take a Level-0 script to **Level 1**, and wire it into CI so it touches **Level 2**.

---

## 4. Anatomy of an ML pipeline

A pipeline is a **DAG (directed acyclic graph)** of steps. Each step has inputs, outputs and a command, just like CI stages.

```
 ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐
 │  ingest  │──▶│ validate  │──▶│ preprocess │──▶│  train  │──▶│ evaluate │──▶│ register │
 └──────────┘   └───────────┘   └────────────┘   └─────────┘   └────┬─────┘   └──────────┘
                                                                     │ metric below threshold?
                                                                     ▼
                                                                  FAIL the pipeline (quality gate)
```

**Design rules**

1. **One step, one responsibility, one script.** `preprocess.py`, `train.py`, `evaluate.py`, never one giant notebook.
2. **Steps talk through files or artifacts, not global variables.** That makes each step cacheable and re-runnable.
3. **Parameters live in a config file** (`params.yaml`), not hard-coded, so changes are visible in Git diffs.
4. **Every step is deterministic.** Fix random seeds (`random_state=42`) and pin library versions.
5. **Quality gate.** Evaluate fails the pipeline if the metric is below a threshold. It's the ML version of a failing unit test.

A typical repo layout:

```
churn-model/
├── data/
│   ├── raw/                 # tracked by DVC, not Git
│   └── processed/           # produced by the pipeline
├── src/
│   ├── preprocess.py
│   ├── train.py
│   └── evaluate.py
├── params.yaml              # hyperparameters + thresholds
├── dvc.yaml                 # pipeline definition (DAG)
├── dvc.lock                 # exact hashes of every input/output (auto-generated)
├── requirements.txt
└── .github/workflows/train.yml
```

---

## 5. Tooling landscape: MLflow vs Kubeflow vs Vertex AI

The session outline names three families of tools. They overlap, but each has a sweet spot:

| | **MLflow** | **Kubeflow Pipelines (KFP)** | **Vertex AI Pipelines** |
|---|---|---|---|
| What it is | Open-source tracking, model registry, packaging and serving | Open-source pipeline orchestrator **on Kubernetes** | **Managed** Google Cloud service that runs KFP-format pipelines |
| Runs where | Laptop, VM, any cloud (managed on Databricks, SageMaker, Azure ML) | Your K8s cluster | GCP only, serverless |
| Strength | Experiment tracking and model registry, simple to start | Each step runs as a container, scales on K8s, strong for large teams | No cluster to manage, integrated with GCP data services |
| Weakness | Not a heavy-duty orchestrator by itself | Heavy to install and operate | Vendor lock-in, costs per run |
| Pipeline defined in | Python + MLflow Projects, or pair it with DVC, Airflow or GitHub Actions | Python SDK (`kfp`), compiled to YAML | Same `kfp` SDK |
| AWS equivalent | SageMaker **Managed MLflow** | — | **SageMaker Pipelines** |

**How they fit together in practice:** MLflow is often *combined* with an orchestrator. Kubeflow or Vertex runs the steps, and MLflow records what each run did. In this course we use:

- **DVC** to define and cache the pipeline DAG locally,
- **MLflow** for tracking and the registry,
- **GitHub Actions** as the CI/CD orchestrator.

The same concepts carry over directly to Kubeflow and Vertex, and the instructor will show the equivalent.

**A Kubeflow / Vertex pipeline looks like this** (read-only, just to recognise the style):

```python
from kfp import dsl

@dsl.component(base_image="python:3.12-slim", packages_to_install=["scikit-learn", "pandas"])
def train(data_path: str, n_estimators: int) -> float:
    ...                     # each component runs in its own container
    return accuracy

@dsl.pipeline(name="churn-training")
def churn_pipeline(n_estimators: int = 100):
    prep = preprocess(raw_path="gs://bucket/raw.csv")
    trn  = train(data_path=prep.output, n_estimators=n_estimators)
```

Notice the idea: **every step is a container**, and outputs pass from step to step. It is the same DAG as in §4.

---

## 6. Versioning data and models with Git + DVC

**The problem:** Git is built for small text files. A 2 GB dataset or a 500 MB model in Git bloats the repo and slows down every clone.

**DVC (Data Version Control)** fixes this by storing the big file in a **remote** (S3, GCS, Azure Blob, SSH or a local folder) and committing only a tiny **pointer file** to Git:

```
data/raw/customers.csv        ← real 2 GB file, ignored by Git, pushed to S3 by DVC
data/raw/customers.csv.dvc    ← 5-line pointer with an MD5 hash, committed to Git
```

```yaml
# customers.csv.dvc
outs:
- md5: 3c2a6e0f4b1d9e8a...
  size: 2147483648
  path: customers.csv
```

**Core commands** (they mirror Git on purpose):

| Command | Git analogy | What it does |
|---|---|---|
| `dvc init` | `git init` | Set up DVC inside a Git repo |
| `dvc add data/raw/customers.csv` | `git add` | Hash the file, create the `.dvc` pointer, add the file to `.gitignore` |
| `dvc remote add -d store s3://my-bucket/dvc` | `git remote add` | Where the big files live |
| `dvc push` / `dvc pull` | `git push` / `git pull` | Upload / download the big files |
| `dvc repro` | `make` | Re-run only the pipeline stages whose inputs changed |
| `dvc exp run -S train.n_estimators=200` | — | Run an experiment with a changed parameter |
| `git checkout v1.0 && dvc checkout` | `git checkout` | Restore **the exact data and model** of release v1.0 |

**Pipelines in DVC.** `dvc.yaml` declares the DAG:

```yaml
stages:
  preprocess:
    cmd: python src/preprocess.py
    deps: [src/preprocess.py, data/raw/customers.csv]
    outs: [data/processed]
  train:
    cmd: python src/train.py
    deps: [src/train.py, data/processed]
    params: [train.n_estimators, train.max_depth]      # read from params.yaml
    outs: [models/model.pkl]
  evaluate:
    cmd: python src/evaluate.py
    deps: [src/evaluate.py, models/model.pkl]
    metrics: [metrics.json]
```

`dvc repro` hashes every `deps` entry. If nothing changed, the stage is **skipped** (cached). Change one hyperparameter in `params.yaml` and only `train` and `evaluate` re-run. It's `make` for ML.

**The combination that gives you reproducibility:** one Git commit pins the code, `params.yaml`, `dvc.yaml`, `dvc.lock` (hashes of data and model) and `requirements.txt`. Checking out any commit and running `dvc pull` gives you back exactly that model.

---

## 7. Experiment tracking with MLflow

Data scientists run dozens of training runs with different parameters. Without tracking, you end up with `model_final_v2_REALLY_final.pkl`. MLflow Tracking records every run in a database you can browse and compare.

**What gets recorded per run**

| Item | Example | API |
|---|---|---|
| Parameters | `n_estimators=200` | `mlflow.log_param()` / `log_params()` |
| Metrics | `accuracy=0.93`, per epoch too | `mlflow.log_metric()` |
| Artifacts | Confusion-matrix PNG, `model.pkl`, reports | `mlflow.log_artifact()` |
| Model | Packaged model with signature + dependencies | `mlflow.sklearn.log_model()` |
| Tags / metadata | Git commit, dataset version, author | `mlflow.set_tag()` (Git commit is auto-captured) |

**Minimal example** (MLflow 3.x):

```python
import mlflow
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

mlflow.set_tracking_uri("http://localhost:5000")   # the MLflow server
mlflow.set_experiment("churn-model")

params = {"n_estimators": 200, "max_depth": 8, "random_state": 42}

with mlflow.start_run(run_name="rf-200"):
    model = RandomForestClassifier(**params).fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))

    mlflow.log_params(params)
    mlflow.log_metric("accuracy", acc)
    mlflow.set_tag("data_version", "dvc:3c2a6e0f")
    mlflow.sklearn.log_model(
        model,
        name="model",
        registered_model_name="churn-model",     # also creates a new registry version
        input_example=X_test.head(3),            # records the input schema (signature)
    )
```

Shortcut: `mlflow.sklearn.autolog()` logs params, metrics and the model automatically.

**MLflow architecture.** Know this for interviews and production design:

```
  training code ──(REST)──▶  MLflow Tracking Server  ──▶  Backend store: run metadata
  (laptop / CI runner)                                    (SQLite locally, PostgreSQL/MySQL in prod)
                                        │
                                        └──────────────▶  Artifact store: models, plots
                                                          (local folder locally, S3/GCS/Blob in prod)
```

A production setup is: MLflow server in a container on ECS or Kubernetes, **RDS PostgreSQL** as the backend store, an **S3 bucket** as the artifact store, and auth in front. Or use SageMaker's managed MLflow.

**Model Registry.** The registry is the hand-off point between training and deployment:

- Every registered model has **numbered versions** (v1, v2, v3…), each linked to the run, and therefore to the code, params, metrics and data that produced it.
- **Aliases** such as `@champion` (production) and `@challenger` (candidate) point at versions. Deployment code loads `models:/churn-model@champion`, so promoting a model means **moving the alias, not rebuilding the app**.
- Older MLflow versions used fixed *stages* (Staging/Production). These are deprecated, so use **aliases and tags** instead.

We use the registry heavily in Session 2 for deployment and governance.

---

## 8. CI/CD for ML: CI, CT and CD

| | Trigger | What runs | Goal |
|---|---|---|---|
| **CI**: Continuous Integration | PR / push to code | Lint, unit tests for feature code, **data validation tests**, a small training run on sample data | Catch broken code or bad data early |
| **CT**: Continuous Training | New data, schedule (cron), drift alert, or merge to `main` | Full `dvc repro`: preprocess → train → evaluate → register | Keep the model fresh |
| **CD**: Continuous Delivery | New model version passes its gate (plus approval) | Build serving image, deploy to staging, then prod | Ship the model safely (Session 2) |

**What to test in ML CI**, beyond normal unit tests:

- **Data tests:** expected columns and types, no nulls in key fields, values in range, enough rows.
- **Feature tests:** preprocessing gives the same output for a known input.
- **Model tests:** accuracy ≥ threshold, new model not worse than current `@champion`, prediction latency within budget, fixed test cases predict as expected.

**A continuous-training workflow in GitHub Actions** (preview; you'll build the real one in class):

```yaml
name: train-model
on:
  push:
    branches: [main]
    paths: ["src/**", "params.yaml", "data/**.dvc"]
  schedule:
    - cron: "0 2 * * 1"          # retrain every Monday 02:00 UTC
  workflow_dispatch: {}

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: dvc pull                          # fetch data from the DVC remote (S3)
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      - run: pytest tests/                     # data + code tests
      - run: dvc repro                         # preprocess -> train -> evaluate
        env:
          MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      - run: python src/check_gate.py          # exit 1 if accuracy < threshold
      - run: dvc push                          # save new model/data versions
```

Everything here is DevOps you already know: triggers, secrets, jobs and exit codes. The only new parts are *what* the steps do.

---

## 9. Artifact storage and reproducibility

**Where each thing lives**

| Thing | Store | Why |
|---|---|---|
| Code, configs, `params.yaml`, `dvc.yaml`, `dvc.lock` | Git | Small, text, reviewable in PRs |
| Raw and processed datasets | DVC remote (S3/GCS/Blob) | Large, binary, content-addressed |
| Run metadata (params, metrics, tags) | MLflow backend store (Postgres) | Queryable, comparable |
| Models, plots, reports | MLflow artifact store (S3) | Large, linked to runs |
| Serving images | Container registry (ECR, Docker Hub) | Deployable unit (Session 2) |

**Reproducibility checklist.** A run is reproducible only if you can answer all of these:

- [ ] Which **code** commit? *(Git SHA, auto-tagged by MLflow)*
- [ ] Which **data** version? *(DVC hash in `dvc.lock`)*
- [ ] Which **parameters**? *(`params.yaml` + MLflow params)*
- [ ] Which **library versions**? *(pinned `requirements.txt`, logged with the MLflow model)*
- [ ] Which **random seed**? *(`random_state` in params)*
- [ ] Which **environment**? *(Docker base image / CI runner image)*

If any box is empty, "it worked on my laptop" is back.

---

## 10. What you'll do in the session (hands-on preview)

You'll start from a single training script and, step by step:

1. Split it into `preprocess`, `train` and `evaluate` stages, driven by `params.yaml`.
2. Version the dataset with **DVC** and define the pipeline in `dvc.yaml`. Run `dvc repro` and watch caching work.
3. Add **MLflow tracking**, run several experiments, and compare them in the MLflow UI.
4. Register the best model and give it the `@champion` alias.
5. Add a **quality gate** and a **GitHub Actions** workflow that retrains on every push.

Come with `verify_setup.py` passing, and the MLflow UI and Docker working.

---

## 11. Self-check (answer before class)

1. Name three reasons an ML model can degrade even though nobody changed the code.
2. What does a `.dvc` file contain, and why is the actual data file in `.gitignore`?
3. You change only `max_depth` in `params.yaml` and run `dvc repro`. Which stages re-run, and why?
4. What is the difference between an MLflow **parameter**, **metric** and **artifact**? Give one example of each.
5. Why do deployments load `models:/churn-model@champion` rather than `models:/churn-model/7`?
6. Where would you store MLflow's backend store and artifact store in an AWS production setup?
7. In ML CI/CD, what is **CT**, and name two things that can trigger it.
8. Kubeflow Pipelines vs Vertex AI Pipelines: what is the main operational difference?

<details>
<summary>Answers</summary>

1. Data drift (the input data changes), concept drift (the real-world relationship changes), upstream data-pipeline bugs, seasonality, new user segments.
2. An MD5 hash, size and path pointing to the real file in the DVC remote. The big file is git-ignored so Git only versions the lightweight pointer.
3. `train` and `evaluate`, because they list that parameter or depend on the model output. `preprocess` is cached because its dependencies didn't change.
4. Parameter: an input setting (`n_estimators=200`). Metric: a measured result (`accuracy=0.93`). Artifact: a produced file (`model.pkl`, a confusion-matrix PNG).
5. The alias decouples deployment from a specific version. Promotion or rollback is just moving the alias, with no code change.
6. Backend store in RDS PostgreSQL, artifact store in S3.
7. Continuous Training: automatically retraining the model. Triggers: new data, a schedule, a drift alert, or a merge to `main`.
8. With KFP you run and operate the Kubernetes cluster. Vertex is managed and serverless on GCP (no cluster), but tied to GCP.
</details>

---

## 12. Optional further reading

- [MLflow documentation](https://mlflow.org/docs/latest/): *Tracking* and *Model Registry* sections
- [DVC Get Started](https://dvc.org/doc/start): *Data versioning* and *Data pipelines*
- [Google Cloud: MLOps continuous delivery and automation pipelines in ML](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning), the source of the maturity levels
- [Kubeflow Pipelines overview](https://www.kubeflow.org/docs/components/pipelines/overview/)
- [Vertex AI Pipelines introduction](https://cloud.google.com/vertex-ai/docs/pipelines/introduction)
- [Amazon SageMaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html)
