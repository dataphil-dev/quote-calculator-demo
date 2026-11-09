"""Quote calculator demo for a fictional cleaning company.

DataPhil demo - all company names, prices and rules are made up.
Run locally:  uv run --with streamlit --with fpdf2 --with pandas --with openpyxl streamlit run app.py
"""
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from fpdf import FPDF

COMPANY = "BrightSpace Cleaning (demo)"

# ---- Pricing rules: in a real project these come from the client's spreadsheet ----
PROPERTY_TYPES = {  # m² a cleaner manages per hour
    "Office": 180,
    "Shop / retail": 150,
    "Medical practice": 110,
    "Apartment building (common areas)": 200,
}
FREQUENCIES = {  # visits per month
    "One-off": 1,
    "Weekly": 4.33,
    "Twice a week": 8.66,
    "Every weekday": 21.7,
}
EXTRAS = {  # name: (type, price)  type = "per_visit" | "per_m2" | "one_off"
    "Window cleaning (inside)": ("per_m2", 0.35),
    "Carpet deep clean": ("one_off", 180.0),
    "Kitchen / break room": ("per_visit", 12.0),
    "Restroom supplies refill": ("per_visit", 6.5),
}
DEFAULT_RATE = 34.0      # $ per cleaner hour
MIN_PER_VISIT = 60.0     # minimum charge per visit
TRAVEL_FEE = 9.0         # per visit


def volume_discount(visits_per_month: float) -> float:
    if visits_per_month >= 20:
        return 0.12
    if visits_per_month >= 8:
        return 0.07
    if visits_per_month >= 4:
        return 0.03
    return 0.0


def calculate(area, ptype, freq, extras, rate):
    hours = area / PROPERTY_TYPES[ptype]
    labour = max(hours * rate, MIN_PER_VISIT)
    lines = [("Cleaning labour", f"{hours:.1f} h × ${rate:.2f}", labour, "per visit"),
             ("Travel fee", "flat", TRAVEL_FEE, "per visit")]
    one_off = 0.0
    for name in extras:
        kind, price = EXTRAS[name]
        if kind == "per_m2":
            lines.append((name, f"{area:.0f} m² × ${price:.2f}", area * price, "per visit"))
        elif kind == "per_visit":
            lines.append((name, "flat", price, "per visit"))
        else:
            lines.append((name, "once", price, "one-off"))
            one_off += price
    per_visit = sum(l[2] for l in lines if l[3] == "per visit")
    visits = FREQUENCIES[freq]
    disc = volume_discount(visits)
    monthly = per_visit * visits * (1 - disc)
    df = pd.DataFrame(lines, columns=["Item", "Basis", "Amount ($)", "Charged"])
    return df, hours, per_visit, visits, disc, monthly, one_off


def pdf_quote(client, ptype, area, freq, df, per_visit, visits, disc, monthly, one_off) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, COMPANY, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Quote for: {client or 'Client'}    Date: {date.today():%d %b %Y}    "
                   f"Valid until: {date.today() + timedelta(days=30):%d %b %Y}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{ptype}, {area:.0f} m², {freq.lower()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    for w, h in zip((80, 50, 30, 30), ("Item", "Basis", "Amount", "Charged")):
        pdf.cell(w, 8, h, border="B")
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for _, r in df.iterrows():
        pdf.cell(80, 7, r["Item"])
        pdf.cell(50, 7, r["Basis"].replace("×", "x"))
        pdf.cell(30, 7, f"${r['Amount ($)']:.2f}", align="R")
        pdf.cell(30, 7, r["Charged"])
        pdf.ln()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Per visit: ${per_visit:.2f}   x {visits:.1f} visits/month   "
                   f"volume discount {disc:.0%}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, f"Monthly total: ${monthly:,.2f}", new_x="LMARGIN", new_y="NEXT")
    if one_off:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Plus one-off services: ${one_off:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, "Demo quote with made-up prices. Built by DataPhil as an example of a "
                         "spreadsheet turned into a simple web tool.")
    return bytes(pdf.output())


def excel_file(df, summary: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Breakdown", index=False)
        pd.DataFrame(list(summary.items()), columns=["Key", "Value"]).to_excel(
            xw, sheet_name="Summary", index=False)
    return buf.getvalue()


# ---------------------------------- UI ----------------------------------
st.set_page_config(page_title="Quote calculator (demo)", page_icon="🧽", layout="wide")
st.title("Cleaning quote calculator")
st.caption(f"{COMPANY} · demo with made-up prices and rules")

with st.sidebar:
    st.header("1  Job details")
    client = st.text_input("Client name", "Northwind Dental")
    ptype = st.selectbox("Property type", list(PROPERTY_TYPES), index=2)
    area = st.number_input("Area to clean (m²)", 20, 5000, 240, step=10)
    freq = st.selectbox("Frequency", list(FREQUENCIES), index=2)
    extras = st.multiselect("Extras", list(EXTRAS), default=["Window cleaning (inside)", "Restroom supplies refill"])
    with st.expander("Pricing rules"):
        rate = st.slider("Cleaner rate ($/h)", 25.0, 50.0, DEFAULT_RATE, 0.5)
        st.write(f"Minimum per visit: ${MIN_PER_VISIT:.0f} · travel fee ${TRAVEL_FEE:.0f}")
        st.write("Volume discount: 3 % from weekly, 7 % from twice a week, 12 % daily")

df, hours, per_visit, visits, disc, monthly, one_off = calculate(area, ptype, freq, extras, rate)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Per visit", f"${per_visit:,.2f}")
c2.metric("Monthly total", f"${monthly:,.2f}", f"-{disc:.0%} volume discount" if disc else None, delta_color="inverse")
c3.metric("Cleaner hours / visit", f"{hours:.1f} h")
c4.metric("One-off extras", f"${one_off:,.2f}")

left, right = st.columns([3, 2])
with left:
    st.subheader("Breakdown")
    st.dataframe(df, hide_index=True, use_container_width=True,
                 column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f")})
with right:
    st.subheader("Monthly cost by item")
    per_month = df[df["Charged"] == "per visit"].set_index("Item")["Amount ($)"] * visits * (1 - disc)
    st.bar_chart(per_month, horizontal=True, color="#14a800")

st.subheader("2  Send the quote")
b1, b2 = st.columns(2)
b1.download_button("Download PDF quote", pdf_quote(client, ptype, area, freq, df, per_visit, visits,
                                                    disc, monthly, one_off),
                   file_name=f"quote_{client.replace(' ', '_') or 'client'}.pdf", mime="application/pdf",
                   type="primary", use_container_width=True)
b2.download_button("Download Excel", excel_file(df, {"Client": client, "Property": ptype, "Area m2": area,
                                                     "Frequency": freq, "Per visit $": round(per_visit, 2),
                                                     "Monthly $": round(monthly, 2), "One-off $": one_off}),
                   file_name="quote_breakdown.xlsx", use_container_width=True)
