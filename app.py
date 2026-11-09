"""Quote calculator demo for a fictional cleaning company.

DataPhil demo - all company names, prices and rules are made up.
Run locally:  uv run --with streamlit --with fpdf2 --with pandas --with openpyxl streamlit run app.py
"""
import html
import io
from datetime import date, timedelta

import altair as alt
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


# ---------------------------------- look & feel (same palette as dataphil.dev) ----------------------------------
NAVY, INK, BODY, MUTED = "#1E3A6E", "#0E1A2F", "#3D4047", "#5A5E66"
GREY, LIGHT, PAPER, WARN = "#9AA3B2", "#D3D9E3", "#F4F5F8", "#B4531A"

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Instrument+Serif&display=swap');
html, body, .stApp, .stMarkdown, p, label, button, input, textarea, select, li {font-family:'IBM Plex Sans',system-ui,sans-serif;}
.block-container {padding-top:2.2rem; max-width:1180px;}
h1 {font-family:'Instrument Serif',Georgia,serif !important; font-weight:400 !important; font-size:2.8rem !important;
    color:#0E1A2F !important; letter-spacing:-.01em; line-height:1.05 !important; padding:0 !important;}
.dp-lead {color:#5A5E66; font-size:1.02rem; margin:.35rem 0 1.5rem; max-width:48rem;}
.dp-lead b {color:#0E1A2F; font-weight:500;}
.dp-chip {font-family:'IBM Plex Mono',monospace; font-size:.7rem; letter-spacing:.08em; color:#1E3A6E;
    background:#E7EBF2; border-radius:20px; padding:.15rem .6rem; margin-left:.5rem; vertical-align:middle; white-space:nowrap;}
.dp-step {font-family:'IBM Plex Mono',monospace; font-size:.72rem !important; letter-spacing:.14em; color:#5A5E66; margin:0 0 .5rem;}
.dp-answer {background:#0E1A2F; color:#fff; border-radius:14px; padding:1.15rem 1.4rem 1.25rem; margin-bottom:.9rem;}
.dp-answer .k {font-family:'IBM Plex Mono',monospace; font-size:.7rem; letter-spacing:.14em; color:#9DB6E3;}
.dp-answer .big {font-family:'Instrument Serif',Georgia,serif; font-size:3.1rem; line-height:1.05; margin:.25rem 0 .55rem;}
.dp-answer .big.warn {color:#F2B48C;}
.dp-answer p {color:#D6DEEB; margin:0; font-size:1rem; line-height:1.55;}
.dp-answer p b {color:#fff; font-weight:500;}
.dp-kpi {background:#fff; border:1px solid #D3D9E3; border-radius:12px; padding:.75rem 1rem; height:100%;}
.dp-kpi .l {font-size:.82rem; color:#5A5E66;}
.dp-kpi .v {font-size:1.5rem; font-weight:500; color:#0E1A2F; line-height:1.25; margin:.1rem 0;}
.dp-kpi .c {font-size:.8rem; color:#5A5E66;} .dp-kpi .c.warn {color:#B4531A;}
.dp-h {font-weight:600; font-size:1.05rem; color:#0E1A2F; margin:0; padding-top:1.3rem;}
.dp-sub {font-size:.84rem; color:#5A5E66; margin:0 0 .4rem;}
.dp-try {font-size:.84rem; color:#3D4047; background:#E7EBF2; border-radius:10px; padding:.6rem .8rem; margin-top:.4rem;}
.dp-note {font-size:.78rem; color:#5A5E66; margin-top:.5rem;}
.dp-list {margin:.2rem 0 0; padding-left:1.1rem; color:#3D4047; font-size:.92rem; line-height:1.7;}
.dp-list b {color:#0E1A2F; font-weight:500;}
@media (max-width:700px){ h1 {font-size:2.1rem !important;} .dp-answer .big {font-size:2.4rem;} }
</style>"""


def esc(s) -> str:
    return html.escape(str(s))


def header(title: str, lead_html: str, sample: bool = True):
    st.title(title)
    chip = '<span class="dp-chip">SAMPLE DATA</span>' if sample else ""
    st.markdown(f'<p class="dp-lead">{lead_html}{chip}</p>', unsafe_allow_html=True)


def step(label: str, where=st):
    where.markdown(f'<p class="dp-step">{esc(label)}</p>', unsafe_allow_html=True)


def answer(label: str, big: str, text_html: str, warn=False, where=st):
    """The one thing the user came for: a big number or verdict, and one sentence that explains it."""
    where.markdown(f'<div class="dp-answer"><span class="k">{esc(label)}</span>'
                   f'<div class="big{" warn" if warn else ""}">{esc(big)}</div><p>{text_html}</p></div>',
                   unsafe_allow_html=True)


def kpi(col, label, value, context="", warn=False):
    col.markdown(f'<div class="dp-kpi"><div class="l">{esc(label)}</div><div class="v">{esc(value)}</div>'
                 f'<div class="c{" warn" if warn else ""}">{"⚠ " if warn else ""}{esc(context)}</div></div>',
                 unsafe_allow_html=True)


def heading(title: str, sub: str = "", where=st):
    where.markdown(f'<p class="dp-h">{esc(title)}</p>' + (f'<p class="dp-sub">{esc(sub)}</p>' if sub else ""),
                   unsafe_allow_html=True)


def try_hint(text_html: str, where=st):
    where.markdown(f'<div class="dp-try"><b>Try it:</b> {text_html}</div>', unsafe_allow_html=True)


def note(text: str, where=st):
    where.markdown(f'<div class="dp-note">{esc(text)}</div>', unsafe_allow_html=True)


def chart_style(chart):
    return (chart.properties(padding={"left": 8, "right": 8, "top": 4, "bottom": 4}).configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUTED, titleColor=MUTED, labelFont="IBM Plex Sans", titleFont="IBM Plex Sans",
                            labelFontSize=12, titleFontSize=12, gridColor="#EEF1F5", domainColor=LIGHT, tickColor=LIGHT)
            .configure_text(font="IBM Plex Sans"))


# ---------------------------------- UI ----------------------------------
st.set_page_config(page_title="Quote calculator (demo)", page_icon="🧽", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

header("What do we charge this client?",
       "A cleaning company's pricing spreadsheet, turned into a tool for the sales meeting. "
       "<b>Enter the job, get the monthly price and a PDF quote.</b>")

left, right = st.columns([1, 2], gap="large")

with left:
    step("1 · THE JOB")
    with st.container(border=True):
        client = st.text_input("Client", "Northwind Dental")
        ptype = st.selectbox("Property type", list(PROPERTY_TYPES), index=2)
        area = st.number_input("Area to clean (m²)", 20, 5000, 240, step=10)
        freq = st.selectbox("How often", list(FREQUENCIES), index=1)
        extras = st.multiselect("Extras", list(EXTRAS), default=["Window cleaning (inside)"])
        with st.expander("Pricing rules"):
            rate = st.slider("Cleaner rate ($/h)", 25.0, 50.0, DEFAULT_RATE, 0.5)
            st.caption(f"Minimum ${MIN_PER_VISIT:.0f} per visit · travel ${TRAVEL_FEE:.0f} per visit · "
                       "volume discount 3 % weekly, 7 % twice a week, 12 % every weekday")
    try_hint("change <b>How often</b> to every weekday and watch the price per visit drop.", left)
    note("Fictional company, made-up prices. In a real project the rules come from your spreadsheet.", left)

df, hours, per_visit, visits, disc, monthly, one_off = calculate(area, ptype, freq, extras, rate)
per_visit_net = per_visit * (1 - disc)
labour_hit_min = hours * rate < MIN_PER_VISIT
alt_rows = []
for f in FREQUENCIES:
    _, _, pvv, vv, dd, mm, _ = calculate(area, ptype, f, extras, rate)
    alt_rows.append({"Frequency": f, "Monthly": mm, "Per visit": pvv * (1 - dd), "Chosen": f == freq})
freq_df = pd.DataFrame(alt_rows)

with right:
    step("2 · THE QUOTE")
    once = freq == "One-off"
    text = (f"{'One visit' if once else freq + ' cleaning'} of {area} m² ({ptype.lower()}) for "
            f"<b>{esc(client) or 'this client'}</b>"
            + (f", {visits:.1f} visits a month" if not once else "")
            + (f", including a {disc:.0%} volume discount." if disc else ".")
            + (f" Plus <b>${one_off:,.0f}</b> once for one-off services." if one_off else ""))
    if labour_hit_min:
        text += " The job is small, so the minimum charge per visit applies."
    answer("PRICE PER MONTH" if not once else "PRICE", f"${monthly:,.0f}", text)

    k1, k2 = st.columns(2)
    kpi(k1, "Price per visit", f"${per_visit_net:,.2f}",
        f"after {disc:.0%} volume discount" if disc else "no volume discount at this frequency")
    if one_off:
        kpi(k2, "One-off services", f"${one_off:,.0f}", "billed once with the first invoice")
    else:
        kpi(k2, "Cleaner time per visit", f"{hours:.1f} h", f"{area} m² at {PROPERTY_TYPES[ptype]} m² per hour",
            warn=labour_hit_min)

    st.write("")
    b1, b2 = st.columns([3, 2])
    b1.download_button("Download the PDF quote", pdf_quote(client, ptype, area, freq, df, per_visit, visits,
                                                           disc, monthly, one_off),
                       file_name=f"quote_{client.replace(' ', '_') or 'client'}.pdf", mime="application/pdf",
                       type="primary", use_container_width=True)
    b2.download_button("Excel breakdown", excel_file(df, {"Client": client, "Property": ptype, "Area m2": area,
                                                          "Frequency": freq, "Per visit $": round(per_visit, 2),
                                                          "Monthly $": round(monthly, 2), "One-off $": one_off}),
                       file_name="quote_breakdown.xlsx", use_container_width=True)

    heading("If the client asks for more or fewer visits",
            "Monthly price for each frequency. More visits cost more per month but less per visit.")
    fb = alt.Chart(freq_df).encode(
        y=alt.Y("Frequency:N", sort=list(FREQUENCIES), title=None,
                axis=alt.Axis(labelLimit=200, ticks=False, domain=False, labelPadding=8)),
        x=alt.X("Monthly:Q", title=None, axis=None, scale=alt.Scale(domain=[0, freq_df["Monthly"].max() * 1.9])))
    fbars = fb.mark_bar(cornerRadiusEnd=3, height=20).encode(
        color=alt.condition(alt.datum.Chosen, alt.value(NAVY), alt.value(LIGHT)),
        tooltip=[alt.Tooltip("Frequency"), alt.Tooltip("Monthly", format="$,.0f"),
                 alt.Tooltip("Per visit", format="$,.2f")])
    ftext = fb.mark_text(align="left", dx=6, color=BODY, fontSize=12).encode(
        text=alt.Text("label:N")).transform_calculate(
        label="datum.Frequency == 'One-off' ? format(datum.Monthly, '$,.0f') + ' once' : "
              "format(datum.Monthly, '$,.0f') + ' a month  ·  ' + format(datum['Per visit'], '$,.0f') + ' per visit'")
    st.altair_chart(chart_style((fbars + ftext).properties(height=40 * len(freq_df) + 6)), use_container_width=True)

    with st.expander("How the price is calculated (line items)"):
        st.dataframe(df, hide_index=True, use_container_width=True,
                     column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f")})
        st.caption(f"Cleaner time per visit: {hours:.1f} h ({area} m² at {PROPERTY_TYPES[ptype]} m² per hour). "
                   f"Price per visit before discount: ${per_visit:,.2f}.")
