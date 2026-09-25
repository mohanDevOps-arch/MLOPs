# MLOps Sessions — Prerequisites & Installation Guide

**Program:** PPMCAD — Multicloud Architecture in DevOps
**Module:** MLOps
**Covers:** Session 1 *Building ML Pipelines with DevOps Practices* and Session 2 *Deployment, Monitoring, and Governance*
**Time needed:** 60–90 minutes (mostly downloads). **Please finish this before Session 1.**

---

## 1. What you need to know already

You do **not** need a data-science background. The sessions are written for DevOps engineers. You should be comfortable with:

| Skill | Level needed | Quick refresher if rusty |
|---|---|---|
| Linux shell | Navigate folders, edit files, run scripts, set env variables | Your Bash lab from the Linux module |
| Git & GitHub | clone, branch, commit, push, pull request | `git log --oneline --graph` should make sense to you |
| Docker | Write a Dockerfile, build, run, push an image | Docker module notes |
| Kubernetes | Deployment, Service, `kubectl apply/get/logs/describe` | Kubernetes module notes |
| CI/CD | Read a GitHub Actions or Jenkins pipeline | CI/CD module notes |
| Python | Read a 50-line script, create a virtual environment, `pip install` | [Python venv docs](https://docs.python.org/3/library/venv.html) |
| YAML | Indentation, lists, maps | — |

Machine-learning ideas (training, features, accuracy, drift) are explained in the pre-reads, so don't worry if they are new.

---

## 2. Hardware and accounts

**Laptop**

| | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Free disk | 20 GB | 30 GB |
| CPU | 4 cores, 64-bit | Apple Silicon or 6+ cores |
| OS | Windows 10 22H2 / 11, macOS 13+, Ubuntu 22.04 / 24.04 | — |

Low on RAM? Use an **AWS EC2 instance** instead (see §5.4). It works just as well.

**Accounts**

| Account | Required? | Used for |
|---|---|---|
| GitHub | **Yes** | Repos and GitHub Actions pipelines |
| Docker Hub | Optional | Pushing model images (you can also stay local) |
| AWS | Optional | SageMaker walkthrough in Session 2. **May incur charges.** The instructor demos it, and following along is optional. |

---

## 3. What you will install

| Tool | Why | Session |
|---|---|---|
| Python 3.11 or 3.12 | Runs the training and serving code | 1, 2 |
| Git | Versioning code, and pipelines through GitHub Actions | 1, 2 |
| Docker Desktop / Docker Engine | Packaging models, running Prometheus and Grafana | 1, 2 |
| kubectl + kind | A local Kubernetes cluster for model deployment | 2 |
| MLflow | Experiment tracking and model registry | 1, 2 |
| DVC | Data and model versioning next to Git | 1 |
| Evidently | Data and model drift reports | 2 |
| scikit-learn, pandas | Training a small model | 1, 2 |
| FastAPI, Uvicorn, prometheus-client | Serving the model as an API with metrics | 2 |
| AWS CLI v2 (+ boto3, sagemaker) | SageMaker walkthrough | 2 (optional) |
| VS Code (or any editor) | Editing | 1, 2 |

**Why no Kubeflow install?** A full Kubeflow deployment needs a large cluster and is too heavy for a laptop. Kubeflow Pipelines and Vertex AI Pipelines are explained conceptually and demoed by the instructor, and the ideas map one-to-one to what you'll build with MLflow and GitHub Actions.

---

## 4. Get the setup files

The `setup/` folder shared with this guide contains:

```
setup/
├── requirements.txt               # core Python packages
├── requirements-aws.txt           # optional, SageMaker only
├── verify_setup.py                # checks everything + runs a smoke test
├── kind-config.yaml               # local Kubernetes cluster
├── docker-compose.monitoring.yml  # Prometheus + Grafana
└── prometheus.yml                 # Prometheus scrape config
```

Create a working folder called `mlops-lab` and copy the contents of `setup/` into it. All commands below run from inside `mlops-lab`.

---

## 5. Install, by operating system

Pick **one** path: §5.1 Windows, §5.2 macOS, §5.3 Linux, or §5.4 EC2. Then go to §6.

### 5.1 Windows 10 / 11

**Recommended:** do the work inside **WSL 2 (Ubuntu)**. Most MLOps tooling is Linux-first, and this avoids path and permission problems.

**Step 1: Enable WSL 2.** Open **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart when asked, then open **Ubuntu** from the Start menu and create a username and password.

**Step 2: Install Docker Desktop.**

```powershell
winget install -e --id Docker.DockerDesktop
```

Open Docker Desktop, then go to **Settings → General** and tick **Use the WSL 2 based engine**. Under **Settings → Resources → WSL Integration**, switch on **Ubuntu-24.04**. Click *Apply & restart*.

**Step 3: Install VS Code with WSL support** (optional, but it helps):

```powershell
winget install -e --id Microsoft.VisualStudioCode
code --install-extension ms-vscode-remote.remote-wsl
```

**Step 4:** Open the **Ubuntu** terminal and follow **§5.3 Linux** from Step 1. **Skip the Docker Engine step**, because Docker Desktop already provides `docker` inside WSL.

> **Keep your files inside WSL**, e.g. `~/mlops-lab`, not under `/mnt/c/...`. File operations under `/mnt/c` are much slower and cause permission errors with DVC and Git.
> Open the folder in VS Code from Ubuntu with `code .`

<details>
<summary><b>Native Windows (no WSL)</b>: use only if WSL is blocked on your machine</summary>

```powershell
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12
winget install -e --id Docker.DockerDesktop
winget install -e --id Kubernetes.kubectl
winget install -e --id Kubernetes.kind
winget install -e --id Amazon.AWSCLI        # optional
```

Close and reopen PowerShell, then:

```powershell
cd $HOME\mlops-lab
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation fails with *"running scripts is disabled"*:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then continue at **§6** (use `python` instead of `python3`).
</details>

---

### 5.2 macOS (Intel or Apple Silicon)

**Step 1: Install Homebrew** (skip if `brew --version` already works):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

On Apple Silicon, run the two `eval` lines Homebrew prints at the end so `brew` is on your PATH.

**Step 2: Install the tools.**

```bash
brew install python@3.12 git kubectl kind awscli
brew install --cask docker            # Docker Desktop
```

**Step 3:** Open **Docker Desktop** from Applications once and accept the prompts. Then go to **Settings → Resources** and give it **at least 4 CPUs and 6 GB memory**.

**Step 4: Check.**

```bash
python3.12 --version && git --version && docker --version && kubectl version --client && kind version
```

Continue at **§6**, using `python3.12` to create the virtual environment.

> Docker Desktop not allowed on your Mac? Use **Colima** instead: `brew install colima docker docker-compose && colima start --cpu 4 --memory 6`.

---

### 5.3 Linux (Ubuntu 22.04 / 24.04, also WSL)

**Step 1: Base packages and Python.**

Ubuntu **24.04** ships Python 3.12:

```bash
sudo apt update
sudo apt install -y git curl unzip ca-certificates python3 python3-venv python3-pip
```

Ubuntu **22.04** ships Python 3.10, so add 3.12:

```bash
sudo apt update
sudo apt install -y git curl unzip ca-certificates software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.12 python3.12-venv
```

**Step 2: Docker Engine** (skip on WSL if you installed Docker Desktop):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker                      # or log out and back in
docker run --rm hello-world
```

**Step 3: kubectl.**

```bash
ARCH=$(dpkg --print-architecture)          # amd64 or arm64
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl"
sudo install -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
kubectl version --client
```

**Step 4: kind.** Check the newest version on the [kind releases page](https://github.com/kubernetes-sigs/kind/releases) and update `KIND_VERSION` if a newer one exists:

```bash
KIND_VERSION=v0.30.0
ARCH=$(dpkg --print-architecture)
curl -Lo kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${ARCH}"
sudo install -m 0755 kind /usr/local/bin/kind && rm kind
kind version
```

**Step 5: AWS CLI v2** (optional, for the SageMaker walkthrough):

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip
unzip -q awscliv2.zip && sudo ./aws/install && rm -rf aws awscliv2.zip
aws --version
```

Continue at **§6**.

---

### 5.4 AWS EC2 (if your laptop is too small)

1. Launch **Ubuntu Server 24.04 LTS** with instance type **t3.large** (2 vCPU, 8 GB) or bigger and a **30 GB gp3** root volume.
2. Security group: allow **SSH (22) from My IP only**. **Do not** open 5000, 3000, 8080 or 9090 to the internet. Reach them through an SSH tunnel instead:

   ```bash
   ssh -i key.pem \
     -L 5000:localhost:5000 -L 3000:localhost:3000 \
     -L 9090:localhost:9090 -L 8080:localhost:8080 -L 8000:localhost:8000 \
     ubuntu@<EC2_PUBLIC_IP>
   ```

   Now `http://localhost:5000` in your laptop browser opens MLflow running on EC2.
3. Follow **§5.3 Linux**, Steps 1–5.
4. **Stop the instance after each session** to avoid charges.

---

## 6. Create the Python environment (all OSes)

From inside `mlops-lab`:

```bash
# create — use python3.12 / python3 / "py -3.12" depending on your OS
python3.12 -m venv .venv

# activate
source .venv/bin/activate            # Linux, macOS, WSL
# .\.venv\Scripts\Activate.ps1       # Windows PowerShell

# install
python -m pip install --upgrade pip
pip install -r requirements.txt

# optional — only if you'll follow the SageMaker demo
pip install -r requirements-aws.txt
```

The first install downloads about 500 MB and takes 3–8 minutes.

> **Always activate `.venv` before working.** Your prompt shows `(.venv)` when it's active.

---

## 7. Verify everything

### 7.1 Run the checker

```bash
python verify_setup.py
```

Expected ending:

```
=== Smoke test: train -> track -> register -> drift report ===
  [OK]   MLflow run logged (accuracy=1.00) and model registered
  [OK]   Model reloaded from the registry and served a prediction
  [OK]   Evidently drift report generated

=== Result ===
All good — you're ready for the MLOps sessions.
```

`[WARN]` lines for `aws`, `boto3` and `sagemaker` are fine if you're skipping the SageMaker demo.

### 7.2 Start the MLflow UI once

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open **http://localhost:5000**. You should see the MLflow UI with a *Default* experiment. Stop it with `Ctrl+C`.

> **macOS:** if port 5000 is taken (AirPlay Receiver uses it), use `--port 5001`.

### 7.3 Create the local Kubernetes cluster

```bash
kind create cluster --name mlops --config kind-config.yaml
kubectl get nodes
```

Expected: one node, `mlops-control-plane`, with STATUS `Ready` (this can take about a minute).

You can keep the cluster, or delete it and recreate it in class:

```bash
kind delete cluster --name mlops
```

### 7.4 Start Prometheus and Grafana once

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

* **http://localhost:9090**: Prometheus. Under *Status → Targets*, `prometheus` is **UP**. `model-api` shows **DOWN** until Session 2; that's expected.
* **http://localhost:3000**: Grafana, login `admin` / `admin` (skip the password change).

Then stop both:

```bash
docker compose -f docker-compose.monitoring.yml down
```

### 7.5 Pre-pull images (saves class time and bandwidth)

```bash
docker pull python:3.12-slim
docker pull prom/prometheus:latest
docker pull grafana/grafana:latest
```

The `kindest/node` image is pulled automatically in §7.3.

### 7.6 AWS CLI (optional)

```bash
aws configure          # Access key, Secret key, region e.g. ap-south-1, output json
aws sts get-caller-identity
```

Use an IAM user or SSO role with permissions your instructor provides. **Never commit AWS keys to Git.**

---

## 8. Pre-session checklist

- [ ] `python verify_setup.py` ends with **All good**
- [ ] MLflow UI opened at `localhost:5000` (or 5001)
- [ ] `kubectl get nodes` showed a `Ready` node
- [ ] Prometheus (`localhost:9090`) and Grafana (`localhost:3000`) opened
- [ ] Images pre-pulled
- [ ] GitHub account ready, and you can `git push` to a repo of yours
- [ ] Read **01_PreRead_Building_ML_Pipelines_with_DevOps.md** (before Session 1)
- [ ] Read **02_PreRead_Deployment_Monitoring_Governance.md** (before Session 2)

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `python: command not found` | Different name on your OS | Use `python3`, `python3.12`, or `py -3.12` (Windows) |
| `error: externally-managed-environment` | pip run outside a venv | Activate `.venv` first (§6) |
| `ModuleNotFoundError: mlflow` | venv not active, or a different Python | `source .venv/bin/activate`, then `which python` should point into `.venv` |
| `Cannot connect to the Docker daemon` | Docker not running | Start Docker Desktop, or run `sudo systemctl start docker` on Linux |
| `permission denied ... docker.sock` (Linux) | User not in the docker group | `sudo usermod -aG docker $USER`, then log out and back in |
| `kind create cluster` hangs or fails | Docker has too little memory | Give Docker Desktop at least 6 GB (Settings → Resources) |
| Port 5000 already in use | AirPlay (macOS) or another app | `--port 5001` |
| Windows: `Activate.ps1 cannot be loaded` | Execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| WSL very slow, or DVC/Git permission errors | Project under `/mnt/c/...` | Move the project to `~/mlops-lab` inside WSL |
| `pip install` fails building a wheel | Old pip | `python -m pip install --upgrade pip`, then retry |
| Corporate network blocks downloads | Proxy or firewall | Set `HTTPS_PROXY`, or use the EC2 path (§5.4) |

Still stuck? Post the **full output of `python verify_setup.py`** plus your OS in the batch support channel before the session.
