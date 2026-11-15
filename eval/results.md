# Eval results

Trap questions (auto-graded): 2/3 correctly declined.
Factual + synthesis questions: 12 — read each one below and judge for yourself; no auto-grade.

## Q1 [factual]
**Question:** Can Stripe monitor a PaymentIntent with webhooks?
**Expected:** Stripe can send webhook events to your server to notify you when the status of a PaymentIntent changes, which you can use for purposes such as determining when to fulfill goods and services.
**Actual:** Yes. Stripe can send webhook events (such as `payment_intent.succeeded` or `payment_intent.payment_failed`) to your server so you can monitor a PaymentIntent’s status and act on it — for example, fulfilling goods after a successful payment [1][4].
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** verifying-status (0.389), handling-payment-events (0.421), verifying-status (0.430)

## Q2 [factual]
**Question:** What should you do when a PaymentIntent event is `processing`?
**Expected:** Wait for the initiated payment to succeed or fail. Only applicable to payment methods with delayed success confirmation.
**Actual:** When a PaymentIntent’s status is **`processing`**, the payment has passed any required customer actions but is using an asynchronous payment method (for example, a bank‑debit) that can take several days to complete. At this point you should **continue monitoring the PaymentIntent**—typically via Stripe webhooks (e.g., listening for the `payment_intent.succeeded` or `payment_intent.failed` events) or by periodically retrieving the object—rather than attempting to fulfill the order. Fulfillment should wait until the status changes to **`succeeded`** (or another final state) [5][1].
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** verifying-status (0.813), verifying-status (0.904), verifying-status (0.916)

## Q3 [factual]
**Question:** What are three example events webhooks let you be notified about, outside your payment flow?
**Expected:** Successful payments (payment_intent.succeeded), disputed payments (charge.dispute.created), and available balance in your Stripe account (balance.available).
**Actual:** Webhooks can notify you about events that happen outside of your own checkout flow, such as:

1. A successful payment – `payment_intent.succeeded` [1]  
2. A disputed payment – `charge.dispute.created` [1]  
3. A change to your Stripe account’s available balance – `balance.available` [1]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** handling-payment-events (0.606), verifying-status (0.745), verifying-status (0.762)

## Q4 [factual]
**Question:** What should you do if a single API call triggers a rate limit error?
**Expected:** Wait and try the request again. If you anticipate a large increase in traffic, you can request a limit increase.
**Actual:** If a single API call returns a `Stripe::RateLimitError`, you should pause for a short period and then try the request again. [1]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (0.814), error-handling (0.972), error-handling (1.081)

## Q5 [factual]
**Question:** What is the problem described for a `Stripe::PermissionError`?
**Expected:** The API key used for this request doesn't have the necessary permissions.
**Actual:** The problem for a **`Stripe::PermissionError`** is that **the API key used for the request doesn’t have the necessary permissions**【1】.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (0.436), error-handling (0.676), error-handling (0.677)

## Q6 [factual]
**Question:** What happens during the `incomplete` subscription status window?
**Expected:** Your customer has 23 hours to pay. This window accommodates customers who pay on-session. If the customer returns after 23 hours, create a new subscription for them.
**Actual:** During the **`incomplete`** window a subscription is **not yet active** – it is waiting for the first payment to succeed.

* The customer **must complete a successful payment within 23 hours** of the subscription’s creation; otherwise the subscription will move to `incomplete_expired` [3][5].  
* The status can also appear when the payment **requires customer action**, such as authentication, or when there is a **pending PaymentIntent whose status is `processing`** [3][5].  
* While the subscription is `incomplete`, it is not considered “active” and you should not assume the customer has been billed or that the product can be provisioned until the payment succeeds [3][5].  

So, the `incomplete` period is essentially a short grace period during which Stripe waits for the required first‑payment action to be completed before the subscription can transition to `active`.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.823), overview (0.835), overview (0.888)

