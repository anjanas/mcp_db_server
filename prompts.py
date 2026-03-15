"""User prompts for the overdue invoice agent."""

FIND_OVERDUE_INVOICES_OVER_1000 = (
    "Find all overdue invoices that are more than $1000. For each unique customer with such invoices, "
    "get their contact info and send them a notification. Send notifications to all such customers."
)

FIND_FUTURE_INVOICES_COUNT = "Find the number of future invoices."

CUSTOMERS= "List the name of all customers with invoices. Names must be unique"

TOTAL_COST_OF_INVOICES = "Find the total cost of all invoices."

CUSTOMERS_WITH_MULTIPLE_INVOICES = "List the name of all customers with multiple invoices. Names must be unique"

# Numbered prompts for command-line selection
PROMPTS = {
    1: FIND_OVERDUE_INVOICES_OVER_1000,
    2: FIND_FUTURE_INVOICES_COUNT,
    3: CUSTOMERS,
    4: TOTAL_COST_OF_INVOICES,
    5: CUSTOMERS_WITH_MULTIPLE_INVOICES,
}
