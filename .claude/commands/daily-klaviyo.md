---
description: Pull the daily Klaviyo email-performance report from the Hiro Analytics MCP and post it to Slack.
---

# Daily Klaviyo Report

Run the daily Klaviyo email report. Full spec lives at `reports/SPEC.md` —
read it if anything below is ambiguous.

## Steps

### 1. Determine the report window
Today's date is the current date in **America/Chicago (Central)** time.

- If today is **Monday**: produce **three** separate single-day reports for
  the prior **Friday, Saturday, and Sunday**. Each day is compared to that
  same weekday one week earlier (Fri vs. prior Fri, Sat vs. prior Sat,
  Sun vs. prior Sun).
- Otherwise (Tue–Sun, though normally only Tue–Fri): produce **one** report
  for **yesterday**, compared to the same weekday one week earlier.

### 2. Get the client list
Call the Hiro MCP `list_clients` tool. Build the working list by **excluding
the client named "AJ Banned"** (case-insensitive match). Every remaining
client gets one row per table.

### 3. Pull the metrics
For each client and each report day, retrieve these five metrics with
same-day-prior-week comparison:

1. **Revenue By Channel — Email** (email-attributed revenue)
2. **Email Subscribes**
3. **Email Unsubscribes**
4. **Email Campaign Open Rate**
5. **Email Campaign Click Rate**

Use `get_performance` (or whichever Hiro tool exposes these). Because four of
the five metrics are non-revenue engagement metrics, you **must** pass an
explicit `fields` parameter naming the metrics you want — the default revenue
overview will not include subscribes/unsubscribes/open/click. If you're
unsure of the exact field identifiers, call `list_metrics` first to discover
them, then pass them through.

Request the comparison window so the response includes both current-period
and previous-period values for each metric.

### 4. Render in-window
Output one markdown table per report day. Above each table, include a
caption with the date range, e.g. `**2026-05-05** vs. **2026-04-28**`.

Table requirements (per Hiro MCP display rules):
- One row per client.
- Use `_field_labels` from the response as column headers.
- Show all returned data fields as columns.
- After **every** metric column, add a `% Change` column.
- Currency: `$1,234.56` with the response's currency symbol.
- Rates/percentages: 1–2 decimals with `%`.
- Sort rows by attributed/email revenue **descending**.

On Mondays this means three tables stacked in the response: Friday first,
then Saturday, then Sunday.

### 5. Post to Slack
Send the same content as a **direct message to the user** via the Slack
connector. The exact tool name depends on which Slack connector is
installed — look for an MCP tool that posts to Slack (e.g. one named like
`*slack*post*` or `*slack*send*`) and use it. If multiple Slack tools are
available, prefer the one that posts to a user/DM target rather than a
channel.

Format the Slack payload as a fixed-width **code block** (triple backticks)
because Slack does not render markdown tables — column alignment only works
inside a code block. Include the same caption(s) above each code block.

Title the Slack message: `Daily Klaviyo Report — <date or date range>`.

If no Slack tool is available in the current session, surface that clearly
to the user with a one-line note ("Slack connector not loaded in this
session — printed in-window only") and continue with the in-window output
rather than failing.

### 6. Confirm
After posting, print a one-line confirmation in the Claude window with the
Slack destination and the dates covered. Done.

## Notes
- Do **not** create artifacts, canvases, or HTML dashboards. Plain markdown
  tables only, per Hiro MCP display rules.
- Do **not** add summary cards, KPI sections, or commentary above the
  table(s). The table(s) are the response.
- Do not include metrics the user didn't ask for (no extra engagement
  metrics, no retention, no subscriber totals beyond subscribes/unsubscribes).