## Q7 [factual]
**Question:** What does the `past_due` subscription status mean?
**Expected:** Payment on the latest finalized invoice either failed or wasn't attempted. The subscription continues to create invoices; Stripe might retry payment but this status doesn't guarantee another attempt.
**Actual:** `past_due` indicates that the payment for the subscription’s most‑recent finalized invoice has failed **or** has not been attempted. While in this state the subscription keeps generating invoices, and Stripe may try to collect payment again, but the status does **not** guarantee another attempt. Paying the outstanding invoice (or marking it uncollectible) moves the subscription back to `active`. Because the subscription is no longer in good standing, you should notify the customer and ask them to update their payment details【3†L1-L5】【4†L1-L5】.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.608), overview (0.665), webhooks (0.670)

## Q8 [factual]
**Question:** How long does Stripe retry a failing webhook endpoint in live mode?
**Expected:** Up to 3 days with an exponential back-off. In a sandbox, Stripe retries three times over a few hours.
**Actual:** In live mode, Stripe keeps retrying a webhook that doesn’t respond correctly for **up to 3 days**, using an exponential back‑off schedule. [1][3]
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.421), error-handling (0.438), webhooks (0.454)

## Q9 [synthesis]
**Question:** During a live-mode webhook retry window, does Stripe attempt to charge the customer, and what else does it do?
**Expected:** No, Stripe won't attempt to charge the customer during the retry window unless it receives a successful response, and it also sends an email notifying you the webhook is failing.
**Actual:** During a live‑mode webhook retry window Stripe **does not try to charge the customer**. Instead it keeps retrying the webhook delivery (up to 3 days with exponential back‑off) and also sends you an email notifying you that the webhook is failing【2】. The same retry behavior applies to all webhook endpoints in live mode【4】.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.456), webhooks (0.545), webhooks (0.576)

## Q10 [synthesis]
**Question:** What's the difference between the `incomplete_expired` and `past_due` subscription statuses?
**Expected:** `incomplete_expired` means the customer didn't make a successful payment within 23 hours of creation, and these subscriptions don't bill customers at all. `past_due` means a later invoice's payment failed or wasn't attempted, and the subscription keeps creating invoices while Stripe may retry.
**Actual:** **`incomplete_expired`**

* This status appears when the **initial payment** for a newly‑created subscription fails **and the customer does not make a successful payment within 23 hours** of the subscription’s creation.  
* The subscription never moves to an active state and **does not bill the customer**. It exists only so you can track customers who failed to activate their subscriptions.  
* (Source: [1] – “expired The initial payment on the subscription failed and the customer didn’t make a successful payment within 23 hours of subscription creation… These subscriptions don’t bill customers.”)

**`past_due`**

* This status occurs **after a subscription is already active** when the **most recent finalized invoice** either fails payment or is not attempted.  
* The subscription continues to generate invoices; Stripe may retry payment, but the status does **not guarantee another attempt**.  
* When the customer eventually pays the latest invoice (or the invoice is marked uncollectible), the subscription **returns to `active`** regardless of whether the payment happens before or after the invoice’s due date.  
* (Source: [5] – “Payment on the latest finalized invoice either failed or wasn’t attempted… To reactivate the subscription, have your customer pay the most recent invoice. The subscription status becomes active…”)

### Key differences

| Aspect | `incomplete_expired` | `past_due` |
|--------|----------------------|------------|
| **When it happens** | Immediately after subscription creation, if the **first payment** is not completed within 23 h. | After a subscription is **already active**, when a **subsequent invoice** fails or isn’t attempted. |
| **Billing** | No invoices are billed; the subscription never becomes billable. | Invoices are still created and may be retried; the subscription can be re‑activated by paying the overdue invoice. |
| **State transition** | Remains in this terminal state; the subscription never becomes `active`. | Can transition back to `active` once the overdue invoice is paid (or marked uncollectible). |
| **Purpose** | To track customers who never activated their subscription. | To indicate a payment problem on an existing active subscription and trigger recovery actions. |

Thus, `incomplete_expired` is a **pre‑activation failure** that ends the subscription’s lifecycle, while `past_due` is a **post‑activation payment failure** that can be resolved and the subscription can return to good standing.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** overview (0.633), overview (0.744), webhooks (0.745)

## Q11 [synthesis]
**Question:** What's the difference in next steps between an `amount_capturable_updated` event and a `payment_failed` event?
**Expected:** For `amount_capturable_updated`, capture the funds that are available for payment. For `payment_failed`, reach out to the customer through email or push notification and prompt them for another payment method.
**Actual:** The excerpts you provided do not include any description of the **`amount_capturable_updated`** webhook event, so the documentation does not specify what actions should be taken when that event is received【?】.

