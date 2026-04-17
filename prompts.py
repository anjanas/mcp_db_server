"""User prompts for the overdue invoice agent."""

FIND_OVERDUE_INVOICES_OVER_1000 = (
    "Find all overdue invoices that are more than $1000. For each unique customer with such invoices, "
    "get their contact info and send them a notification. Send notifications to all such customers."
)

FIND_FUTURE_INVOICES_COUNT = "Find the number of future invoices."

CUSTOMERS= "List the name of all customers with invoices. Names must be unique"

TOTAL_COST_OF_INVOICES = "Find the total cost of all invoices."

CUSTOMERS_WITH_MULTIPLE_INVOICES = "List the name of all customers with multiple invoices. Names must be unique"

FIND_INVOICES_DELAYED_OVER_2_DAYS_OVER_500 = (
    "Find all invoices that are strictly more than two calendar days overdue (today is more than two days "
    "after the due_date) and have total_cost greater than $500. List the matching invoices "
    "(e.g. invoice_id, customer_id, due_date, total_cost)."
)

LIST_OVERDUE_INVOICES_GROUPED_BY_DAYS_DELAYED = (
    "List all overdue invoices (due_date is before today). For each invoice, compute how many full calendar "
    "days late it is as of today (days between due_date and today). Group the invoices by that number of "
    "days delayed—for example, put every invoice that is exactly 10 days late in one group. Show "
    "invoice_id, customer_id, due_date, total_cost, and days delayed for each invoice, organized by group."
)

# Numbered prompts for command-line selection
PROMPTS = {
    1: FIND_OVERDUE_INVOICES_OVER_1000,
    2: FIND_FUTURE_INVOICES_COUNT,
    3: CUSTOMERS,
    4: TOTAL_COST_OF_INVOICES,
    5: CUSTOMERS_WITH_MULTIPLE_INVOICES,
    6: FIND_INVOICES_DELAYED_OVER_2_DAYS_OVER_500,
    7: LIST_OVERDUE_INVOICES_GROUPED_BY_DAYS_DELAYED,
}
