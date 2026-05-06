# Daily Klaviyo Report — Spec

## Overview
A manually-triggered slash command (`/daily-klaviyo`) that pulls a per-client
Klaviyo email-performance snapshot from the **Hiro Analytics MCP**, renders a
markdown table in the Claude window, and posts the same content as a Slack DM.

The earlier approach (direct Klaviyo + Postscript APIs writing to Google Sheets
on a GitHub Actions cron) was scrapped because the data it produced was not
accurate. The Hiro MCP is the source of truth.

## Trigger
- **Manual:** user runs `/daily-klaviyo` each morning around 8am Central.
- No scheduler. No GitHub Action. No headless Claude.

## Clients
- Call Hiro `list_clients`.
- Include all clients **except** "AJ Banned".
- One row per client.

## Metrics (columns)
1. Revenue By Channel — Email
2. Email Subscribes
3. Email Unsubscribes
4. Email Campaign Open Rate
5. Email Campaign Click Rate

For each metric, include a **% Change** column comparing the report day to the
same weekday one week prior.

## Time window
- **Tuesday–Friday:** report covers **yesterday**, compared to the same weekday
  one week prior. One table.
- **Monday:** report covers **Friday, Saturday, and Sunday** as three separate
  single-day tables. Each day is compared to that same weekday one week prior
  (Fri vs. prior Fri, Sat vs. prior Sat, Sun vs. prior Sun).
  - Rationale: Friday data isn't fully populated until Saturday, and the
    weekend isn't reported live, so Monday catches up on all three.

## Output

### In-window
- Plain markdown table(s), one row per client.
- Caption above each table noting the date(s) covered.
- Sort rows by attributed/email revenue descending.
- Currency formatted with `$` and commas; rates as `XX.XX%`.

### Slack
- Posted as a DM to the user via the Slack connector (added via Claude
  connector — not an incoming webhook).
- Same content as the in-window table, formatted as a fixed-width code block
  so columns align in Slack (Slack does not render markdown tables).

## Open items for next session
- Confirm the Slack connector exposes a `post_message` (or similar) tool to a
  DM target after session restart.
- Identify the exact Hiro field names for the 5 metrics so the prompt can
  request them precisely (likely via `get_performance` with explicit `fields`,
  since the 5 metrics include engagement metrics that are not in the default
  revenue overview).
- Decide whether the slash command lives at `.claude/commands/daily-klaviyo.md`
  or as a saved prompt elsewhere.
