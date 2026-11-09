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
.block-container {padding-top:2rem; max-width:1200px;}
h1 {font-family:'Instrument Serif',Georgia,serif !important; font-weight:400 !important; font-size:2.9rem !important;
    color:#0E1A2F !important; letter-spacing:-.01em; line-height:1.05 !important; padding:0 !important;}
.dp-bar {font-family:'IBM Plex Mono',monospace; font-size:.78rem; color:#C3CCDB; background:#0E1A2F;
    padding:.55rem 1rem; border-radius:10px; display:flex; justify-content:space-between; margin-bottom:1.1rem;}
.dp-bar b {font-weight:400; color:#fff; background:#17253F; border-radius:20px; padding:0 .6rem;}
.dp-lead {color:#5A5E66; font-size:1rem; margin:.2rem 0 1.2rem;}
.dp-kpi {background:#fff; border:1px solid #D3D9E3; border-radius:12px; padding:.85rem 1rem; height:100%;}
.dp-kpi .l {font-size:.82rem; color:#5A5E66;}
.dp-kpi .v {font-size:1.75rem; font-weight:500; color:#0E1A2F; line-height:1.25; margin:.15rem 0;}
.dp-kpi .c {font-size:.8rem; color:#5A5E66;} .dp-kpi .c.warn {color:#B4531A;}
.dp-msg {background:#0E1A2F; color:#fff; border-radius:12px; padding:1rem 1.25rem; margin:1rem 0 1.4rem; font-size:1.02rem; line-height:1.5;}
.dp-msg .k {display:block; font-family:'IBM Plex Mono',monospace; font-size:.7rem; letter-spacing:.14em; color:#9DB6E3; margin-bottom:.2rem;}
.dp-h {font-weight:600; font-size:1.08rem; color:#0E1A2F; margin:.6rem 0 0;}
.dp-sub {font-size:.84rem; color:#5A5E66; margin:0 0 .4rem;}
.dp-steps {display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:1.4rem;}
.dp-steps div {border:1px solid #D3D9E3; border-radius:12px; padding:.9rem 1rem; font-size:.88rem; color:#3D4047; background:#fff;}
.dp-steps div.r {background:#1E3A6E; color:#fff; border-color:#1E3A6E;}
.dp-steps span {display:block; font-family:'IBM Plex Mono',monospace; font-size:.68rem; letter-spacing:.14em; color:#5A5E66; margin-bottom:.3rem;}
.dp-steps div.r span {color:#9DB6E3;}
.dp-src {font-family:'IBM Plex Mono',monospace; font-size:.78rem; color:#3D4047; line-height:1.9;}
.dp-src i {color:#2E7D4F; font-style:normal; margin-right:.4rem;}
.dp-note {background:#E7EBF2; border-radius:10px; padding:.7rem .9rem; font-size:.8rem; color:#3D4047; margin-top:1rem;}
@media (max-width:700px){ .dp-steps {grid-template-columns:1fr;} h1 {font-size:2.2rem !important;} }
</style>"""


def esc(s) -> str:
    return html.escape(str(s))


def bar(left: str, right: str = "Sample data"):
    st.markdown(f'<div class="dp-bar"><span>{esc(left)}</span><b>{esc(right)}</b></div>', unsafe_allow_html=True)


def kpi(col, label, value, context="", warn=False):
    col.markdown(f'<div class="dp-kpi"><div class="l">{esc(label)}</div><div class="v">{esc(value)}</div>'
                 f'<div class="c{" warn" if warn else ""}">{"⚠ " if warn else ""}{esc(context)}</div></div>',
                 unsafe_allow_html=True)


def message(text_html: str, label="MESSAGE FOR THE MEETING"):
    st.markdown(f'<div class="dp-msg"><span class="k">{label}</span>{text_html}</div>', unsafe_allow_html=True)


def heading(title: str, sub: str = ""):
    st.markdown(f'<p class="dp-h">{esc(title)}</p>' + (f'<p class="dp-sub">{esc(sub)}</p>' if sub else ""),
                unsafe_allow_html=True)


def sources(files):
    st.markdown("<p class='dp-sub' style='letter-spacing:.12em;font-family:IBM Plex Mono'>DATA SOURCES</p>"
                + "".join(f"<div class='dp-src'><i>✓</i>{esc(f)}</div>" for f in files), unsafe_allow_html=True)


def steps(before: str, tool: str, result: str):
    st.markdown(f'<div class="dp-steps"><div><span>1 · BEFORE</span>{before}</div><div><span>2 · THE TOOL</span>{tool}'
                f'</div><div class="r"><span>3 · RESULT</span>{result}</div></div>', unsafe_allow_html=True)


def chart_style(chart):
    return (chart.properties(padding={"left": 8, "right": 8, "top": 4, "bottom": 4}).configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUTED, titleColor=MUTED, labelFont="IBM Plex Sans", titleFont="IBM Plex Sans",
                            labelFontSize=12, titleFontSize=12, gridColor="#EEF1F5", domainColor=LIGHT, tickColor=LIGHT)
            .configure_text(font="IBM Plex Sans"))


# ---------------------------------- UI ----------------------------------
st.set_page_config(page_title="Quote calculator (demo)", page_icon="🧽", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    sources(["price_list_2026.xlsx", "productivity_rates.xlsx"])
    st.markdown("<p class='dp-h' style='margin-top:1.2rem'>Job details</p>", unsafe_allow_html=True)
    client = st.text_input("Client", "Northwind Dental")
    ptype = st.selectbox("Property type", list(PROPERTY_TYPES), index=2)
    area = st.number_input("Area to clean (m²)", 20, 5000, 240, step=10)
    freq = st.selectbox("Frequency", list(FREQUENCIES), index=2)
    extras = st.multiselect("Extras", list(EXTRAS), default=["Window cleaning (inside)", "Restroom supplies refill"])
    with st.expander("Pricing rules (from the spreadsheet)"):
        rate = st.slider("Cleaner rate ($/h)", 25.0, 50.0, DEFAULT_RATE, 0.5)
        st.caption(f"Minimum ${MIN_PER_VISIT:.0f} per visit · travel fee ${TRAVEL_FEE:.0f} · volume discount "
                   "3 % weekly, 7 % twice a week, 12 % daily")
    st.markdown("<div class='dp-note'>Runs locally. Prices and rules stay on your computer.</div>",
                unsafe_allow_html=True)

df, hours, per_visit, visits, disc, monthly, one_off = calculate(area, ptype, freq, extras, rate)
labour_hit_min = hours * rate < MIN_PER_VISIT

# the story: what drives the price, and what would another frequency cost?
pv = df[df["Charged"] == "per visit"].copy()
pv["Monthly"] = pv["Amount ($)"] * visits * (1 - disc)
pv["Share"] = pv["Amount ($)"] / per_visit
top = pv.sort_values("Monthly", ascending=False).iloc[0]
alt_rows = []
for f, v in FREQUENCIES.items():
    _, _, pvv, vv, dd, mm, _ = calculate(area, ptype, f, extras, rate)
    alt_rows.append({"Frequency": f, "Monthly": mm, "Per visit": pvv * (1 - dd), "Chosen": f == freq})
freq_df = pd.DataFrame(alt_rows)
per_visit_net = per_visit * (1 - disc)

bar("quote-tool.local · cleaning quotes")
st.title("Cleaning quote calculator")
st.markdown(f"<p class='dp-lead'>BrightSpace Cleaning (fictional) · a pricing spreadsheet turned into a tool "
            f"sales can use in the client meeting</p>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Monthly price", f"${monthly:,.0f}", f"{freq.lower()}, {visits:.1f} visits")
kpi(k2, "Per visit", f"${per_visit_net:,.2f}",
    f"after {disc:.0%} volume discount" if disc else "no volume discount at this frequency")
kpi(k3, "Cleaner time per visit", f"{hours:.1f} h",
    f"minimum charge of ${MIN_PER_VISIT:.0f} applies" if labour_hit_min else f"{area} m² at {PROPERTY_TYPES[ptype]} m²/h",
    warn=labour_hit_min)
kpi(k4, "Price per m² and month", f"${monthly / area:,.2f}",
    f"plus ${one_off:,.0f} one-off services" if one_off else f"for {area} m² of {ptype.lower()}")

weekly = freq_df.set_index("Frequency").loc["Weekly", "Per visit"] if freq != "Weekly" else None
msg = (f"<b>{esc(client) or 'This client'}</b>: <b>${monthly:,.0f} per month</b> for {freq.lower()} cleaning of "
       f"{area} m². The biggest cost driver is <b>{esc(top['Item'].lower())}</b> ({top['Share']:.0%} of each visit).")
if disc:
    msg += f" The {disc:.0%} volume discount saves the client ${per_visit * visits * disc:,.0f} a month."
if labour_hit_min:
    msg += " The job is so small that the minimum charge applies; offer a lower frequency or bundle sites."
message(msg, "QUOTE IN ONE SENTENCE")

left, right = st.columns([1, 1], gap="large")
with left:
    heading(f"{top['Item']} drives the price", "Monthly cost per item, after discount")
    order = pv.sort_values("Monthly", ascending=False)["Item"].tolist()
    base = alt.Chart(pv).encode(
        y=alt.Y("Item:N", sort=order, title=None, axis=alt.Axis(labelLimit=220, ticks=False, domain=False, labelPadding=8)),
        x=alt.X("Monthly:Q", title=None, axis=None, scale=alt.Scale(domain=[0, pv["Monthly"].max() * 1.25])))
    bars = base.mark_bar(cornerRadiusEnd=3, height=22).encode(
        color=alt.condition(alt.datum.Item == top["Item"], alt.value(NAVY), alt.value(LIGHT)),
        tooltip=[alt.Tooltip("Item"), alt.Tooltip("Monthly", format="$,.0f")])
    labels = base.mark_text(align="left", dx=6, color=BODY, fontSize=12).encode(text=alt.Text("Monthly:Q", format="$,.0f"))
    st.altair_chart(chart_style((bars + labels).properties(height=46 * len(pv) + 10)), use_container_width=True)
with right:
    cheaper = freq_df[(freq_df["Per visit"] < per_visit_net - 0.01)]
    sub = ("Price per visit falls with more visits (volume discount)" if len(cheaper)
           else "This is already the lowest price per visit")
    heading("What other frequencies would cost", sub)
    fb = alt.Chart(freq_df).encode(
        y=alt.Y("Frequency:N", sort=list(FREQUENCIES), title=None, axis=alt.Axis(labelLimit=220, ticks=False, domain=False, labelPadding=8)),
        x=alt.X("Monthly:Q", title=None, axis=None, scale=alt.Scale(domain=[0, freq_df["Monthly"].max() * 1.9])))
    fbars = fb.mark_bar(cornerRadiusEnd=3, height=22).encode(
        color=alt.condition(alt.datum.Chosen, alt.value(NAVY), alt.value(LIGHT)),
        tooltip=[alt.Tooltip("Frequency"), alt.Tooltip("Monthly", format="$,.0f"),
                 alt.Tooltip("Per visit", format="$,.2f")])
    ftext = fb.mark_text(align="left", dx=6, color=BODY, fontSize=12).encode(
        text=alt.Text("label:N")).transform_calculate(
        label="datum.Frequency == 'One-off' ? format(datum.Monthly, '$,.0f') + ' once' : format(datum.Monthly, '$,.0f') + ' a month  ·  ' + format(datum['Per visit'], '$,.0f') + ' per visit'")
    st.altair_chart(chart_style((fbars + ftext).properties(height=46 * len(freq_df) + 10)),
                    use_container_width=True)

heading("Line items", "Exactly what goes on the quote")
st.dataframe(df, hide_index=True, use_container_width=True,
             column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f")})

b1, b2 = st.columns(2)
b1.download_button("Download PDF quote", pdf_quote(client, ptype, area, freq, df, per_visit, visits,
                                                    disc, monthly, one_off),
                   file_name=f"quote_{client.replace(' ', '_') or 'client'}.pdf", mime="application/pdf",
                   type="primary", use_container_width=True)
b2.download_button("Download Excel breakdown", excel_file(df, {"Client": client, "Property": ptype, "Area m2": area,
                                                               "Frequency": freq, "Per visit $": round(per_visit, 2),
                                                               "Monthly $": round(monthly, 2), "One-off $": one_off}),
                   file_name="quote_breakdown.xlsx", use_container_width=True)

steps("Prices lived in a spreadsheet only one person understood. Every quote took a call to the office.",
      "Reads the same rules, asks five questions, and produces the quote, the PDF and the Excel file.",
      "Sales quotes on the spot. Try it: switch to <b>every weekday</b> and see the discount kick in.")
