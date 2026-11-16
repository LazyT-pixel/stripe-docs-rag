# Eval results

Trap questions (auto-graded): 3/3 correctly declined.
Factual + synthesis questions: 12 — read each one below and judge for yourself; no auto-grade.

## Q1 [factual]
**Question:** Can Stripe monitor a PaymentIntent with webhooks?
**Expected:** Stripe can send webhook events to your server to notify you when the status of a PaymentIntent changes, which you can use for purposes such as determining when to fulfill goods and services.
**Actual:** Yes. Stripe can send webhook events (e.g., `payment_intent.succeeded`, `payment_intent.payment_failed`) to your server whenever a PaymentIntent’s status changes, allowing you to monitor the PaymentIntent and act on those changes [1][4].
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** verifying-status (0.389), handling-payment-events (0.421), verifying-status (0.430)

## Q2 [factual]
**Question:** What should you do when a PaymentIntent event is `processing`?
**Expected:** Wait for the initiated payment to succeed or fail. Only applicable to payment methods with delayed success confirmation.
**Actual:** The provided excerpts describe what the **processing** status means—i.e., it occurs after required actions are complete for an asynchronous payment method and can take a few days to finish—but they do not specify any particular action you should take when you receive a PaymentIntent event with this status. Therefore, the excerpts do not contain enough information to answer the question.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** verifying-status (0.813), verifying-status (0.904), verifying-status (0.916)

## Q3 [factual]
**Question:** What are three example events webhooks let you be notified about, outside your payment flow?
**Expected:** Successful payments (payment_intent.succeeded), disputed payments (charge.dispute.created), and available balance in your Stripe account (balance.available).
**Actual:** Webhooks can notify you about events that happen outside of your own checkout flow, such as:

1. **Successful payments** – the `payment_intent.succeeded` event.  
2. **Disputed payments** – the `charge.dispute.created` event.  
3. **Changes to your account balance** – the `balance.available` event.  

These examples are listed in the webhook documentation [1].
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** handling-payment-events (0.606), verifying-status (0.745), verifying-status (0.762)

## Q4 [factual]
**Question:** What should you do if a single API call triggers a rate limit error?
**Expected:** Wait and try the request again. If you anticipate a large increase in traffic, you can request a limit increase.
**Actual:** If a single API call returns a Stripe::RateLimitError, you should pause and then retry the request — wait a moment and try the call again (often by adding a delay and, if needed, using exponential back‑off). [1]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (0.814), error-handling (0.972), error-handling (1.081)

## Q5 [factual]
**Question:** What is the problem described for a `Stripe::PermissionError`?
**Expected:** The API key used for this request doesn't have the necessary permissions.
**Actual:** The problem described for a **`Stripe::PermissionError`** is that **the API key used for the request does not have the necessary permissions**【1】【2】.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (0.436), error-handling (0.676), error-handling (0.677)

## Q6 [factual]
**Question:** What happens during the `incomplete` subscription status window?
**Expected:** Your customer has 23 hours to pay. This window accommodates customers who pay on-session. If the customer returns after 23 hours, create a new subscription for them.
**Actual:** During the **incomplete** status a subscription is not yet active. The customer must *complete a successful payment* within 23 hours for the subscription to become active. If the payment requires additional steps (for example, customer authentication) or is still pending with a PaymentIntent in the *processing* state, the subscription remains in the incomplete state until those actions are finished [3][5].
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.823), overview (0.835), overview (0.888)

## Q7 [factual]
**Question:** What does the `past_due` subscription status mean?
**Expected:** Payment on the latest finalized invoice either failed or wasn't attempted. The subscription continues to create invoices; Stripe might retry payment but this status doesn't guarantee another attempt.
**Actual:** `past_due` indicates that the payment for the most‑recent **finalized** invoice has either **failed** or **has not been attempted**. While in this state the subscription keeps generating new invoices, and Stripe may try to collect payment again, but the status does **not guarantee** that another attempt will occur.  

What happens next depends on the settings you chose in the Dashboard: after all retry attempts, the subscription can stay `past_due`, or be moved to **canceled** or **unpaid**. If the customer pays the latest invoice, the subscription immediately switches back to **active**, regardless of whether the payment is made before or after the invoice’s due date. When a subscription enters `past_due` you should notify the customer and ask them to update their payment details. [3][4][1]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.608), overview (0.665), webhooks (0.670)

## Q8 [factual]
**Question:** How long does Stripe retry a failing webhook endpoint in live mode?
**Expected:** Up to 3 days with an exponential back-off. In a sandbox, Stripe retries three times over a few hours.
**Actual:** In live mode, Stripe will keep retrying a webhook endpoint that doesn’t respond correctly for **up to 3 days**, using an exponential back‑off strategy. [1][3]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.421), error-handling (0.438), webhooks (0.454)

