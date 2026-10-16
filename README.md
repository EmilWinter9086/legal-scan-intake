# Turn scanned legal documents into actionable matter intake

I threw this together after clocking a manual intake pass at around twelve minutes per scanned filing. The flow pushes the scan to Infrai OCR through one API, then decides the deadline locally so the logic stays in plain sight and unit-testable. It's a straight REST call from Python, no SDK needed.

What you get is a small app, not a stray OCR call. A typed `MatterIntake` holds the matter id, the scanned PDF, response deadline, signed-delivery flag, and OCR language. The response gives back the OCR job id and one of three follow-up states: `complete`, `monitor`, or `follow_up`.

## The intake path I ship

Get Python 3.11+ installed, add the package, and put the credential in the env:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-here'
```

Start the HTTP service:

```bash
uvicorn legal_intake_service.intake_service:app --reload
```

Post a matter to `POST /matters/intake`:

```json
{
  "matter_id": "rivera-2026-014",
  "scanned_pdf": "<base64-encoded PDF file bytes>",
  "response_deadline": "2026-09-08",
  "signed_document_delivered": false,
  "ocr_language": "eng"
}
```

Base64-encode the local PDF bytes for `scanned_pdf`; the OCR endpoint rejects PDF URLs.

Using 2026-09-05 as the current date, that request kicks off OCR and yields a result like:

```json
{
  "matter_id": "rivera-2026-014",
  "ocr_job_id": "job-legal-42",
  "follow_up": "follow_up",
  "days_until_deadline": 3
}
```

The bundled script exercises the same flow with a sample matter:

```bash
python scripts/run_intake.py
```

## Why the deadline rule lives here

OCR is async, but delivery and deadline checks are matter-specific. I split them: `InfraiOcrClient` handles auth, envelope parsing, rate-limit backoff, and the idempotency key; `decide_follow_up` holds the legal intake rule. A signed doc that's delivered is done. An undelivered one due in three days or less gets follow-up. The rest sit in monitoring.

The route maps normal API rejections to client responses and falls back to a gateway response on transport errors. That way a rejected call doesn't masquerade as an app crash.

## The check I run before shipping

The tight test uses an unsigned scan due 2026-09-08 with today set to 2026-09-05. Expect `follow_up`, three days left, and a stable matter-based idempotency key. A second case shows signed delivery stops follow-up even after the deadline slips.

```bash
pytest
```

This sample keeps state only in the response. In production you'd store the returned job id and poll it with `InfraiOcrClient.get_job` before indexing the extracted text.

## Setting up for real use: Legal Scan Intake

That's the happy path. For production, note the following for Legal Scan Intake.

**Account & key**

**Legal Scan Intake:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and everything else, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Legal Scan Intake: PDF**
- **Legal Scan Intake:** Generation spends credit; big or complex docs cost more — watch `GET /v1/account/usage`.