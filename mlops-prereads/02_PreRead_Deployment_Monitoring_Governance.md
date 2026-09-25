# Pre-Read — Session 2: Deployment, Monitoring, and Governance

**Program:** PPMCAD — Multicloud Architecture in DevOps · **Module:** MLOps
**Reading time:** about 35 minutes
**Before this:** Session 1 (or its pre-read), with `verify_setup.py` passing

---

## What the session covers

1. Deploy ML models to production using **Docker**, **Kubernetes**, or cloud services like **SageMaker** or **GCP Vertex AI** (formerly AI Platform).
2. Monitor model performance with **drift detection** and **logging** (**Prometheus**, **Grafana**, **Evidently**).
3. Implement **model governance** with version control, audit trails and approval workflows.

Session 1 ended with a registered model version in MLflow. Session 2 takes that model to production, keeps watching it, and makes sure every change is controlled and traceable.

---

## 1. From registry to production: the big picture

```
            Session 1                                   Session 2
 ┌───────────────────────────────┐   ┌──────────────────────────────────────────────────────┐
 │ pipeline → MLflow Registry    │   │ approve → package → deploy → serve → monitor → retrain│
 │            churn-model v7     │──▶│  (gov)    Docker    K8s /    API    Prometheus  (CT)  │
 │            @challenger        │   │                     SageMaker       Grafana           │
 └───────────────────────────────┘   │                                     Evidently         │
                                     └──────────────────────────────────────────────────────┘
```

Three questions frame the whole session:

- **Deployment:** how do predictions reach users reliably and at scale?
- **Monitoring:** how do we know the model is still *right*, not just *up*?
- **Governance:** who approved this model, what data trained it, and can we prove it?

---

## 2. Serving patterns

| Pattern | How it works | Latency | Example | Typical infra |
|---|---|---|---|---|
| **Online / real-time** | REST or gRPC API returns a prediction per request | ms | Fraud check at checkout | FastAPI container on K8s, SageMaker real-time endpoint |
| **Batch** | Scheduled job scores a whole table and writes the results | minutes–hours | Nightly churn scores for CRM | K8s CronJob, SageMaker Batch Transform, Airflow |
| **Streaming** | Consume events from a queue and emit predictions | seconds | Real-time recommendations | Kafka/Kinesis consumer |
| **Serverless** | Function wraps the model and scales to zero | ms (plus cold start) | Low-traffic internal tool | Lambda, SageMaker Serverless Inference, Cloud Run |
| **Edge** | Model runs on the device | µs–ms | Mobile image classifier | ONNX / TFLite |

Session 2 focuses on **online serving**, the most common pattern and the one closest to regular microservice DevOps.

---

## 3. Packaging a model with Docker

A model is just a file. To serve it you need **model + runtime + API + dependencies**, and a container packages all four.

**Option A: let MLflow build it.**

```bash
# quick local test: serve straight from the registry
mlflow models serve -m "models:/churn-model@champion" -p 5001 --env-manager local

# build a production image (the MLflow scoring server lives inside)
mlflow models build-docker -m "models:/churn-model@champion" -n churn-model:1.0.0
docker run -p 5001:8080 churn-model:1.0.0

curl -X POST http://localhost:5001/invocations \
     -H "Content-Type: application/json" \
     -d '{"dataframe_split": {"columns": ["tenure","monthly_charges"], "data": [[12, 70.5]]}}'
```

This is fast to set up, but you get MLflow's generic API.

**Option B: your own FastAPI service.** This is what most teams do in production, because you control validation, auth, metrics and response format.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY app/ app/
COPY model/ model/            # model downloaded from the registry at build time
USER 1000                     # never run as root
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Image best practices** carry straight over from your Docker module: a slim base, pinned dependencies, non-root user, a health endpoint, and tagging the image with the **model version** (`churn-model:1.0.7`, following the `1.0.x` convention) so each image maps to exactly one registry version.

**Should the model be baked into the image, or loaded at startup?**

| | Bake into image | Load at startup from registry/S3 |
|---|---|---|
| Pros | Immutable, reproducible, one artifact to deploy | Swap models without rebuilding |
| Cons | New image per model version | Startup depends on S3/registry, harder to audit |
| Use when | Regulated or production systems | Fast experimentation, very large models |

---

## 4. Deploying on Kubernetes

A model API is a stateless microservice, so the usual K8s objects apply, with a few ML-specific twists:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: churn-model
  labels: { app: churn-model, model-version: "7" }