## Q9 [synthesis]
**Question:** During a live-mode webhook retry window, does Stripe attempt to charge the customer, and what else does it do?
**Expected:** No, Stripe won't attempt to charge the customer during the retry window unless it receives a successful response, and it also sends an email notifying you the webhook is failing.
**Actual:** During a live‑mode webhook retry period Stripe **does not try to charge the customer**; it waits for your endpoint to return a successful response before attempting any payment collection. While it keeps retrying the webhook (up to 3 days with exponential back‑off), Stripe also **sends you an email** to let you know the webhook is failing【2】. In live mode this retry behavior applies to all webhook endpoints on your account【4】.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.456), webhooks (0.545), webhooks (0.576)

## Q10 [synthesis]
**Question:** What's the difference between the `incomplete_expired` and `past_due` subscription statuses?
**Expected:** `incomplete_expired` means the customer didn't make a successful payment within 23 hours of creation, and these subscriptions don't bill customers at all. `past_due` means a later invoice's payment failed or wasn't attempted, and the subscription keeps creating invoices while Stripe may retry.
**Actual:** **`incomplete_expired`**  
* Means the very first payment for the subscription never succeeded.  
* The customer did not make a successful payment within **23 hours** of the subscription’s creation, so the subscription never becomes active and it does not bill the customer.  
* The status exists only so you can track customers who failed to activate their subscriptions.  
[1]

**`past_due`**  
* Means a payment on the **latest finalized invoice** has failed or was not attempted **after the subscription is already active (or after a trial ends)**.  
* The subscription continues to exist and Stripe may retry the payment, but the status does not guarantee another attempt.  
* Paying the latest invoice (or marking it uncollectible) will move the subscription back to **active**.  
[5][4]

**Key difference**

| Aspect | `incomplete_expired` | `past_due` |
|--------|----------------------|------------|
| When it occurs | Immediately after creation, if the initial payment is not completed within 23 hours. | After the subscription is active (or trial ends) when a subsequent invoice payment fails. |
| Billing impact | The subscription never bills the customer. | The subscription continues to generate invoices; billing can resume once the overdue invoice is paid. |
| Path to activation | The subscription cannot become active; you would need to create a new subscription. | The subscription can return to **active** by paying the overdue invoice. |

These distinctions are drawn directly from the documentation excerpts above.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.633), overview (0.744), webhooks (0.745)

## Q11 [synthesis]
**Question:** What's the difference in next steps between an `amount_capturable_updated` event and a `payment_failed` event?
**Expected:** For `amount_capturable_updated`, capture the funds that are available for payment. For `payment_failed`, reach out to the customer through email or push notification and prompt them for another payment method.
**Actual:** I’m sorry, but the provided excerpts do not contain any information about an `amount_capturable_updated` event, so I can’t compare its next‑step guidance to that of a `payment_failed` event.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.862), verifying-status (0.865), webhooks (0.895)

## Q12 [synthesis]
**Question:** How does the recommended response to a connection error differ from the recommended response to a rate-limit error?
**Expected:** For a connection error, turn on automatic retries (Stripe generates idempotency keys for you) and rely on webhooks for the real outcome, since the result of the original call is indeterminate. For a rate-limit error, simply wait and retry, or request a limit increase if you expect sustained higher traffic.
**Actual:** **Connection error** – the docs tell you to make the request *repeatable* so you can safely try again:

* Use an idempotency key when creating or updating an object, then **repeat the request with the same key until you receive a clear success or failure** [3].  
* You can also turn on automatic retries, letting Stripe generate idempotency keys and resend the request when it’s safe [3].

**Rate‑limit error** – the docs advise a *delayed retry* strategy instead of simply resending:

* If a single call hits the limit, **wait and try it again** [1].  
* To handle limits automatically, **retry the call after a delay and increase the delay exponentially** if the error persists [1].  
* For sustained high traffic you can request a higher limit from support [1].

**Key difference**

*For connection errors* you are encouraged to **repeat the original request (with an idempotency key or automatic retries) until you know whether it succeeded or failed**.  
*For rate‑limit errors* you should **wait, then retry with back‑off timing (exponential delay) rather than immediate repetition**, and consider contacting support for a higher limit.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (1.278), error-handling (1.290), error-handling (1.396)

## Q13 [trap (should say "I don't know")]
**Question:** How do I process a refund for a completed charge?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** I’m sorry, but the provided excerpts do not contain information on how to process a refund for a completed charge.
**Auto-verdict:** PASS
**Top retrieved sources:** webhooks (1.111), verifying-status (1.153), webhooks (1.230)

## Q14 [trap (should say "I don't know")]
**Question:** How do I set up Stripe Connect payouts to a connected account?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** The provided excerpts do not contain information about setting up Stripe Connect payouts to a connected account.
**Auto-verdict:** PASS
**Top retrieved sources:** handling-payment-events (0.674), verifying-status (0.840), handling-payment-events (0.862)

## Q15 [trap (should say "I don't know")]
**Question:** What tax rates does Stripe Tax apply to digital goods sold in the EU?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** I’m sorry, but the provided excerpts do not contain information about which tax rates Stripe Tax applies to digital goods sold in the EU.
**Auto-verdict:** PASS
**Top retrieved sources:** webhooks (1.148), webhooks (1.155), verifying-status (1.232)
