# Shopify → Customer.io Webhook Setup

How to wire Shopify store events (orders, checkouts, customers, etc.) into
Customer.io webhook-triggered campaigns, so store activity can trigger
messaging workflows without middleware (no Zapier, no custom server).

Store: **1776 Health** (`1776rx.health`)

## How the two sides fit together

```
Shopify event (e.g. orders/create)
        │  POST, JSON payload
        ▼
Customer.io webhook trigger URL   (unique per campaign)
        │
        ▼
Customer.io workflow: Create/Update Person → Send Event → downstream campaigns
```

- **Customer.io** generates a unique webhook URL when you create a
  webhook-triggered campaign. It accepts JSON in any shape — Shopify's raw
  webhook payload works as-is, no transformation layer needed.
- **Shopify** sends webhooks as `POST` requests with a JSON body and signs
  each request with an HMAC header (`X-Shopify-Hmac-Sha256`). Customer.io
  doesn't verify Shopify HMACs, but the trigger URL itself is unguessable,
  which is the standard level of protection for this integration.

## Step 1 — Create the webhook-triggered campaign in Customer.io

Done in the Customer.io UI (Journeys workspace):

1. Go to **Campaigns → Create Campaign** and choose **Webhook** as the
   trigger type.
2. Customer.io shows a unique **webhook URL** — copy it. Each campaign gets
   its own URL, so plan one campaign per Shopify topic (one for
   `orders/create`, one for `checkouts/create`, etc.).
3. Send a **sample payload** to that URL (Shopify's "Send test notification"
   button in admin does this — see Step 2) so Customer.io can learn the
   payload shape and let you map fields.
4. In the campaign's trigger settings, map an **identifier** from the
   payload to a person. For Shopify order payloads use `email` (top level)
   or `customer.email`; for customer payloads use `email`.
5. In the workflow, add actions:
   - **Create or Update Person** — upsert the shopper into the workspace
     using the mapped email, and copy attributes (name, total_spent, tags).
   - **Send Event** — convert the webhook into a Customer.io event (e.g.
     `shopify_order_placed`) that can trigger downstream messaging
     campaigns, segments, and metrics.

Docs: https://docs.customer.io/journeys/webhook-triggered-campaigns/

## Step 2 — Point Shopify at the Customer.io URL

Two options. Option A is simplest for a merchant-owned store; Option B is
what we can run via the Admin API from this session.

### Option A: Shopify admin (no code)

1. Shopify admin → **Settings → Notifications → Webhooks** (bottom of page).
2. **Create webhook** → pick the event (e.g. *Order creation*), format
   **JSON**, and paste the Customer.io webhook URL.
3. Use **Send test notification** to fire a sample at Customer.io (this is
   the sample payload Step 1.3 needs).

Note: admin-created webhooks are shop-level and won't show up in API
listings — that's expected, per Shopify's docs.

### Option B: GraphQL Admin API

The REST `/admin/api/.../webhooks.json` resource still works but is legacy
(REST Admin API is legacy as of Oct 2024). New setups should use GraphQL:

```graphql
mutation webhookSubscriptionCreate(
  $topic: WebhookSubscriptionTopic!
  $webhookSubscription: WebhookSubscriptionInput!
) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
    webhookSubscription { id topic format uri }
    userErrors { field message }
  }
}
```

Variables (one call per topic):

```json
{
  "topic": "ORDERS_CREATE",
  "webhookSubscription": {
    "uri": "https://<customer.io-webhook-url-for-this-campaign>",
    "format": "JSON"
  }
}
```

Caveat: API-created subscriptions belong to the app whose token created
them, and require that app to have the matching access scope (e.g.
`read_orders` for order topics). If the app is ever uninstalled, its
webhooks go with it — another reason Option A is the safer default here.

## Useful topics for messaging automations

| Shopify topic (REST / GraphQL enum) | Fires when | Typical Customer.io use |
| --- | --- | --- |
| `orders/create` / `ORDERS_CREATE` | Order placed | Post-purchase flow, cross-sell |
| `orders/paid` / `ORDERS_PAID` | Payment captured | Receipt/confirmation journeys |
| `orders/fulfilled` / `ORDERS_FULFILLED` | Order shipped | Shipping notification, review ask |
| `checkouts/create` + `checkouts/update` / `CHECKOUTS_*` | Checkout started/changed | Abandoned checkout recovery |
| `customers/create` / `CUSTOMERS_CREATE` | New customer account | Welcome series |
| `customers/update` / `CUSTOMERS_UPDATE` | Profile changed | Keep person attributes in sync |
| `refunds/create` / `REFUNDS_CREATE` | Refund issued | Winback / feedback flow |

## Gotchas

- **One URL per campaign.** Don't point multiple Shopify topics at the same
  Customer.io campaign URL — payload shapes differ and the field mapping
  will break. One topic → one webhook-triggered campaign.
- **Respond-fast requirement.** Shopify retries a webhook 8 times over ~4
  hours if it doesn't get a 2xx within 5 seconds, then may delete the
  subscription after 13 consecutive failed deliveries. Customer.io's
  ingestion endpoint answers immediately, so this only matters if a URL is
  pasted wrong — double-check with a test notification.
- **Guest checkouts** can lack `customer.email` on some events; the
  top-level `email` field on order payloads is the more reliable identifier.
- **Abandoned checkout logic lives on the Customer.io side.** Shopify only
  tells you a checkout was created/updated; the "wait 1 hour, exit if an
  order event arrived" logic is built in the Customer.io workflow.