spec:
  replicas: 2
  selector: { matchLabels: { app: churn-model } }
  template:
    metadata:
      labels: { app: churn-model, model-version: "7" }
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      containers:
        - name: api
          image: mohan019/churn-model:1.0.7
          ports: [{ containerPort: 8000 }]
          resources:
            requests: { cpu: "250m", memory: "512Mi" }
            limits:   { cpu: "1",    memory: "1Gi" }     # models can be memory-hungry
          readinessProbe:                                # only send traffic once the model is loaded
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 10
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            periodSeconds: 20
```

**ML-specific points**

- **Readiness probe = "model loaded".** Loading a big model can take 30 s or more. Without a readiness probe, users get errors during rollouts.
- **Right-size memory.** The model sits in RAM in every replica. OOMKilled pods are a classic ML-on-K8s failure.
- **HPA** on CPU or requests-per-second handles traffic spikes. GPU models use node pools with `nvidia.com/gpu` resources.
- **Label pods with the model version.** Then Prometheus metrics, logs and alerts all carry it, which is essential for comparing versions.
- **Specialised serving platforms** on K8s: **KServe** (the Kubeflow family), **Seldon Core** and **BentoML**. They add canary splits, autoscale-to-zero and standard inference protocols on top of what you see here.

In class we deploy to the local **kind** cluster you created during setup.

---

## 5. Managed platforms: SageMaker and Vertex AI

If you don't want to run the cluster yourself:

| | **AWS SageMaker** | **GCP Vertex AI** |
|---|---|---|
| Deploy unit | **Model** → **Endpoint configuration** → **Endpoint** | **Model** (Model Registry) → **Endpoint** |
| Real-time | Real-time endpoints (instance-based, autoscaling) | Online prediction endpoints |
| Low traffic | Serverless Inference | Scale-to-zero not native (use Cloud Run) |
| Batch | Batch Transform | Batch prediction jobs |
| Traffic split | **Production variants** with weights (A/B, canary) | Traffic split % across deployed models |
| Registry | SageMaker Model Registry (model **package groups**, approval status) | Vertex AI Model Registry (versions, aliases) |
| Drift monitoring | SageMaker **Model Monitor** | Vertex AI **Model Monitoring** |
| Pipelines | SageMaker Pipelines | Vertex AI Pipelines (KFP) |
| MLflow | Managed MLflow on SageMaker | — (self-host) |

**Mental model for SageMaker:** *Model* = image + model artifact in S3. *Endpoint configuration* = which models, on which instance types, and with what traffic weights. *Endpoint* = the running HTTPS API. Updating an endpoint to a new configuration performs a **managed blue/green switch**.

**Cost warning:** a SageMaker real-time endpoint bills **every hour it exists**, even with zero traffic. Always delete demo endpoints: `aws sagemaker delete-endpoint --endpoint-name <name>`.

---

## 6. Safe rollout strategies for models

A new model can pass offline evaluation and still perform worse on live traffic. So roll it out gradually:

| Strategy | How | Risk | When |
|---|---|---|---|
| **Shadow** | New model receives a *copy* of live traffic, and its predictions are logged but **not returned** | None to users | First production test of a very different model |
| **Canary** | 5–10% of traffic goes to the new model, then ramps up if its metrics hold | Low | Default choice |
| **Blue/Green** | Two full environments; flip all traffic at once, flip back to roll back | Medium (all at once), but instant rollback | Simple services, managed endpoints |
| **A/B test** | Split traffic and compare **business** metrics (conversion, revenue) over days | Low–medium | Choosing between two good models |

**Rollback in MLOps = move the `@champion` alias back and redeploy the previous image tag.** That's another reason images are tagged by model version.

---

## 7. Monitoring: "up" is not the same as "right"

A model service can return HTTP 200 in 20 ms and still give **wrong answers**. So monitor four layers:

| Layer | Question | Metrics | Tool |
|---|---|---|---|
| **Infrastructure** | Are the pods healthy? | CPU, memory, restarts, OOMKills | Prometheus + node/kube exporters |
| **Service** | Is the API healthy? | Request rate, error rate, latency p50/p95/p99 | Prometheus + Grafana |
| **Data** | Do the inputs look like the training data? | Feature distributions, nulls, out-of-range values, **data drift** | Evidently, SageMaker Model Monitor |
| **Model** | Are the predictions still good? | Prediction distribution, confidence, **accuracy once ground truth arrives** | Evidently + Prometheus |

### 7.1 Instrumenting the model API for Prometheus

The `prometheus-client` library exposes a `/metrics` endpoint that Prometheus scrapes:

```python
import time
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

PREDICTIONS = Counter("model_predictions_total", "Predictions served",
                      ["model_version", "predicted_class"])
LATENCY = Histogram("model_inference_seconds", "Inference latency in seconds")

app = FastAPI()
app.mount("/metrics", make_asgi_app())

