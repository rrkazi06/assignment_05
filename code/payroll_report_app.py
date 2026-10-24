"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                           (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.
import streamlit as st

from payroll.extract import load_employees, load_export
from payroll import (
    build_history,
    hours_grid,
    missed_weeks,
    pay_by_month,
    summarize_employees
)

st.title("Salt City Coffee — Quarterly Payroll Report")
st.write(
    "Upload the weekly payroll exports for the period you want to review --"
    "old spreadsheet weeks and new app weeks can be mixed. "
    "The roster is loaded automatically.")

uploads = st.file_uploader(
    "Upload weekly payroll exports (CSV)",
    type="csv",
    accept_multiple_files=True,
    key="exports"
)
if not uploads:
    st.stop()

employees = load_employees()
exports = [load_export(f) for f in uploads]
history = build_history(exports, employees)

missing_dept = history[history['department'].isna()]
if not missing_dept.empty:
    ids = ", ".join(missing_dept["employeeid"].unique())
    st.warning(
        f"Warning: {missing_dept.shape[0]} rows have no department "
        f"and were left out: {ids})"
    )
    history = history.dropna(subset=['department'])

dept = st.selectbox(
    "Department",
    ["All"] + history["department"].unique().tolist(),
    key="department"
)

first = history["pay_date"].min().date()
last = history["pay_date"].max().date()
dates = st.date_input("Pay dates", value=(first, last), key="dates")
start, end = dates if len(dates) == 2 else (first, last)

in_dept = (dept == "All") | (history["department"] == dept)
in_range = (history["pay_date"].dt.date >= start) & (history["pay_date"].dt.date <= end)
filtered = history[in_dept & in_range]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Weeks", filtered["week_ending"].nunique())
c2.metric("Employees", filtered["employee_id"].nunique())
c3.metric("Total hours", f"{filtered['hours_worked'].sum():,.2f}")
c4.metric("Total gross pay", f"${filtered['gross_pay'].sum():,.2f}")

st.bar_chart(pay_by_month(filtered), x="month")
st.subheader("Employees")
st.dataframe(summarize_employees(filtered))
st.subheader("Hours by week")
st.caption("0 means the employee was not paid that week.")
grid = hours_grid(filtered)
st.dataframe(grid)

st.subheader("Missed weeks")
st.dataframe(missed_weeks(grid))
st.download_button(
    "Download pay by month for the accountant (CSV)",
    data=pay_by_month(filtered).to_csv(index=False),
    file_name="pay_by_month.csv",
    mime="text/csv",
    key="download",
)
