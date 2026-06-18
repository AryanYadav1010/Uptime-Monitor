# Incident Response Runbook: UrlDown Alert

This runbook outlines triage, diagnosis, and mitigation steps when the `UrlDown` alert fires.

## Alert Overview
- **Name:** `UrlDown`
- **Severity:** Critical
- **Description:** A target URL monitored by `uptime-monitor` is returning non-2xx/3xx response codes or has timed out for more than 2 minutes.

---

## Step 1: Identify the Affected Target URL
Examine the alert details in Alertmanager or the Prometheus UI. Extract the value of the `url` label.
```bash
# Get current firing alerts matching UrlDown using Prometheus API or kubectl
kubectl exec -it deploy/prometheus-k8s -n monitoring -- curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="UrlDown")'
```

---

## Step 2: Validate Target Service Health via Live Check
Trigger an immediate check directly from the uptime-monitor pods to confirm if it is a transient error or a hard outage.
```bash
# Port-forward to one of the uptime-monitor pods
kubectl port-forward svc/uptime-monitor 8000:8000 &
PID=$!
sleep 1

# Send a check request
curl -s http://localhost:8000/check | jq .

# Terminate port-forward
kill $PID
```

---

## Step 3: Inspect Container Logs & OpenTelemetry Traces
Read structured JSON logs from the service. Identify the trace IDs corresponding to the failed checks.
```bash
# View structured JSON logs for checks returning up = false
kubectl logs -l app=uptime-monitor --tail=100 | grep '"up": false' | jq .
```
Expected output fields to trace:
- `url`: Target being checked
- `status_code`: HTTP status code returned (e.g., `502`, `404`, or `0` for network failures/timeouts)
- `latency_ms`: Time taken before failure
- `trace_id`: The OpenTelemetry Trace ID. Copy this value and query your OTel collector backend (e.g., Jaeger or AWS X-Ray) to correlate internal network spans.

---

## Step 4: Isolate the Failure Domain
- **Scenario A (Status Code `0`):** Indicates a network timeout, DNS resolution failure, or egress security group issue on EKS nodes.
  - Action: Check EKS cluster outbound security groups and NAT Gateway status.
- **Scenario B (Status Code `5xx`):** Target server is experiencing server-side issues.
  - Action: Check status page of target (e.g., `status.github.com` if `github.com` failed).
- **Scenario C (Status Code `4xx`):** Target URL path or request payload configuration is invalid.
  - Action: Check environment variable changes in the uptime-monitor deployment configuration.

---

## Step 5: Mitigation and Resolution
- If the issue is a misconfigured URL environment variable:
  ```bash
  kubectl set env deployment/uptime-monitor MONITOR_URLS="github.com,httpbin.org"
  kubectl rollout status deployment/uptime-monitor
  ```
- If the issue is EKS egress connectivity:
  - Check NAT Gateway route tables and security group rules in the Terraform project outputs.