@app.post("/predict")
def predict(features: dict):
    start = time.perf_counter()
    label = "churn"                            # model.predict(...) goes here
    LATENCY.observe(time.perf_counter() - start)
    PREDICTIONS.labels(model_version="7", predicted_class=label).inc()
    return {"prediction": label}
```

Useful **PromQL** queries in Grafana:

```promql
# requests per second, per model version
sum by (model_version) (rate(model_predictions_total[5m]))

# p95 inference latency
histogram_quantile(0.95, sum by (le) (rate(model_inference_seconds_bucket[5m])))

# share of "churn" predictions: a sudden jump hints at drift
sum(rate(model_predictions_total{predicted_class="churn"}[1h]))
  / sum(rate(model_predictions_total[1h]))
```

**Label cardinality warning:** never use user IDs or raw feature values as Prometheus labels. Each unique value creates a new time series and can take Prometheus down.

### 7.2 Logging predictions

Log each prediction as **structured JSON**: timestamp, request ID, model version, input features and prediction. Ship the logs to CloudWatch, Loki or ELK. These logs are:

- the **input to drift detection** (current data vs training data),
- the way to **join ground truth later** (did the customer actually churn?) and compute real accuracy,
- part of the **audit trail** (see §9).

Mask or hash personal data before logging.

---

## 8. Drift: why models decay

| Type | What changes | Example | Detect with |
|---|---|---|---|
| **Data drift** (covariate shift) | Distribution of **inputs** | New marketing campaign brings younger customers | Compare feature distributions: reference vs current |
| **Prediction drift** | Distribution of **outputs** | Share of "churn" predictions doubles | Compare prediction distributions |
| **Concept drift** | Relationship between **inputs and the correct answer** | A competitor's price cut makes loyal customers churn | Needs ground truth: accuracy drops over time |
| **Data quality issues** | Upstream bugs | A column suddenly all nulls, units changed (₹ to $) | Schema and range checks |

**Common statistical tests** (you don't need the maths, just what each is used for):

- **Kolmogorov–Smirnov (KS) test:** numerical features, small samples.
- **Chi-squared test:** categorical features.
- **PSI (Population Stability Index):** a common industry rule of thumb is < 0.1 stable, 0.1–0.25 moderate shift, > 0.25 significant shift.
- **Wasserstein distance / Jensen–Shannon divergence:** larger datasets.

### 8.1 Evidently

**Evidently** is an open-source Python library that compares a **reference** dataset (usually training data) with **current** data (recent production inputs), and produces HTML reports, JSON results or test suites for CI:

```python
from evidently import Report
from evidently.presets import DataDriftPreset

report = Report([DataDriftPreset()])
snapshot = report.run(reference_data=train_df, current_data=last_week_df)
snapshot.save_html("drift_report.html")      # visual report per feature
```

Evidently picks a suitable test per column automatically and flags the dataset as drifted when a set share of columns have drifted.

**Closing the loop:**

```
 prediction logs ──▶ scheduled drift job (Evidently, e.g. K8s CronJob daily)
                          │
                          ├─ export drift score as a Prometheus metric ──▶ Grafana panel + alert
                          │
                          └─ drift above threshold ──▶ trigger the CT pipeline from Session 1
                                                       (GitHub Actions workflow_dispatch)
```

This is how monitoring feeds back into **continuous training**, and it completes the MLOps loop.

---

## 9. Model governance

Governance answers: **who changed what, when, why, and was it allowed?** It matters more every year. Regulations such as the **EU AI Act**, sector rules for banking, healthcare and insurance, and internal risk teams all require models to be **traceable, explainable and approved**.

### 9.1 The three pillars

**1. Version control and lineage.** Every production model must trace back to:

```
Production endpoint ─▶ image mohan019/churn-model:1.0.7
                      ─▶ MLflow model churn-model v7
                        ─▶ MLflow run a1b2c3 (params, metrics, Git SHA 9f8e7d)
                          ─▶ dvc.lock data hash 3c2a6e (training dataset)
                            ─▶ S3 object in the DVC remote
```

Session 1 gave you all these links (Git + DVC + MLflow). Governance means **enforcing** that none are skipped.

**2. Audit trails.** An immutable record of events:

| Event | Where it's recorded |
|---|---|
| Code / config change | Git commits and PR reviews |
| Training run | MLflow run (who, when, params, metrics) |
| Model registration or alias change | MLflow registry and tags; SageMaker Model Registry history |
| Approval | PR approval, GitHub Environment approval log, SageMaker approval status |
| Deployment | CI/CD run logs, `kubectl rollout history`, AWS **CloudTrail** |
| Predictions | Prediction logs (§7.2) |

**3. Approval workflows.** A model reaches production only after passing gates:

```
 train ──▶ automated gate ──▶ register as @challenger ──▶ human review ──▶ @champion ──▶ deploy
           (accuracy ≥ X,       (model card, eval report,     (approver in
            fairness check,      drift baseline attached)      GitHub Environment /
            beats current                                      SageMaker approval)
            champion)