For a **`payment_failed`** event (specifically `invoice.payment_failed`), the documentation does list the recommended next steps:

* Notify the customer.  
* If you’re using PaymentIntents, collect new payment information and confirm the PaymentIntent.  
* Update the default payment method on the subscription.  
* Consider enabling Smart Retries.  

These actions are described in the excerpts about handling payment failures【3†L1-L7】【5†L1-L7】.  

**Therefore:**  
- No next‑step guidance is available in the provided excerpts for `amount_capturable_updated`.  
- For `payment_failed`, the next steps are the four actions listed above.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** webhooks (0.862), verifying-status (0.865), webhooks (0.895)

## Q12 [synthesis]
**Question:** How does the recommended response to a connection error differ from the recommended response to a rate-limit error?
**Expected:** For a connection error, turn on automatic retries (Stripe generates idempotency keys for you) and rely on webhooks for the real outcome, since the result of the original call is indeterminate. For a rate-limit error, simply wait and retry, or request a limit increase if you expect sustained higher traffic.
**Actual:** **Rate‑limit error**

- The guidance is to **wait and retry** the call.  
- If you want to automate this, you should **retry after a delay and increase the delay exponentially** if the error keeps occurring.  
- (See [1] “Rate limit errors – Solutions… wait and try it again… retry the API call after a delay, and increase the delay exponentially if the error continues.”)

**Connection (network) error**

- The result of the call is considered **indeterminate** – you must not assume it succeeded or failed.  
- To recover you should **repeat the request using an idempotency key** (or enable Stripe’s automatic retries) until you get a clear success or failure, and then **verify the outcome** by retrieving the object or listening for a webhook.  
- (See [3] “When creating or updating an object, use an idempotency key… repeat the request with the same idempotency key until you receive a clear success or failure… Turn on automatic retries… To find out if it succeeded, you can: Retrieve the relevant object… Listen for webhook notification.”)

**Key difference**

- **Rate‑limit handling** focuses on *delaying* and *back‑off‑retrying* the same request after a short pause.  
- **Connection‑error handling** treats the request as *uncertain* and advises *re‑issuing the request safely* (with idempotency or automatic retries) and then *checking the actual state* of the object or webhook, rather than simply waiting.
**Your verdict:** PASS / FAIL  _(fill in)_
**Top retrieved sources:** error-handling (1.278), error-handling (1.290), error-handling (1.396)

## Q13 [trap (should say "I don't know")]
**Question:** How do I process a refund for a completed charge?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** The excerpts you provided do not contain instructions for actually creating or processing a refund on a completed charge. They only note that when a charge is refunded Stripe will send events such as `charge.refunded` ([1]) and that you can retrieve the related Charge object from those events ([4]), but they do not describe the API call or steps needed to issue the refund itself. Therefore, based on the supplied documentation, I cannot give a detailed procedure for processing a refund.
**Auto-verdict:** FAIL (answered instead of declining) -- or just a decline phrased unusually; read the Actual text before trusting this
**Top retrieved sources:** webhooks (1.111), verifying-status (1.153), webhooks (1.230)

## Q14 [trap (should say "I don't know")]
**Question:** How do I set up Stripe Connect payouts to a connected account?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** I’m sorry, but the excerpts you provided do not contain any information about setting up Stripe Connect payouts to a connected account. Therefore I can’t answer that question based on the given documentation.
**Auto-verdict:** PASS
**Top retrieved sources:** handling-payment-events (0.674), verifying-status (0.840), handling-payment-events (0.862)

## Q15 [trap (should say "I don't know")]
**Question:** What tax rates does Stripe Tax apply to digital goods sold in the EU?
**Expected:** Not covered by the scoped docs — should decline.
**Actual:** I’m sorry, but the provided excerpts do not contain any information about the specific tax rates that Stripe Tax applies to digital goods sold in the EU.
**Auto-verdict:** PASS
**Top retrieved sources:** webhooks (1.148), webhooks (1.155), verifying-status (1.232)
