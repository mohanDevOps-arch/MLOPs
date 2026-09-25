# MLOps Module — Pre-Session Pack

**Program:** PPMCAD — Multicloud Architecture in DevOps

| Session | Topic |
|---|---|
| 1 | Building ML Pipelines with DevOps Practices |
| 2 | Deployment, Monitoring, and Governance |

## Do these in order

| # | File | When | Time |
|---|---|---|---|
| 1 | `00_Prerequisites_and_Installation.md` | At least 2 days before Session 1 | 60–90 min |
| 2 | `01_PreRead_Building_ML_Pipelines_with_DevOps.md` | Before Session 1 | ~30 min |
| 3 | `02_PreRead_Deployment_Monitoring_Governance.md` | Before Session 2 | ~35 min |

## Setup files (`setup/`)

| File | Purpose |
|---|---|
| `requirements.txt` | MLflow, DVC, Evidently, scikit-learn, pandas, FastAPI, Uvicorn, prometheus-client |
| `requirements-aws.txt` | boto3 + sagemaker (optional, for the SageMaker demo only) |
| `verify_setup.py` | Checks tools and packages, then runs a train → MLflow → registry → Evidently smoke test |
| `kind-config.yaml` | Local Kubernetes cluster (`kind create cluster --name mlops --config kind-config.yaml`) |
| `docker-compose.monitoring.yml` + `prometheus.yml` | Prometheus (9090) + Grafana (3000) for Session 2 |

**Ready check:** `python verify_setup.py` ends with *All good — you're ready for the MLOps sessions.*

## Tool stack

Local-first, so everything runs on a laptop or a single EC2 instance: **Git + DVC + MLflow + GitHub Actions + Docker + kind + Prometheus/Grafana + Evidently**.
Managed platforms (**SageMaker**, and **Kubeflow / Vertex AI** for comparison) are covered as instructor walkthroughs.
