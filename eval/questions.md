# Eval set

15 questions covering the scoped doc areas (Payments, Webhooks,
Subscriptions, Errors). Fill in expected answers once ingestion is done —
write these from the docs directly, not from memory, so they're a fair
ground truth.

Aim for a mix:
- ~8 questions with a clear, factual answer directly in the docs
- ~4 questions requiring synthesis across 2+ chunks
- ~3 "trap" questions that sound answerable but aren't covered by your
  scoped doc set — these test whether the tool correctly says "I don't know"

| # | Question | Expected answer | Category |
|---|----------|------------------|----------|
| 1 | Can Stripe monitor a PaymentIntent with webhooks? | Stripe can send webhook events to your server to notify you when the status of a PaymentIntent changes, which you can use for purposes such as determining when to fulfill goods and services. | factual |
| 2 | What should you do when a PaymentIntent event is `processing`? | Wait for the initiated payment to succeed or fail. Only applicable to payment methods with delayed success confirmation. | factual |
| 3 | What are three example events webhooks let you be notified about, outside your payment flow? | Successful payments (payment_intent.succeeded), disputed payments (charge.dispute.created), and available balance in your Stripe account (balance.available). | factual |
| 4 | What should you do if a single API call triggers a rate limit error? | Wait and try the request again. If you anticipate a large increase in traffic, you can request a limit increase. | factual |
| 5 | What is the problem described for a `Stripe::PermissionError`? | The API key used for this request doesn't have the necessary permissions. | factual |
| 6 | What happens during the `incomplete` subscription status window? | Your customer has 23 hours to pay. This window accommodates customers who pay on-session. If the customer returns after 23 hours, create a new subscription for them. | factual |
| 7 | What does the `past_due` subscription status mean? | Payment on the latest finalized invoice either failed or wasn't attempted. The subscription continues to create invoices; Stripe might retry payment but this status doesn't guarantee another attempt. | factual |
| 8 | How long does Stripe retry a failing webhook endpoint in live mode? | Up to 3 days with an exponential back-off. In a sandbox, Stripe retries three times over a few hours. | factual |
| 9 | During a live-mode webhook retry window, does Stripe attempt to charge the customer, and what else does it do? | No, Stripe won't attempt to charge the customer during the retry window unless it receives a successful response, and it also sends an email notifying you the webhook is failing. | synthesis |
| 10 | What's the difference between the `incomplete_expired` and `past_due` subscription statuses? | `incomplete_expired` means the customer didn't make a successful payment within 23 hours of creation, and these subscriptions don't bill customers at all. `past_due` means a later invoice's payment failed or wasn't attempted, and the subscription keeps creating invoices while Stripe may retry. | synthesis |
| 11 | What's the difference in next steps between an `amount_capturable_updated` event and a `payment_failed` event? | For `amount_capturable_updated`, capture the funds that are available for payment. For `payment_failed`, reach out to the customer through email or push notification and prompt them for another payment method. | synthesis |
| 12 | How does the recommended response to a connection error differ from the recommended response to a rate-limit error? | For a connection error, turn on automatic retries (Stripe generates idempotency keys for you) and rely on webhooks for the real outcome, since the result of the original call is indeterminate. For a rate-limit error, simply wait and retry, or request a limit increase if you expect sustained higher traffic. | synthesis |
| 13 | How do I process a refund for a completed charge? | Not covered by the scoped docs — should decline. | trap (should say "I don't know") |
| 14 | How do I set up Stripe Connect payouts to a connected account? | Not covered by the scoped docs — should decline. | trap (should say "I don't know") |
| 15 | What tax rates does Stripe Tax apply to digital goods sold in the EU? | Not covered by the scoped docs — should decline. | trap (should say "I don't know") |
