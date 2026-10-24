import math
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# HydrogenOrg HPRS Rail Research Simulator V1.1
# Dedicated rail application — research / scenario model only.
# ============================================================

st.set_page_config(
    page_title="HydrogenOrg HPRS Rail Research Simulator",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
HERO_IMG = ASSETS / "hprs_rail_hero.png"
REACTOR_IMG = ASSETS / "reactor_v4.png"
SCHEME_IMG = ASSETS / "plasma_water_splitting.png"

# -----------------------------
# Physical / thermodynamic refs
# -----------------------------
H2_LHV_KWH_KG = 33.3
WATER_KG_PER_KG_H2_STOICH = 18.01528 / 2.016  # 2 H2O -> 2 H2 + O2
O2_KG_PER_KG_H2_STOICH = 31.998 / (2.0 * 2.016)
WATER_SPLIT_DG_KWH_PER_KG_H2 = 32.67
WATER_SPLIT_DH_KWH_PER_KG_H2 = 39.38
GRAVITY_M_S2 = 9.80665
AIR_DENSITY_KG_M3 = 1.225

# Public guideposts: contextual only, never used as hidden calibration.
PUBLIC_RANGE_KM = 460.0
PUBLIC_MAX_SPEED_KMH = 127.0
PUBLIC_REFUEL_MIN = 30.0
PUBLIC_SEATS = 116
PUBLIC_DAILY_KM_LOW = 480.0
PUBLIC_DAILY_KM_HIGH = 600.0

# -----------------------------
# Language
# -----------------------------
LANG = st.sidebar.selectbox("Sprache / Language", ["Deutsch", "English"], index=0)
DE = LANG == "Deutsch"

def t(de: str, en: str) -> str:
    return de if DE else en

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
      :root{
        --ink:#071521; --paper:#f8fbfd; --muted:#60788a; --cyan:#19b6ee; --green:#6bc247;
        --orange:#f59e42; --line:#d9e6ee; --soft:#f3f8fb; --navy:#07111e; --page:#0b111a;
      }
      /* V1.1: keep the rail simulator readable even when Streamlit/browser uses dark mode. */
      .stApp, [data-testid="stAppViewContainer"]{background:var(--page);color:#eef7fb;}
      [data-testid="stSidebar"]{background:#20232d;}
      .block-container{max-width:1480px;padding-top:1rem;padding-bottom:3rem;}
      h1,h2,h3,h4{color:#f4fbff !important;}
      p, li{color:#d4e1e8;}
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{color:#aebfca !important;}
      .hprs-kicker{font-size:.78rem;letter-spacing:.14rem;font-weight:900;color:var(--green);text-transform:uppercase;}
      .hprs-title{font-size:2.8rem;line-height:1.02;font-weight:950;color:#f7fcff;margin:.25rem 0 .6rem;}
      .hprs-title span{color:var(--cyan);}
      .hprs-sub{font-size:1.05rem;line-height:1.65;color:#a9c0cf;max-width:1050px;}
      .hprs-card{border:1px solid var(--line);border-radius:18px;background:#fff;padding:1rem 1.1rem;box-shadow:0 10px 28px rgba(0,0,0,.18);color:var(--ink);}
      .hprs-card h1,.hprs-card h2,.hprs-card h3,.hprs-card h4{color:var(--ink) !important;}
      .hprs-card p,.hprs-card li,.hprs-card .hprs-small{color:#526b7c !important;}
      .hprs-note{border-left:4px solid var(--cyan);background:#edf8fd;border-radius:10px;padding:.85rem 1rem;color:#2f5c73;line-height:1.55;}
      .hprs-note b{color:#173d50;}
      .hprs-warn{border-left:4px solid var(--orange);background:#fff4e8;border-radius:10px;padding:.85rem 1rem;color:#684928;line-height:1.55;}
      .hprs-warn b{color:#4e3218;}
      .hprs-dark{background:#06111f;color:#fff;border:1px solid #1a3346;border-radius:16px;padding:1rem 1.15rem;}
      .hprs-dark b{color:#7dd3fc;}
      .hprs-chip{display:inline-block;border:1px solid var(--line);background:#fff;border-radius:999px;padding:.32rem .6rem;margin:.18rem .22rem .18rem 0;font-size:.76rem;font-weight:800;color:var(--ink);}
      .hprs-small{font-size:.82rem;color:#9fb5c3;line-height:1.5;}

      /* Metric cards: force high contrast independent of Streamlit theme. */
      div[data-testid="stMetric"]{
        background:#f9fcfe !important;
        border:1px solid #cfe0ea !important;
        padding:.9rem .95rem !important;
        border-radius:16px !important;
        box-shadow:0 8px 20px rgba(0,0,0,.16);
        min-height:112px;
      }
      div[data-testid="stMetric"] *{color:var(--ink) !important;}
      div[data-testid="stMetricLabel"]{font-weight:800 !important;}
      div[data-testid="stMetricLabel"] p{
        color:#526b7c !important;
        font-size:.82rem !important;
        line-height:1.22 !important;
      }
      div[data-testid="stMetricValue"]{font-weight:900 !important;}
      div[data-testid="stMetricValue"] > div,
      div[data-testid="stMetricValue"] span{
        color:#071521 !important;
        font-size:1.65rem !important;
        line-height:1.08 !important;
      }
      div[data-testid="stMetricDelta"] *{color:#1e7c48 !important;}

      /* Dataframes/charts remain native, but text controls stay readable on dark canvas. */
      .stTabs [data-baseweb="tab"]{font-weight:800;}
      .stMarkdown a{color:#55c8f3;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Hero
# -----------------------------
st.markdown(
    f"""
    <div class="hprs-kicker">HYDROGENORG · HPRS RAIL RESEARCH PLATFORM</div>
    <div class="hprs-title">{t('PLASMA + WASSERSTOFF FÜR DIE <span>SCHIENE.</span>', 'PLASMA + HYDROGEN FOR <span>RAIL.</span>')}</div>
    <div class="hprs-sub">
      {t(
        'Ein eigenständiger Forschungs-Simulator für Regionalzüge: Fahrmission, Brennstoffzelle/Batterie, H₂-Bedarf, Depot-HPRS-W, thermische Rückgewinnung und die Frage, ob ein Onboard-Plasmareaktor energetisch überhaupt schließen kann.',
        'A dedicated research simulator for regional rail: mission energy, fuel-cell/battery hybridization, hydrogen demand, depot HPRS-W, heat recovery, and whether an onboard plasma reactor can close energetically at all.'
      )}
    </div>
    """,
    unsafe_allow_html=True,
)

if HERO_IMG.exists():
    st.image(str(HERO_IMG), use_container_width=True)

st.markdown(
    f"""
    <div class="hprs-note">
      <b>{t('Wissenschaftliche Grenze:', 'Scientific boundary:')}</b>
      {t(
        'Dieses Modell ist ein First-Order-Szenario, kein homologierter Zugdynamik-, Sicherheits- oder Reaktornachweis. Öffentlich bekannte Rail-Werte dienen nur als Kontext. Fahrzeugmasse, H₂-Speicher, Brennstoffzellenleistung und Batteriekapazität sind frei editierbare Annahmen.',
        'This model is a first-order scenario, not a homologation-grade train-dynamics, safety, or reactor validation model. Public rail figures are context only. Vehicle mass, hydrogen storage, fuel-cell power and battery capacity are editable assumptions.'
      )}
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.header(t("1 · Fahrmission", "1 · Rail mission"))
mission_km = st.sidebar.number_input(t("Missionsdistanz (km)", "Mission distance (km)"), 10.0, 1000.0, 100.0, 10.0)
daily_km = st.sidebar.number_input(t("Tagesleistung (km/Tag)", "Daily distance (km/day)"), 10.0, 2000.0, 500.0, 10.0)
mass_t = st.sidebar.number_input(t("Zugmasse — Szenario (t)", "Train mass — scenario (t)"), 40.0, 500.0, 120.0, 5.0)
cruise_kmh = st.sidebar.slider(t("Rechengeschwindigkeit Widerstände (km/h)", "Cruise speed for resistance (km/h)"), 30, 160, 100, 5)
avg_kmh = st.sidebar.slider(t("Mittlere Missionsgeschwindigkeit inkl. Stops (km/h)", "Average mission speed incl. stops (km/h)"), 20, 140, 65, 5)
cycle_speed_kmh = st.sidebar.slider(t("Beschleunigungs-/Bremszyklus (km/h)", "Acceleration/braking cycle speed (km/h)"), 30, 140, 80, 5)
accel_m_s2 = st.sidebar.slider(t("Spitzenbeschleunigung (m/s²)", "Peak acceleration (m/s²)"), 0.2, 1.2, 0.6, 0.05)
stops_per_100 = st.sidebar.slider(t("Bahnhofsstopps pro 100 km", "Station stops per 100 km"), 0, 30, 8, 1)
elevation_m_100 = st.sidebar.number_input(t("Positiver Höhengewinn pro 100 km (m)", "Positive elevation gain per 100 km (m)"), 0.0, 3000.0, 300.0, 50.0)

with st.sidebar.expander(t("Fahrzeugwiderstände", "Vehicle resistance"), expanded=False):
    crr = st.number_input(t("Rollwiderstandskoeffizient", "Rolling-resistance coefficient"), 0.0005, 0.0050, 0.0015, 0.0001, format="%.4f")
    cda_m2 = st.number_input(t("Aerodynamisches CdA (m²)", "Aerodynamic CdA (m²)"), 2.0, 30.0, 8.0, 0.5)
    drive_eff = st.slider(t("DC-Bus → Rad Wirkungsgrad (%)", "DC-bus → wheel efficiency (%)"), 75, 98, 92, 1) / 100.0
    regen_eff = st.slider(t("Rekuperation Ende-zu-Ende (%)", "End-to-end regenerative recovery (%)"), 0, 90, 70, 5) / 100.0
    aux_kw = st.number_input(t("Mittlere Nebenverbraucher/HVAC (kW)", "Average auxiliaries/HVAC (kW)"), 0.0, 500.0, 80.0, 10.0)

st.sidebar.markdown("---")
st.sidebar.header(t("2 · Fuel Cell + Batterie", "2 · Fuel cell + battery"))
fc_eff = st.sidebar.slider(t("Fuel-Cell-Systemwirkungsgrad H₂-LHV → DC (%)", "Fuel-cell system efficiency H₂ LHV → DC (%)"), 30, 65, 45, 1) / 100.0
fc_nominal_kw = st.sidebar.number_input(t("Fuel-Cell Nennleistung netto (kW)", "Fuel-cell net nominal power (kW)"), 50.0, 3000.0, 400.0, 25.0)
battery_kwh = st.sidebar.number_input(t("Nutzbare Traktionsbatterie (kWh)", "Usable traction battery (kWh)"), 10.0, 3000.0, 250.0, 10.0)
h2_storage_kg = st.sidebar.number_input(t("Nutzbarer H₂-Speicher an Bord (kg)", "Usable onboard H₂ storage (kg)"), 10.0, 2000.0, 120.0, 10.0)
grid_to_dc_eff = st.sidebar.slider(t("Netz/Oberleitung → DC-Bus (%)", "Grid/catenary → DC-bus efficiency (%)"), 75, 99, 94, 1) / 100.0

st.sidebar.markdown("---")
st.sidebar.header(t("3 · HPRS-W Reaktor", "3 · HPRS-W reactor"))
reactor_preset = st.sidebar.radio(
    t("Reaktor-Szenario", "Reactor scenario"),
    [t("Aktueller Forschungs-Punkt", "Current research point"), t("Prototype Target", "Prototype target"), t("Benutzerdefiniert", "Custom")],
    index=0,
)

if reactor_preset == t("Aktueller Forschungs-Punkt", "Current research point"):
    plasma_kwh_gross = 50.0
    h2_recovery = 0.838
    external_heat_kwh_gross = 5.0
elif reactor_preset == t("Prototype Target", "Prototype target"):
    plasma_kwh_gross = 41.0
    h2_recovery = 0.90
    external_heat_kwh_gross = 2.43
else:
    plasma_kwh_gross = st.sidebar.slider(t("Plasma-Strom (kWh/kg H₂ brutto)", "Plasma electricity (kWh/kg gross H₂)"), 30.0, 80.0, 50.0, 0.5)
    h2_recovery = st.sidebar.slider(t("Gesamte H₂-Recovery (%)", "Total H₂ recovery (%)"), 50, 99, 84, 1) / 100.0
    external_heat_kwh_gross = st.sidebar.slider(t("Externe Prozesswärme (kWhₜₕ/kg H₂ brutto)", "External process heat (kWhₜₕ/kg gross H₂)"), 0.0, 20.0, 5.0, 0.5)

st.sidebar.caption(
    t(
        f"Aktiv: Plasma {plasma_kwh_gross:.1f} kWh/kg brutto · H₂-Recovery {100*h2_recovery:.1f}% · externe Wärme {external_heat_kwh_gross:.2f} kWh/kg brutto",
        f"Active: plasma {plasma_kwh_gross:.1f} kWh/kg gross · H₂ recovery {100*h2_recovery:.1f}% · external heat {external_heat_kwh_gross:.2f} kWh/kg gross",
    )
)

st.sidebar.markdown("---")
st.sidebar.header(t("4 · Kosten", "4 · Costs"))
electricity_chf_kwh = st.sidebar.number_input(t("Strompreis (CHF/kWh)", "Electricity price (CHF/kWh)"), 0.0, 1.5, 0.277, 0.01, format="%.3f")
h2_price_chf_kg = st.sidebar.number_input(t("Gelieferter H₂-Preis (CHF/kg)", "Delivered hydrogen price (CHF/kg)"), 0.0, 40.0, 10.0, 0.5)
heat_price_chf_kwh = st.sidebar.number_input(t("Externe Wärme (CHF/kWhₜₕ)", "External heat price (CHF/kWhₜₕ)"), 0.0, 1.5, 0.0, 0.01, format="%.3f")
water_price_chf_m3 = st.sidebar.number_input(t("Wasserpreis (CHF/m³)", "Water price (CHF/m³)"), 0.0, 20.0, 2.0, 0.5)

# -----------------------------
# Rail physics
# -----------------------------
mass_kg = mass_t * 1000.0
distance_m = mission_km * 1000.0
cruise_ms = cruise_kmh / 3.6
cycle_ms = cycle_speed_kmh / 3.6
trip_h = mission_km / max(avg_kmh, 1e-9)

f_roll = mass_kg * GRAVITY_M_S2 * crr
f_aero = 0.5 * AIR_DENSITY_KG_M3 * cda_m2 * cruise_ms**2
steady_wheel_kwh = (f_roll + f_aero) * distance_m / 3.6e6

climb_m = elevation_m_100 * mission_km / 100.0
climb_wheel_kwh = mass_kg * GRAVITY_M_S2 * climb_m / 3.6e6
descent_recovered_kwh = climb_wheel_kwh * regen_eff

cycle_count = max(1.0, stops_per_100 * mission_km / 100.0)
kinetic_cycle_kwh = 0.5 * mass_kg * cycle_ms**2 / 3.6e6
accel_wheel_kwh = cycle_count * kinetic_cycle_kwh
brake_recovered_kwh = accel_wheel_kwh * regen_eff

positive_wheel_kwh = steady_wheel_kwh + climb_wheel_kwh + accel_wheel_kwh
recovered_dc_kwh = descent_recovered_kwh + brake_recovered_kwh
traction_dc_kwh = max(positive_wheel_kwh / max(drive_eff, 1e-9) - recovered_dc_kwh, 0.0)
aux_kwh = aux_kw * trip_h
dc_bus_kwh = traction_dc_kwh + aux_kwh
dc_kwh_km = dc_bus_kwh / max(mission_km, 1e-9)
avg_dc_kw = dc_bus_kwh / max(trip_h, 1e-9)

# Peak proxy.
f_res_cycle = mass_kg * GRAVITY_M_S2 * crr + 0.5 * AIR_DENSITY_KG_M3 * cda_m2 * cycle_ms**2
peak_wheel_kw = (mass_kg * accel_m_s2 + f_res_cycle) * cycle_ms / 1000.0
peak_dc_kw = peak_wheel_kw / max(drive_eff, 1e-9) + aux_kw
battery_peak_kw = max(peak_dc_kw - fc_nominal_kw, 0.0)
battery_peak_minutes = battery_kwh / battery_peak_kw * 60.0 if battery_peak_kw > 0 else math.inf

# Stored hydrogen pathway.
h2_mission_kg = dc_bus_kwh / max(fc_eff * H2_LHV_KWH_KG, 1e-9)
h2_kg_km = h2_mission_kg / max(mission_km, 1e-9)
h2_daily_kg = h2_kg_km * daily_km
h2_range_km = h2_storage_kg / max(h2_kg_km, 1e-12)
h2_tank_energy_kwh_km = h2_kg_km * H2_LHV_KWH_KG
h2_cost_chf_km = h2_kg_km * h2_price_chf_kg

# Direct electric reference.
direct_external_kwh = dc_bus_kwh / max(grid_to_dc_eff, 1e-9)
direct_kwh_km = direct_external_kwh / max(mission_km, 1e-9)
direct_cost_chf_km = direct_kwh_km * electricity_chf_kwh

# HPRS-W depot pathway.
gross_h2_kg = h2_mission_kg / max(h2_recovery, 1e-12)
reactor_electric_kwh = gross_h2_kg * plasma_kwh_gross
reactor_heat_kwh = gross_h2_kg * external_heat_kwh_gross
reactor_total_kwh = reactor_electric_kwh + reactor_heat_kwh
reactor_kwh_km = reactor_total_kwh / max(mission_km, 1e-9)
water_mission_l = gross_h2_kg * WATER_KG_PER_KG_H2_STOICH
water_l_km = water_mission_l / max(mission_km, 1e-9)
o2_mission_kg = gross_h2_kg * O2_KG_PER_KG_H2_STOICH

reactor_cost_chf = (
    reactor_electric_kwh * electricity_chf_kwh
    + reactor_heat_kwh * heat_price_chf_kwh
    + water_mission_l / 1000.0 * water_price_chf_m3
)
reactor_cost_chf_km = reactor_cost_chf / max(mission_km, 1e-9)
reactor_to_dc_eff = dc_bus_kwh / max(reactor_total_kwh, 1e-12)

# Delivered-H2 basis for thermodynamic and onboard loop checks.
reactor_total_per_delivered_h2 = (plasma_kwh_gross + external_heat_kwh_gross) / max(h2_recovery, 1e-12)
reactor_exergy_proxy_per_delivered = (plasma_kwh_gross + 0.20 * external_heat_kwh_gross) / max(h2_recovery, 1e-12)
thermo_energy_ok = (plasma_kwh_gross + external_heat_kwh_gross) >= WATER_SPLIT_DH_KWH_PER_KG_H2
thermo_exergy_ok = (plasma_kwh_gross + 0.20 * external_heat_kwh_gross) >= WATER_SPLIT_DG_KWH_PER_KG_H2
fc_dc_per_delivered_h2 = H2_LHV_KWH_KG * fc_eff
onboard_margin = fc_dc_per_delivered_h2 - reactor_total_per_delivered_h2
onboard_ratio = fc_dc_per_delivered_h2 / max(reactor_total_per_delivered_h2, 1e-12)

# Cost break-even HPRS-W electricity price vs bought H2.
non_electric_cost_chf = reactor_heat_kwh * heat_price_chf_kwh + water_mission_l / 1000.0 * water_price_chf_m3
break_even_electricity = (
    (h2_mission_kg * h2_price_chf_kg - non_electric_cost_chf) / reactor_electric_kwh
    if reactor_electric_kwh > 0 else math.inf
)

# -----------------------------
# Public guideposts
# -----------------------------
st.markdown("---")
st.subheader(t("Öffentlicher Rail-Kontext", "Public rail context"))
p1, p2, p3, p4 = st.columns(4)
p1.metric(t("Öffentlich angegebene Reichweite", "Public advertised range"), f">{PUBLIC_RANGE_KM:.0f} km")
p2.metric(t("Max. Geschwindigkeit", "Maximum speed"), f"{PUBLIC_MAX_SPEED_KMH:.0f} km/h")
p3.metric(t("Betankung", "Refuelling"), f"<{PUBLIC_REFUEL_MIN:.0f} min")
p4.metric(t("Sitzplätze", "Seats"), f"{PUBLIC_SEATS}")
st.caption(
    t(
        f"Kontext: öffentlich beschriebener SBCTA-Einsatz ungefähr {PUBLIC_DAILY_KM_LOW:.0f}–{PUBLIC_DAILY_KM_HIGH:.0f} km/Tag. Diese Werte werden nicht benutzt, um vertrauliche Zugparameter abzuleiten.",
        f"Context: publicly described SBCTA duty roughly {PUBLIC_DAILY_KM_LOW:.0f}–{PUBLIC_DAILY_KM_HIGH:.0f} km/day. These values are not used to infer proprietary train parameters.",
    )
)

# -----------------------------
# Mission summary
# -----------------------------
st.markdown("---")
st.subheader(t("1 · Rail Mission — Energie & Hybridisierung", "1 · Rail mission — energy & hybridization"))
m1, m2, m3, m4 = st.columns(4)
m1.metric(t("DC-Bus Energie / Mission", "DC-bus energy / mission"), f"{dc_bus_kwh:.0f} kWh")
m2.metric(t("Elektrische Intensität", "Electrical intensity"), f"{dc_kwh_km:.2f} kWh/km")
m3.metric(t("Mittlere DC-Leistung", "Average DC demand"), f"{avg_dc_kw:.0f} kW")
m4.metric(t("Peak-DC Proxy", "Peak DC proxy"), f"{peak_dc_kw:.0f} kW")

m5, m6, m7, m8 = st.columns(4)
m5.metric(t("H₂ / Mission", "H₂ / mission"), f"{h2_mission_kg:.1f} kg")
m6.metric(t("H₂-Intensität", "H₂ intensity"), f"{h2_kg_km:.3f} kg/km")
m7.metric(t("Reichweite aus H₂-Speicher", "Range from H₂ storage"), f"{h2_range_km:.0f} km")
m8.metric(t("H₂ / Tag", "H₂ / day"), f"{h2_daily_kg:.1f} kg/day")

st.markdown(
    f"""
    <div class="hprs-note">
      <b>{t('Hybrid-Interpretation:', 'Hybrid interpretation:')}</b>
      {t(
        f'Die gewählte Fuel-Cell-Nennleistung beträgt {fc_nominal_kw:.0f} kW. Der First-Order-Peak liegt bei {peak_dc_kw:.0f} kW; die Batterie puffert damit ungefähr {battery_peak_kw:.0f} kW. Bei voller Peak-Unterstützung entspräche die nutzbare Batterie grob {battery_peak_minutes:.1f} min.' if math.isfinite(battery_peak_minutes) else f'Die gewählte Fuel-Cell-Nennleistung beträgt {fc_nominal_kw:.0f} kW und deckt den berechneten Peak-Proxy ab.',
        f'The selected fuel-cell nominal power is {fc_nominal_kw:.0f} kW. The first-order peak is {peak_dc_kw:.0f} kW; the battery therefore buffers about {battery_peak_kw:.0f} kW. At full peak support the usable battery corresponds to roughly {battery_peak_minutes:.1f} min.' if math.isfinite(battery_peak_minutes) else f'The selected fuel-cell nominal power is {fc_nominal_kw:.0f} kW and covers the calculated peak proxy.'
      )}
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Architecture comparison
# -----------------------------
st.markdown("---")
st.subheader(t("2 · Drei Rail-Architekturen im Vergleich", "2 · Three rail architectures compared"))

comparison = pd.DataFrame(
    [
        {
            t("Pfad", "Pathway"): t("Direkt elektrisch / Oberleitung", "Direct electric / catenary"),
            t("Energieinput (kWh/km)", "Energy input (kWh/km)"): direct_kwh_km,
            t("H₂ (kg/km)", "H₂ (kg/km)"): 0.0,
            t("Energiekosten (CHF/km)", "Energy cost (CHF/km)"): direct_cost_chf_km,
            t("Wasser (L/km)", "Water (L/km)"): 0.0,
        },
        {
            t("Pfad", "Pathway"): t("Gelieferter H₂ → Fuel Cell", "Delivered H₂ → fuel cell"),
            t("Energieinput (kWh/km)", "Energy input (kWh/km)"): h2_tank_energy_kwh_km,
            t("H₂ (kg/km)", "H₂ (kg/km)"): h2_kg_km,
            t("Energiekosten (CHF/km)", "Energy cost (CHF/km)"): h2_cost_chf_km,
            t("Wasser (L/km)", "Water (L/km)"): 0.0,
        },
        {
            t("Pfad", "Pathway"): t("Depot HPRS-W → H₂ → Fuel Cell", "Depot HPRS-W → H₂ → fuel cell"),
            t("Energieinput (kWh/km)", "Energy input (kWh/km)"): reactor_kwh_km,
            t("H₂ (kg/km)", "H₂ (kg/km)"): h2_kg_km,
            t("Energiekosten (CHF/km)", "Energy cost (CHF/km)"): reactor_cost_chf_km,
            t("Wasser (L/km)", "Water (L/km)"): water_l_km,
        },
    ]
)

st.dataframe(
    comparison.style.format({
        t("Energieinput (kWh/km)", "Energy input (kWh/km)"): "{:.2f}",
        t("H₂ (kg/km)", "H₂ (kg/km)"): "{:.3f}",
        t("Energiekosten (CHF/km)", "Energy cost (CHF/km)"): "{:.2f}",
        t("Wasser (L/km)", "Water (L/km)"): "{:.3f}",
    }),
    use_container_width=True,
    hide_index=True,
)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"##### {t('Energieinput pro Zug-km', 'Energy input per train-km')}")
    chart_energy = comparison[[t("Pfad", "Pathway"), t("Energieinput (kWh/km)", "Energy input (kWh/km)")]].set_index(t("Pfad", "Pathway"))
    st.bar_chart(chart_energy, height=320)
with c2:
    st.markdown(f"##### {t('Modellierte Energiekosten', 'Modeled energy cost')}")
    chart_cost = comparison[[t("Pfad", "Pathway"), t("Energiekosten (CHF/km)", "Energy cost (CHF/km)")]].set_index(t("Pfad", "Pathway"))
    st.bar_chart(chart_cost, height=320)

# -----------------------------
# Reactor visual + thermodynamics
# -----------------------------
st.markdown("---")
st.subheader(t("3 · HPRS-W Plasma Reactor Core", "3 · HPRS-W plasma reactor core"))
rv1, rv2 = st.columns([1.15, 0.85], gap="large")
with rv1:
    if REACTOR_IMG.exists():
        st.image(str(REACTOR_IMG), use_container_width=True)
with rv2:
    st.markdown(
        f"""
        <div class="hprs-card">
          <div class="hprs-kicker">REACTOR DIAGNOSTIC</div>
          <h3>{t('Vom Wasser zum H₂ — aber mit Energierechnung.', 'From water to H₂ — with the energy balance exposed.')}</h3>
          <p class="hprs-small">
          {t(
              'Der Rail-Simulator behandelt HPRS-W als externe H₂-Produktionsstufe. Plasmaenergie, Wärme und H₂-Recovery bleiben explizite Annahmen. Ein DC-Feld kann geladene Spezies beeinflussen; die reale H₂/O₂-Trennung und Rekombinationskinetik müssen experimentell validiert werden.',
              'The rail simulator treats HPRS-W as an external hydrogen-production stage. Plasma electricity, heat and H₂ recovery remain explicit assumptions. A DC field can influence charged species; actual H₂/O₂ separation and recombination kinetics require experimental validation.'
          )}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

r1, r2, r3, r4 = st.columns(4)
r1.metric(t("ΔG reversibel", "Reversible ΔG"), f"{WATER_SPLIT_DG_KWH_PER_KG_H2:.2f} kWh/kg H₂")
r2.metric(t("ΔH thermoneutral", "Thermoneutral ΔH"), f"{WATER_SPLIT_DH_KWH_PER_KG_H2:.2f} kWh/kg H₂")
r3.metric(t("Reaktorenergie / H₂ geliefert", "Reactor energy / delivered H₂"), f"{reactor_total_per_delivered_h2:.1f} kWh/kg")
r4.metric(t("HPRS-W → Fuel-Cell DC", "HPRS-W → fuel-cell DC"), f"{100*reactor_to_dc_eff:.1f}%")

if thermo_energy_ok and thermo_exergy_ok:
    st.success(t("Der gewählte Reaktorpunkt verletzt die einfachen Standardzustands-Energie-/Exergie-Grenzen nicht.", "The selected reactor point does not violate the simple standard-state energy/exergy guards."))
else:
    st.error(t("Der gewählte Reaktorpunkt verletzt mindestens eine einfache Standardzustands-Grenze. Diese Kombination sollte nicht als physikalisch zulässiges Ziel interpretiert werden.", "The selected reactor point violates at least one simple standard-state guard. Do not interpret this combination as a physically admissible target."))

# -----------------------------
# Process diagram
# -----------------------------
st.markdown("---")
st.subheader(t("4 · Prozessarchitektur — Plasma, Quench, Separation", "4 · Process architecture — plasma, quench, separation"))
if SCHEME_IMG.exists():
    st.image(str(SCHEME_IMG), use_container_width=True)
st.markdown(
    f"""
    <div class="hprs-warn">
      <b>{t('Interpretationsgrenze:', 'Interpretation boundary:')}</b>
      {t(
        'Die Abbildung ist eine ideale Forschungsarchitektur. Sie ist kein validierter Reaktorentwurf und keine Aussage, dass neutrale H₂/O₂-Moleküle nach der Rekombination direkt durch ein DC-Feld getrennt werden können.',
        'The figure is an ideal research architecture. It is not a validated reactor design and does not claim that neutral H₂/O₂ molecules can be directly separated by a DC field after recombination.'
      )}
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Depot vs onboard diagnosis
# -----------------------------
st.markdown("---")
st.subheader(t("5 · Depot-HPRS-W oder Onboard?", "5 · Depot HPRS-W or onboard?"))
d1, d2, d3, d4 = st.columns(4)
d1.metric(t("Depot-HPRS Energie", "Depot HPRS energy"), f"{reactor_kwh_km:.2f} kWh/km")
d2.metric(t("H₂-Recovery", "H₂ recovery"), f"{100*h2_recovery:.1f}%")
d3.metric(t("Wasserbedarf", "Water makeup"), f"{water_l_km:.3f} L/km")
d4.metric(t("O₂ Nebenprodukt / Mission", "O₂ coproduct / mission"), f"{o2_mission_kg:.1f} kg")

if onboard_margin >= 0:
    st.success(
        t(
            f"Onboard-Energiediagnose: Fuel Cell liefert {fc_dc_per_delivered_h2:.1f} kWh DC pro kg H₂; HPRS-W benötigt {reactor_total_per_delivered_h2:.1f} kWh/kg geliefert. Einfacher Energie-Margin: +{onboard_margin:.1f} kWh/kg. Das wäre noch kein Nachweis eines selbsttragenden Systems.",
            f"Onboard energy diagnostic: the fuel cell returns {fc_dc_per_delivered_h2:.1f} kWh DC per kg H₂; HPRS-W requires {reactor_total_per_delivered_h2:.1f} kWh/kg delivered. Simple energy margin: +{onboard_margin:.1f} kWh/kg. This would still not demonstrate a self-sustaining system."
        )
    )
else:
    st.error(
        t(
            f"Onboard-Selbstversorgung schließt nicht: Fuel Cell ≈ {fc_dc_per_delivered_h2:.1f} kWh DC/kg H₂ gegenüber HPRS-W ≈ {reactor_total_per_delivered_h2:.1f} kWh/kg geliefert. Margin = {onboard_margin:.1f} kWh/kg; Output/Input = {onboard_ratio:.2f}. Der wissenschaftlich sauberere erste Rail-Pfad ist daher HPRS-W im Depot/Testzentrum → H₂ → bestehendes Fuel-Cell/Batterie-PowerPack.",
            f"The onboard self-powered loop does not close: fuel cell ≈ {fc_dc_per_delivered_h2:.1f} kWh DC/kg H₂ versus HPRS-W ≈ {reactor_total_per_delivered_h2:.1f} kWh/kg delivered. Margin = {onboard_margin:.1f} kWh/kg; output/input = {onboard_ratio:.2f}. The scientifically cleaner first rail pathway is therefore depot/test-facility HPRS-W → H₂ → existing fuel-cell/battery PowerPack."
        )
    )

if math.isfinite(break_even_electricity):
    st.info(
        t(
            f"Kosten-Schwelle gegen gelieferten H₂: Bei unveränderten Annahmen müsste der Reaktorstrom ungefähr ≤ CHF {break_even_electricity:.3f}/kWh kosten, um den eingestellten gelieferten H₂-Preis von CHF {h2_price_chf_kg:.2f}/kg zu erreichen. CAPEX, Wartung, Kompression, Speicherung und Degradation sind nicht enthalten.",
            f"Cost threshold versus delivered H₂: with the other assumptions unchanged, reactor electricity would need to be about ≤ CHF {break_even_electricity:.3f}/kWh to match the selected delivered H₂ price of CHF {h2_price_chf_kg:.2f}/kg. CAPEX, maintenance, compression, storage and degradation are excluded."
        )
    )

# -----------------------------
# Collaboration screen
# -----------------------------
st.markdown("---")
st.subheader(t("6 · Kooperationsfall — was ein Rail-OEM beitragen kann", "6 · Collaboration case — what a rail OEM can contribute"))
colA, colB, colC = st.columns(3)
with colA:
    st.markdown(
        f"""
        <div class="hprs-card"><h4>{t('A · Reale Mission', 'A · Real mission')}</h4>
        <p class="hprs-small">{t('Streckenprofil, Fahrplan, Masse, Nebenverbraucher, Bremsenergie, Winter/Sommer-HVAC.', 'Route profile, timetable, mass, auxiliaries, braking energy, winter/summer HVAC.')}</p></div>
        """,
        unsafe_allow_html=True,
    )
with colB:
    st.markdown(
        f"""
        <div class="hprs-card"><h4>{t('B · PowerPack-Schnittstelle', 'B · PowerPack interface')}</h4>
        <p class="hprs-small">{t('Fuel-Cell/Batterie-Leistungsfluss, H₂-Druckniveau, Pufferstrategie, thermische Integration.', 'Fuel-cell/battery power flow, H₂ pressure level, buffer strategy, thermal integration.')}</p></div>
        """,
        unsafe_allow_html=True,
    )
with colC:
    st.markdown(
        f"""
        <div class="hprs-card"><h4>{t('C · Go/No-Go Test', 'C · Go/No-Go test')}</h4>
        <p class="hprs-small">{t('Messbarer Reaktor-kWh/kg-H₂, Reinheit, Recovery, Quench, Dauerbetrieb, Wartung und Safety.', 'Measured reactor kWh/kg H₂, purity, recovery, quench, endurance, maintenance and safety.')}</p></div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
    <div class="hprs-dark">
      <b>{t('Vorgeschlagener erster Schritt:', 'Proposed first step:')}</b><br>
      {t(
        '90-tägige gemeinsame Machbarkeitsstudie: reale Rail-Mission in den Simulator übernehmen, HPRS-W-Depot-Spezifikation ableiten, Labor-Messplan definieren und danach einen klaren Go/No-Go-Entscheid für einen Prüfstand treffen.',
        '90-day joint feasibility study: import a real rail mission into the simulator, derive the HPRS-W depot specification, define the laboratory measurement plan, then make a clear Go/No-Go decision for a test bench.'
      )}
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Model boundaries / references
# -----------------------------
with st.expander(t("Modellgrenzen & öffentliche Quellen", "Model boundaries & public references")):
    st.markdown(
        t(
            """
**Nicht enthalten:** detaillierte Längsdynamik, Kurven-/Gradientenprofil, Adhäsionsgrenzen, Fahrgastmasse, Kompressor- und Speicherverluste, Brennstoffzellendegradation, Batterie-SOC-Regelung, Redundanz, Brandschutz, Crash, Homologation, CAPEX und Wartung.

**Öffentliche Rail-Kontextquellen**  
- Stadler FLIRT H₂: https://www.stadlerrail.com/en/solutions/rolling-stock/mainline-flirt-h2  
- Stadler SBCTA reference: https://www.stadlerrail.com/en/solutions/references/flirt-h2-sbcta  
- DOE Hydrail workshop context: https://www.energy.gov/documents/fcto-h2-rail-workshop-2019-hoffrichterpdf

**Thermodynamische Referenz**  
- Wasser-Spaltung bei 298 K: ΔG ≈ 32.67 kWh/kg H₂, ΔH ≈ 39.38 kWh/kg H₂ (Standardzustand; NIST/DOE-konforme Referenzwerte).

**First-order Gleichungen**  
`F_roll = m g Crr`  
`F_aero = 0.5 rho CdA v²`  
`E_accel = 0.5 m v²`  
`E_climb = m g h`  
`H₂ = E_DC / (eta_FC × LHV_H₂)`
            """,
            """
**Excluded:** detailed longitudinal train dynamics, route curves/gradients, adhesion limits, passenger-mass variation, compressor/storage losses, fuel-cell degradation, battery SOC control, redundancy, fire safety, crash, homologation, CAPEX and maintenance.

**Public rail context sources**  
- Stadler FLIRT H₂: https://www.stadlerrail.com/en/solutions/rolling-stock/mainline-flirt-h2  
- Stadler SBCTA reference: https://www.stadlerrail.com/en/solutions/references/flirt-h2-sbcta  
- DOE Hydrail workshop context: https://www.energy.gov/documents/fcto-h2-rail-workshop-2019-hoffrichterpdf

**Thermodynamic reference**  
- Water splitting at 298 K: ΔG ≈ 32.67 kWh/kg H₂, ΔH ≈ 39.38 kWh/kg H₂ (standard-state reference; consistent with NIST/DOE values).

**First-order equations**  
`F_roll = m g Crr`  
`F_aero = 0.5 rho CdA v²`  
`E_accel = 0.5 m v²`  
`E_climb = m g h`  
`H₂ = E_DC / (eta_FC × LHV_H₂)`
            """
        )
    )

st.caption(
    t(
        "HydrogenOrg HPRS Rail Research Simulator V1.1 · Forschungsmodell — keine zertifizierte Leistungsangabe.",
        "HydrogenOrg HPRS Rail Research Simulator V1.1 · research model — not a certified performance claim.",
    )
)