```

How to implement the human gate:

- **GitHub Actions Environments:** a `production` environment with **required reviewers**. The deploy job pauses until an approver clicks *Approve*, and GitHub records who approved and when.
- **SageMaker Model Registry:** each model package has an **approval status** of `PendingManualApproval`, `Approved` or `Rejected`. An EventBridge rule on the status change to `Approved` can trigger the deployment pipeline.
- **MLflow:** use tags (`approval_status=approved`, `approved_by=…`) and only let the CD pipeline's identity move the `@champion` alias.

### 9.2 Model cards

A **model card** is a short document stored with each model version. It covers: purpose and intended use, training data (and its version), evaluation metrics (overall and per segment), known limitations and biases, owner, and approval date. Log it as an MLflow artifact so it travels with the model.

### 9.3 Separation of duties

The person who trains a model should not be the only person who can approve it for production. Enforce this with **RBAC**: data scientists can register models, and only the release role or pipeline identity can promote them. It's the same principle as protected branches in Git.

---

## 10. What you'll do in the session (hands-on preview)

Starting from the registered model in Session 1:

1. Wrap the model in a **FastAPI** service with `/predict`, `/health` and `/metrics`, then build and run it with **Docker**.
2. Deploy it to your local **kind** cluster with a Deployment, Service and readiness probes, and scale it.
3. Start **Prometheus and Grafana** (`docker-compose.monitoring.yml`), and build a dashboard for request rate, latency and prediction mix.
4. Simulate drifted traffic and generate an **Evidently** drift report.
5. Add a **governance gate**: a GitHub Actions workflow that deploys only after the model passes checks and a reviewer approves, then promote `@challenger` to `@champion`.
6. *(Instructor demo)* Deploy the same model to a **SageMaker** real-time endpoint and look at the model approval status in the SageMaker Model Registry.

---

## 11. Self-check (answer before class)

1. Give one use case each for online, batch and streaming serving.
2. Why is a **readiness probe** especially important for a model-serving pod?
3. Your API shows 0% errors and 30 ms p95 latency, yet the business says predictions are "wrong". Which monitoring layers were missing?
4. What is the difference between **data drift** and **concept drift**? Which one can you detect without ground-truth labels?
5. Why must you never put `customer_id` as a Prometheus label?
6. Describe a canary rollout for a new model version on Kubernetes.
7. List the chain of links that lets you trace a production prediction back to its training data.
8. Name two ways to implement a human approval step before a model reaches production.
9. Why should you delete a SageMaker endpoint after a demo?

<details>
<summary>Answers</summary>

1. Online: fraud check at payment. Batch: nightly churn scoring. Streaming: real-time recommendations from clickstream events.
2. Model loading can take seconds to minutes. Without readiness, the pod gets traffic before the model is in memory, which causes errors during every rollout or scale-up.
3. The data and model layers: no drift detection on inputs, and no quality tracking against ground truth.
4. Data drift: the input distribution changes. Concept drift: the input-to-correct-answer relationship changes. Data drift (and prediction drift) can be detected without labels; concept drift needs ground truth.
5. Every unique label value creates a new time series. Millions of customers means millions of series, which exhausts Prometheus memory (a cardinality explosion).
6. Deploy the new version alongside the old with a small share of traffic (via replica ratio, Ingress or service-mesh weights, or KServe canary), compare error, latency and prediction metrics per `model_version` label, then ramp up or roll back.
7. Endpoint → image tag → registry model version → MLflow run (Git SHA, params) → `dvc.lock` data hash → dataset in the DVC remote.
8. GitHub Environments with required reviewers; the SageMaker Model Registry approval status (`PendingManualApproval` → `Approved`). Also: a PR approval on an alias-change file.
9. Real-time endpoints bill per instance-hour whether or not they receive traffic.
</details>

---

## 12. Optional further reading

- [MLflow: Deploy models](https://mlflow.org/docs/latest/ml/deployment/) and [Model Registry aliases](https://mlflow.org/docs/latest/ml/model-registry/)
- [Evidently documentation](https://docs.evidentlyai.com/)
- [Prometheus Python client](https://prometheus.github.io/client_python/)
- [Amazon SageMaker: Deploy models for inference](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)
- [Amazon SageMaker Model Registry: approval status](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-approve.html)
- [Vertex AI: Deploy a model to an endpoint](https://cloud.google.com/vertex-ai/docs/general/deployment)
- [KServe](https://kserve.github.io/website/): model serving on Kubernetes
- [GitHub Actions: Environments and required reviewers](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993), the original paper
