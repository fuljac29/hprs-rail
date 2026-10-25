import math
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="HPRS Automotive + Rail — Plasma Research Simulator",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Reference constants — V1 uses n-octane as a transparent gasoline surrogate.
C_ATOMIC = 12.011
H_ATOMIC = 1.008
H2_MOLAR = 2.016
OCTANE_C = 8
OCTANE_H = 18
OCTANE_MOLAR_KG = (OCTANE_C * C_ATOMIC + OCTANE_H * H_ATOMIC) / 1000.0

# Ideal non-oxidative decomposition: C8H18 -> 8 C(s) + 9 H2
H2_KG_PER_KG_FUEL_IDEAL = ((OCTANE_H / 2) * H2_MOLAR / 1000.0) / OCTANE_MOLAR_KG
C_KG_PER_KG_FUEL_IDEAL = (OCTANE_C * C_ATOMIC / 1000.0) / OCTANE_MOLAR_KG

# NIST Chemistry WebBook gives ΔfH°(liquid n-octane) near -250 kJ/mol.
# Standard-state products H2(g) and graphite C(s) have ΔfH° = 0.
# The ideal standard-state decomposition floor is therefore ~+250 kJ/mol.
OCTANE_DECOMP_KJ_PER_MOL = 250.0
THERMO_MIN_KWH_PER_KG_H2 = (
    OCTANE_DECOMP_KJ_PER_MOL / 3600.0
) / (((OCTANE_H / 2) * H2_MOLAR) / 1000.0)

H2_LHV_KWH_KG = 33.3  # U.S. DOE
CO2_PER_C = 44.0095 / 12.011
CO2_KG_PER_KG_FUEL_COMPLETE_OX = C_KG_PER_KG_FUEL_IDEAL * CO2_PER_C

# Steam-assisted n-octane reference pathways.
# A) Steam reforming to syngas:
# C8H18 + 8 H2O -> 8 CO + 17 H2
H2_KG_PER_KG_FUEL_STEAM_SYNGAS = (
    17.0 * H2_MOLAR / 1000.0
) / OCTANE_MOLAR_KG
WATER_KG_PER_KG_FUEL_STEAM_SYNGAS = (
    8.0 * 18.01528 / 1000.0
) / OCTANE_MOLAR_KG

# B) Steam reforming + complete water-gas shift:
# C8H18 + 16 H2O -> 8 CO2 + 25 H2
H2_KG_PER_KG_FUEL_STEAM_WGS = (
    25.0 * H2_MOLAR / 1000.0
) / OCTANE_MOLAR_KG
WATER_KG_PER_KG_FUEL_STEAM_WGS = (
    16.0 * 18.01528 / 1000.0
) / OCTANE_MOLAR_KG
CO2_KG_PER_KG_FUEL_STEAM_WGS = CO2_KG_PER_KG_FUEL_COMPLETE_OX

# Approximate standard-state reaction-enthalpy references for gaseous reactants.
# Steam reforming: ~1310 kJ/mol n-octane.
# Complete WGS adds ~8*(-41) kJ/mol, giving ~982 kJ/mol net.
STEAM_SYNGAS_REACTION_KJ_PER_MOL = 1310.0
STEAM_WGS_REACTION_KJ_PER_MOL = 982.0

STEAM_SYNGAS_REACTION_KWH_PER_KG_H2 = (
    STEAM_SYNGAS_REACTION_KJ_PER_MOL / 3600.0 / OCTANE_MOLAR_KG
) / H2_KG_PER_KG_FUEL_STEAM_SYNGAS

STEAM_WGS_REACTION_KWH_PER_KG_H2 = (
    STEAM_WGS_REACTION_KJ_PER_MOL / 3600.0 / OCTANE_MOLAR_KG
) / H2_KG_PER_KG_FUEL_STEAM_WGS

# HPRS-W water-splitting reference: 2 H2O -> 2 H2 + O2
WATER_MOLAR = 18.01528
O2_MOLAR = 31.998
WATER_KG_PER_KG_H2_STOICH = WATER_MOLAR / H2_MOLAR
O2_KG_PER_KG_H2_STOICH = O2_MOLAR / (2.0 * H2_MOLAR)

# V3.3 advanced HPRS-W thermodynamic references at 298.15 K, 1 bar.
# NIST-JANAF water(l): Delta_f H deg = -285.830 kJ/mol,
# Delta_f G deg = -237.141 kJ/mol. For H2O(l) -> H2(g) + 0.5 O2(g),
# the water-splitting reaction therefore requires +285.830 kJ/mol enthalpy
# and +237.141 kJ/mol reversible Gibbs work under these standard conditions.
FARADAY_C_MOL = 96485.33212
BOLTZMANN_J_K = 1.380649e-23
GAS_CONSTANT_J_MOL_K = 8.314462618
ARGON_MOLAR_KG = 39.948 / 1000.0
WATER_SPLIT_DG_KJ_PER_MOL_H2 = 237.141
WATER_SPLIT_DH_KJ_PER_MOL_H2 = 285.830
WATER_SPLIT_TDS_KJ_PER_MOL_H2 = (
    WATER_SPLIT_DH_KJ_PER_MOL_H2 - WATER_SPLIT_DG_KJ_PER_MOL_H2
)
WATER_SPLIT_REV_KWH_PER_KG_H2 = (
    WATER_SPLIT_DG_KJ_PER_MOL_H2 / 3600.0
) / (H2_MOLAR / 1000.0)
WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2 = (
    WATER_SPLIT_DH_KJ_PER_MOL_H2 / 3600.0
) / (H2_MOLAR / 1000.0)
WATER_SPLIT_ENTROPIC_HEAT_KWH_PER_KG_H2 = (
    WATER_SPLIT_TDS_KJ_PER_MOL_H2 / 3600.0
) / (H2_MOLAR / 1000.0)
WATER_SPLIT_REV_VOLTAGE_V = (
    WATER_SPLIT_DG_KJ_PER_MOL_H2 * 1000.0 / (2.0 * FARADAY_C_MOL)
)
WATER_SPLIT_THERMONEUTRAL_VOLTAGE_V = (
    WATER_SPLIT_DH_KJ_PER_MOL_H2 * 1000.0 / (2.0 * FARADAY_C_MOL)
)

# V3.3.6 standalone renewable-rail depot: scenario-specific finance and PV-only comparison.
def rail_hybrid_dispatch(pv_kwp, sun_hours, pv_pr, geo_electric_kwh_day,
                         geo_alloc_frac, battery_capacity_kwh, battery_power_kw,
                         battery_rt_eff, h2_kg_day, specific_electricity_kwh_kg):
    """24-hour synthetic repeating-day electrical dispatch for a hydrogen depot.

    The first 14 passes settle battery state under a repeating representative day;
    the 15th is used for costs. No site-specific weather or long-term guarantee.
    """
    solar_shape = [max(0.0, math.sin(math.pi * (h + 0.5 - 6.0) / 12.0)) for h in range(24)]
    solar_norm = sum(solar_shape)
    pv_total = pv_kwp * sun_hours * pv_pr
    pv_hourly = [pv_total * x / solar_norm for x in solar_shape]
    geo_hourly = geo_electric_kwh_day * geo_alloc_frac / 24.0
    elec_demand_hourly = h2_kg_day * specific_electricity_kwh_kg / 24.0
    charge_eff = math.sqrt(max(battery_rt_eff, 1e-9))
    discharge_eff = charge_eff
    soc = battery_capacity_kwh * 0.5
    rows = []
    start_soc = soc
    for cycle in range(15):
        rows = []
        start_soc = soc
        for hour in range(24):
            available = pv_hourly[hour] + geo_hourly
            direct = min(available, elec_demand_hourly)
            surplus = max(available - direct, 0.0)
            deficit = max(elec_demand_hourly - direct, 0.0)
            charged = min(surplus, battery_power_kw, max(battery_capacity_kwh - soc, 0.0) / charge_eff)
            soc += charged * charge_eff
            surplus -= charged
            discharged = min(deficit, battery_power_kw, soc * discharge_eff)
            soc -= discharged / discharge_eff
            deficit -= discharged
            soc = min(battery_capacity_kwh, max(soc, 0.0))
            rows.append({
                'Hour': hour, 'PV kWh': pv_hourly[hour],
                'Geothermal kWh': geo_hourly, 'Process demand kWh': elec_demand_hourly,
                'Direct renewables kWh': direct, 'Battery charged kWh': charged,
                'Battery discharged kWh': discharged, 'Grid imports kWh': deficit,
                'Renewable surplus kWh': surplus, 'Battery SOC kWh': soc,
            })
    return {
        'rows': rows, 'pv_kwh_day': pv_total,
        'geo_allocated_kwh_day': geo_electric_kwh_day * geo_alloc_frac,
        'renewable_used_kwh_day': sum(row['Direct renewables kWh'] + row['Battery charged kWh'] for row in rows),
        'grid_kwh_day': sum(row['Grid imports kWh'] for row in rows),
        'surplus_kwh_day': sum(row['Renewable surplus kWh'] for row in rows),
        'battery_start_kwh': start_soc, 'battery_end_kwh': soc,
        'specific_kwh_kg': specific_electricity_kwh_kg,
    }


def rail_capital_recovery_factor(discount_rate, lifetime_years):
    """Constant real annual payment / invested CHF. Straight-line depreciation is separate.

    Rate is an annual fraction. At zero rate, capital recovery equals straight-line
    depreciation; at positive rate it includes the required cost of capital.
    """
    n = max(int(lifetime_years), 1)
    r = max(float(discount_rate), 0.0)
    return 1.0 / n if r == 0 else r / (1.0 - (1.0 + r) ** (-n))


def rail_asset_cost_schedule(capex_by_asset, lifetime_by_asset, real_discount_rate):
    """Per-asset CAPEX / straight-line depreciation / annualized economic capital."""
    entries = []
    for asset, capex in capex_by_asset.items():
        life = int(lifetime_by_asset[asset])
        annuity = float(capex) * rail_capital_recovery_factor(real_discount_rate, life)
        entries.append({
            'Asset': asset,
            'Attributed CAPEX CHF': float(capex),
            'Life years': life,
            'Straight-line depreciation CHF/year': float(capex) / life,
            'Economic annuity CHF/year': annuity,
        })
    return entries


# Public technology benchmarks used only as external reference guideposts.
# U.S. DOE 2026 system targets: PEM ~51 kWh_e/kg H2; high-temperature
# electrolysis ~36 kWh_e/kg H2 and ~44 kWh/kg H2 total energy.
DOE_PEM_2026_SYSTEM_KWH_KG_H2 = 51.0
DOE_HTE_2026_ELECTRIC_KWH_KG_H2 = 36.0
DOE_HTE_2026_TOTAL_KWH_KG_H2 = 44.0


# V3.3 rail public guideposts — used only as contextual references, not calibration data.
# Stadler FLIRT H2 (SBCTA): advertised range >460 km, max speed 127 km/h,
# refuelling time <30 min, 116 seats; SBCTA duty is described as about 480–600 km/day.
# The train uses a modular PowerPack with fuel cells, hydrogen tanks and batteries;
# regenerative braking energy is stored in the traction batteries.
RAIL_PUBLIC_RANGE_KM = 460.0
RAIL_PUBLIC_MAX_SPEED_KMH = 127.0
RAIL_PUBLIC_REFUEL_MIN = 30.0
RAIL_PUBLIC_SEATS = 116
RAIL_PUBLIC_DAILY_KM_LOW = 480.0
RAIL_PUBLIC_DAILY_KM_HIGH = 600.0
GRAVITY_M_S2 = 9.80665
AIR_DENSITY_KG_M3 = 1.225

st.markdown(
    """
    <style>
    :root{--ink:#0b1724;--muted:#587084;--cyan:#0ea5d8;--green:#49a52e;--orange:#f36b19;--line:#d8e5ee;--soft:#f4f8fb;}
    .block-container{max-width:1500px;padding-top:1.1rem;padding-bottom:2.2rem;}
    h1,h2,h3{color:var(--ink);}
    .horg-kicker{display:inline-block;color:var(--green);font-size:.76rem;font-weight:900;letter-spacing:.13rem;text-transform:uppercase;margin-bottom:.45rem;}
    .horg-hero{padding:1.3rem 1.45rem;border:1px solid var(--line);border-radius:20px;background:linear-gradient(135deg,#fff 0%,#eef9ff 58%,#f4fbef 100%);margin-bottom:1rem;}
    .horg-hero h1{color:#0b1724!important;margin:.15rem 0 .6rem;font-size:2.35rem;line-height:1.04;font-weight:900;}
    .horg-hero p{color:var(--muted);font-size:1.03rem;line-height:1.65;margin:0;}
    .horg-chip{display:inline-block;margin:.45rem .35rem 0 0;padding:.32rem .58rem;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:.76rem;font-weight:800;color:var(--ink);}
    .horg-callout{padding:1rem 1.1rem;border-radius:16px;border:1px solid rgba(243,107,25,.25);background:#fff7ed;color:#5c6f7f;line-height:1.6;}
    .horg-eq{padding:1rem 1.15rem;border-radius:16px;background:#06111f;color:#fff;border:1px solid rgba(14,165,216,.3);font-size:1.1rem;font-weight:800;text-align:center;margin:.6rem 0 1rem;}
    .horg-note{padding:.9rem 1rem;border-radius:14px;background:#f7fbfd;border:1px solid var(--line);color:var(--muted);line-height:1.55;font-size:.9rem;}
    .horg-exec{margin:0 0 1.1rem;padding:1.15rem 1.2rem;border-radius:18px;border:1px solid #b9d9e8;background:linear-gradient(135deg,#07111e 0%,#0d2434 58%,#123526 100%);box-shadow:0 10px 28px rgba(0,0,0,.12);}
    .horg-exec-kicker{font-size:.76rem;letter-spacing:.12rem;font-weight:900;text-transform:uppercase;color:#7dd3fc;margin-bottom:.35rem;}
    .horg-exec h2{color:#fff!important;margin:.15rem 0 .55rem;font-size:1.55rem;line-height:1.15;}
    .horg-exec p{color:#dbeaf2;margin:.2rem 0 .8rem;line-height:1.55;}
    .horg-exec-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-top:.8rem;}
    .horg-exec-card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:.85rem .9rem;color:#eaf6fb;}
    .horg-exec-card b{display:block;color:#fff;margin-bottom:.28rem;}
    .horg-exec-card span{font-size:.88rem;line-height:1.45;color:#c5d9e4;}
    .horg-exec-foot{margin-top:.8rem;padding-top:.7rem;border-top:1px solid rgba(255,255,255,.14);font-size:.82rem;color:#adc4d1;line-height:1.5;}
    @media(max-width:900px){.horg-exec-grid{grid-template-columns:1fr;}}
    /* V3.3.1 UI fix: metric cards remain readable in Streamlit dark mode. */
    div[data-testid="stMetric"]{
        background:#ffffff!important;
        border:1px solid var(--line)!important;
        padding:.65rem .8rem!important;
        border-radius:14px!important;
    }
    div[data-testid="stMetric"] *,
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricValue"]{
        color:#0b1724!important;
        -webkit-text-fill-color:#0b1724!important;
        opacity:1!important;
    }
    div[data-testid="stMetricLabel"] p{
        color:#526b80!important;
        -webkit-text-fill-color:#526b80!important;
        font-weight:700!important;
    }
    div[data-testid="stMetricValue"]{font-size:1.62rem!important;font-weight:900!important;}
    div[data-testid="stMetricDelta"] *,
    div[data-testid="stMetricDelta"]{
        color:#15803d!important;
        -webkit-text-fill-color:#15803d!important;
        opacity:1!important;
    }
    /* V3.3.6: compact in-page navigation and readable chart areas. */
    .horg-nav{display:flex;align-items:center;flex-wrap:wrap;gap:.45rem;margin:0 0 1.05rem;padding:.65rem .75rem;border:1px solid #c7dce9;border-radius:14px;background:#edf7fc;}
    .horg-nav-label{color:#29465a;font-size:.82rem;font-weight:800;margin-right:.25rem;}
    .horg-nav a{display:inline-block;padding:.37rem .68rem;border:1px solid #b7d8e8;border-radius:999px;background:#fff;color:#075277!important;text-decoration:none!important;font-size:.82rem;font-weight:800;}
    .horg-nav a:hover{background:#d7f0fb;border-color:#58b6db;}
    .horg-section-anchor{display:block;position:relative;top:-1rem;visibility:hidden;}
    @media(max-width:720px){.horg-nav{gap:.35rem;padding:.5rem}.horg-nav a{font-size:.77rem;padding:.32rem .52rem}}
    html, body, [data-testid="stAppViewContainer"]{scroll-behavior:auto!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="horg-hero">
      <span class="horg-kicker">HydrogenOrg · HPRS Automotive + Rail V3.3.6</span>
      <h1>Plasma Mobility Research Simulator</h1>
      <p>
        Research simulator for HPRS automotive pathways and a new rail application layer. The rail module
        compares direct electric traction, stored-H₂ fuel-cell operation, depot HPRS-W hydrogen production
        and the theoretical possibility of an onboard HPRS-W loop.
      </p>
      <span class="horg-chip">Research-stage model</span>
      <span class="horg-chip">n-octane surrogate</span>
      <span class="horg-chip">Mass & energy balance</span>
      <span class="horg-chip">Conventional ICE benchmark</span>
      <span class="horg-chip">Pulsed plasma control</span>
      <span class="horg-chip">Same-net-power normalization</span>
      <span class="horg-chip">HPRS-W plasma water splitting</span>
      <span class="horg-chip">H₂O–Ar RF concept · ~1 bar</span>
      <span class="horg-chip">Rail mission + fuel-cell hybrid</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# V3.3.6: compact section navigation. Internal anchors do not change model state.
st.markdown(
    """
    <nav class="horg-nav" aria-label="Simulator section navigation">
      <span class="horg-nav-label">Jump to:</span>
      <a href="#horg-graphics">Research charts</a>
      <a href="#horg-automotive">Automotive results</a>
      <a href="#horg-rf">HPRS-W &amp; RF</a>
      <a href="#horg-advanced">Advanced theory</a>
      <a href="#horg-rail">Rail simulator</a>
      <a href="#horg-hybrid-rail">Renewable rail depot</a>
      <a href="#horg-references">References</a>
    </nav>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# V3.3 EXECUTIVE ENERGY CONCLUSION
# ============================================================
# This top-of-page synthesis deliberately separates:
#   (1) the best overall rail energy pathway, and
#   (2) the most promising H2-production research pathway.
# It is a model interpretation, not validated reactor performance.

st.markdown(
    """
    <div class="horg-exec">
      <div class="horg-exec-kicker">V3.3 synthesis · executive energy conclusion</div>
      <h2>Direct renewable electricity first. H₂O–Ar RF plasma where hydrogen is required.</h2>
      <p>
        Across the stationary and rail screening models, the lowest-energy end-use pathway is
        <b>direct electricity supplied from renewable generation</b> whenever grid, catenary or battery operation is practical.
        Hydrogen introduces additional conversion losses and should therefore be used where storage, range, logistics or infrastructure justify it.
      </p>
      <div class="horg-exec-grid">
        <div class="horg-exec-card">
          <b>1 · Best overall energy pathway</b>
          <span>Renewable electricity → electric drivetrain. This remains the reference to beat in the rail module.</span>
        </div>
        <div class="horg-exec-card">
          <b>2 · Preferred HydrogenOrg H₂ research concept</b>
          <span>Atmospheric-pressure H₂O–Ar RF-plasma reactor with rapid quench, H₂/O₂ separation, heat recovery and argon recycle.</span>
        </div>
        <div class="horg-exec-card">
          <b>3 · What V3.3 actually supports</b>
          <span>The current HPRS-W point is not yet the energy winner. V3.3 adds catalyst, RF/pulse, heat/electric recovery and argon-loop levers while preserving the thermodynamic guards.</span>
        </div>
      </div>
      <div class="horg-exec-foot">
        Scientific boundary: the simulator does not model RF electromagnetic coupling, detailed plasma kinetics, electrode/sheath physics or validated reactor hardware.
        “Atmospheric-pressure H₂O–Ar RF plasma” is the preferred reactor architecture for the next research stage, not a measured performance claim.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="horg-eq">C₈H₁₈ → 8 C(s) + 9 H₂ &nbsp;&nbsp; | &nbsp;&nbsp; No O₂ is produced by this reaction</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="horg-path-grid">

      <div class="horg-path-card">
        <h4>1 · Conventional gasoline engine</h4>
        <p>
          Gasoline is combusted directly in the ICE.
          <strong>Reference benchmark</strong> for fuel use, shaft efficiency
          and theoretical CO₂.
        </p>
      </div>

      <div class="horg-path-card">
        <h4>2 · Dry HPRS carbon-retention</h4>
        <p>
          C₈H₁₈ → 8 C(s) + 9 H₂.
          Hydrogen feeds the engine while the model attempts to
          <strong>retain carbon as a solid</strong>.
        </p>
      </div>

      <div class="horg-path-card">
        <h4>3 · Gasoline + water / steam</h4>
        <p>
          Separate gasoline and water feeds are vaporized before the reactor.
          The model compares <strong>steam reforming / WGS</strong>,
          hydrogen yield, water demand, CO/CO₂ and operating cost.
        </p>
      </div>

      <div class="horg-path-card">
        <h4>4 · HPRS-W plasma water splitting</h4>
        <p>
          Superheated steam + argon enter the preferred <strong>atmospheric-pressure RF-plasma concept</strong>, followed by
          <strong>species steering, rapid quench, H₂/O₂ separation, heat recovery
          and steam recirculation</strong>. This pathway uses no gasoline; RF coupling itself is not explicitly solved in V3.3.
        </p>
      </div>

    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "V3.3.6: key charts are visible in the research dashboard; long detailed sections remain collapsed by default. "
    "Open them only when needed; HPRS-W experimental levers and the Rail application remain directly visible."
)

st.info(
    "Four automotive pathways are retained from V3.3.6, and a new rail layer evaluates a regional hydrogen train mission. "
    "The rail module compares direct electric traction, purchased/stored H2 + fuel cell, depot HPRS-W + fuel cell, "
    "and an onboard HPRS-W loop-closure diagnostic. Public FLIRT H2 values are shown only as guideposts; train mass, "
    "route physics and component sizing remain editable scenario assumptions."
)

with st.sidebar:
    st.header("Model assumptions")
    st.caption("Scenario inputs — not validated reactor performance.")

    comparison_focus = st.radio(
        "Comparison focus",
        [
            "Show all four pathways",
            "Conventional gasoline",
            "Dry HPRS carbon-retention",
            "Gasoline + water / steam",
            "HPRS-W plasma water splitting",
        ],
        index=0,
        help=(
            "This selector is for presentation focus. Core calculations remain "
            "available so the four pathways can still be compared."
        ),
    )


    gross_engine_kw = st.slider(
        "Gross H₂-engine shaft power (kW)", 10, 250, 100, 5,
        help="Mechanical output before subtracting plasma/auxiliary parasitic power.",
    )
    engine_eff = st.slider(
        "H₂ engine brake efficiency (%)", 20, 50, 38, 1
    ) / 100.0

    conventional_eff = st.slider(
        "Conventional gasoline engine efficiency (%)", 20, 45, 30, 1,
        help="Reference brake efficiency for the conventional gasoline benchmark.",
    ) / 100.0

    st.divider()
    st.subheader("Scientific normalization")

    normalized_target_kw = st.slider(
        "Same net shaft power for comparison (kW)",
        min_value=10,
        max_value=150,
        value=50,
        step=5,
        help=(
            "All four pathways are rescaled to deliver this same net mechanical "
            "shaft power. This is the primary apples-to-apples comparison in V3.3."
        ),
    )

    reactor_conversion = st.slider(
        "Overall fuel conversion after recycle (%)", 60, 100, 92, 1,
        help="Net fraction of fuel converted through the modeled plasma pathway.",
    ) / 100.0

    h2_recovery = st.slider(
        "H₂ recovery to engine (%)", 70, 100, 96, 1
    ) / 100.0

    carbon_capture = st.slider(
        "Solid-carbon collection (%)", 70, 100, 96, 1
    ) / 100.0

    st.divider()
    st.subheader("Plasma mode")

    plasma_mode = st.radio(
        "Electrical model",
        ["Continuous reference", "Pulsed plasma"],
        index=0,
        help=(
            "Continuous mode uses a specific electricity value. Pulsed mode "
            "calculates average electrical power from pulse energy, frequency "
            "and active cells."
        ),
    )

    pulse_energy_mj = None
    pulse_frequency_khz = None
    pulse_width_ns = None
    active_cells = None
    derived_pulse_power_kw = None
    pulse_peak_power_kw_per_cell = None
    pulse_duty_cycle = None

    if plasma_mode == "Continuous reference":
        plasma_sei = st.slider(
            "Plasma electricity (kWh/kg H₂)",
            float(round(THERMO_MIN_KWH_PER_KG_H2, 1)),
            35.0,
            8.0,
            0.1,
            help=(
                "Gross electrical input per kg H₂. Lower bound is the ideal "
                "standard-state n-octane decomposition floor."
            ),
        )
    else:
        st.caption(
            "Exploratory control parameters — not validated automotive reactor specifications."
        )

        pulse_energy_mj = st.number_input(
            "Energy per pulse per cell (mJ)",
            min_value=0.1,
            max_value=500.0,
            value=20.0,
            step=1.0,
            format="%.1f",
        )

        st.markdown("#### Pulse frequency control")

        pulse_frequency_khz = st.slider(
            "Pulse frequency (kHz)",
            min_value=0.5,
            max_value=100.0,
            value=20.0,
            step=0.5,
            help=(
                "Electrical pulse repetition frequency for each active plasma cell. "
                "Average plasma power increases linearly with frequency when pulse "
                "energy and active-cell count are unchanged."
            ),
        )

        st.caption(
            f"Current pulse frequency: **{pulse_frequency_khz:.1f} kHz** "
            f"({pulse_frequency_khz*1000:.0f} pulses/s per active cell)"
        )

        pulse_width_ns = st.number_input(
            "Pulse width (ns)",
            min_value=10.0,
            max_value=5000.0,
            value=200.0,
            step=10.0,
            format="%.0f",
            help="Used to estimate instantaneous peak power and duty cycle.",
        )

        active_cells = st.slider(
            "Active plasma cells",
            1, 200, 50, 1,
        )

        # Pavg = Epulse * frequency * active cells
        derived_pulse_power_kw = (
            pulse_energy_mj * 1e-3
            * pulse_frequency_khz * 1e3
            * active_cells
            / 1000.0
        )

        pulse_peak_power_kw_per_cell = (
            (pulse_energy_mj * 1e-3)
            / (pulse_width_ns * 1e-9)
            / 1000.0
        )

        pulse_duty_cycle = (
            pulse_width_ns * 1e-9
            * pulse_frequency_khz * 1e3
            * 100.0
        )

    recovery_offset = st.slider(
        "Validated recovered-energy offset (%)", 0, 80, 20, 1,
        help=(
            "Fraction of gross plasma electrical demand genuinely covered by "
            "recovered energy; not free energy."
        ),
    ) / 100.0

    generator_eff = st.slider(
        "Generator / power-electronics efficiency (%)", 70, 98, 90, 1
    ) / 100.0

    st.divider()
    st.subheader("Steam-assisted comparison")

    steam_route = st.radio(
        "Gasoline + steam pathway",
        [
            "Steam reforming + WGS",
            "Steam reforming to syngas",
        ],
        index=0,
        help=(
            "The WGS route maximizes H2 but converts the fuel carbon to CO2. "
            "The syngas route produces H2 + CO. Neither route is the same as "
            "the dry carbon-retention pathway."
        ),
    )

    steam_reaction_floor_input = (
        STEAM_WGS_REACTION_KWH_PER_KG_H2
        if steam_route == "Steam reforming + WGS"
        else STEAM_SYNGAS_REACTION_KWH_PER_KG_H2
    )

    steam_thermal_energy = st.number_input(
        "Steam-route thermal demand (kWh_th/kg H₂)",
        min_value=float(round(steam_reaction_floor_input, 2)),
        max_value=40.0,
        value=float(max(8.0, math.ceil(steam_reaction_floor_input * 2.0) / 2.0)),
        step=0.5,
        key=f"steam_thermal_{steam_route}",
        help=(
            "Gross thermal process demand. The lower limit is the approximate "
            "standard-state reaction-enthalpy reference for the selected idealized route."
        ),
    )

    steam_electrical_aux = st.number_input(
        "Steam-route electrical auxiliaries (kWh_e/kg H₂)",
        min_value=0.0,
        max_value=15.0,
        value=1.5,
        step=0.1,
        help=(
            "Exploratory electrical demand for pumps, controls, separation, compression "
            "and any electrically driven reactor auxiliaries."
        ),
    )

    steam_heat_recovery = st.slider(
        "Steam-route thermal recovery (%)",
        min_value=0,
        max_value=90,
        value=50,
        step=5,
        help=(
            "Fraction of gross thermal process demand supplied by recovered heat. "
            "This reduces external thermal demand, not the electrical auxiliary load."
        ),
    ) / 100.0

    water_recycle = st.slider(
        "Water recycle (%)",
        min_value=0,
        max_value=95,
        value=0,
        step=5,
        help="Fraction of gross steam/water feed recovered and reused.",
    ) / 100.0

    st.divider()
    st.subheader("HPRS-W plasma water splitting")
    st.caption(
        "Architecture based on the supplied HTPR-QS concept: steam preheat, argon mixing, "
        "plasma dissociation, electric-field species steering, rapid quench, H₂/O₂ separation, "
        "heat recovery and steam recirculation. Inputs are research assumptions."
    )

    hprsw_plasma_electricity_base = st.number_input(
        "HPRS-W baseline plasma-system electricity (kWh_e/kg gross H₂)",
        min_value=20.0,
        max_value=100.0,
        value=50.0,
        step=1.0,
        help=(
            "Baseline electrical intensity before the V3.3 catalyst/pulsing/recovery modifiers. "
            "The supplied architecture shows a 45–55 kWh/kg H₂ example target; "
            "this is not treated as validated performance."
        ),
    )

    hprsw_steam_preheat = st.number_input(
        "HPRS-W steam preheat demand (kWh_th/kg gross H₂)",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=0.5,
        help=(
            "Separate thermal demand for vaporization/superheat and reactor feed conditioning. "
            "This is reported separately from plasma electricity."
        ),
    )

    hprsw_heat_recovery_base = st.slider(
        "HPRS-W base heat recovery (%)",
        0, 95, 50, 5,
        help="Base fraction of steam-preheat thermal demand supplied by recovered heat before the V3.3 recovery boost.",
    ) / 100.0

    hprsw_ion_separation_eff = st.slider(
        "Ion/species separation efficiency (%)",
        50, 100, 90, 1,
        help=(
            "Exploratory fraction of dissociated hydrogen-bearing species successfully routed "
            "toward the H₂-rich stream before quench/purification."
        ),
    ) / 100.0

    hprsw_quench_loss = st.slider(
        "Quench/recombination H₂ loss (%)",
        0, 40, 5, 1,
        help="Exploratory loss caused by recombination or incomplete chemistry freezing during quench.",
    ) / 100.0

    hprsw_purification_recovery = st.slider(
        "H₂ purification recovery (%)",
        70, 100, 98, 1,
        help="Fraction of H₂ entering the purification stage recovered as product H₂.",
    ) / 100.0

    hprsw_o2_recovery = st.slider(
        "O₂ recovery (%)",
        0, 100, 90, 5,
        help="Fraction of theoretical oxygen coproduct recovered as a usable O₂-rich stream.",
    ) / 100.0

    hprsw_steam_excess = st.slider(
        "Steam circulation / stoichiometric water (×)",
        1.0, 3.0, 1.5, 0.1,
        help=(
            "Gross steam circulation relative to stoichiometric water consumption. "
            "Only excess steam can be recycled; stoichiometric water is chemically consumed."
        ),
    )

    hprsw_excess_steam_recycle = st.slider(
        "Excess-steam recycle (%)",
        0, 99, 90, 1,
        help=(
            "Recovery of steam above the stoichiometric amount. This does not reduce the "
            "minimum water chemically consumed to make H₂."
        ),
    ) / 100.0

    hprsw_argon_circulation = st.number_input(
        "Argon circulation (kg Ar/kg gross H₂)",
        min_value=0.0,
        max_value=20.0,
        value=1.0,
        step=0.1,
        help="Exploratory argon working-fluid circulation ratio for the plasma/mixing stage.",
    )

    hprsw_argon_recovery = st.slider(
        "Argon recovery (%)",
        0, 100, 99, 1,
        help="Fraction of circulating argon recovered for reuse.",
    ) / 100.0

    st.divider()
    st.subheader("V3.3 experimental levers — catalyst, RF/pulsing, recovery & Ar")
    st.caption(
        "These controls are research-screening parameters. Catalyst and pulse settings do not change ΔG or ΔH; "
        "only measured/assumed reductions of process overhead are credited. RF carrier frequency and pulse repetition "
        "are kept separate so frequency itself is never treated as free efficiency."
    )

    with st.expander("Catalyst / plasma-catalysis scenario", expanded=True):
        hprsw_catalyst_family = st.selectbox(
            "Catalyst scenario",
            [
                "None / empty reactor",
                "Au/TiO₂/SBA-15 literature reference",
                "Custom experimental catalyst",
            ],
            index=0,
            help=(
                "The Au/TiO₂/SBA-15 entry is a literature reference for H₂O/Ar non-thermal plasma water splitting. "
                "No automatic performance gain is assigned; enter only a measured or deliberately assumed effect below."
            ),
        )
        hprsw_catalyst_overhead_reduction = st.slider(
            "Catalyst reduction of plasma kinetic/transport overhead (%)",
            0, 60, 0, 1,
            help=(
                "Applied only to the modeled electrical overhead above the standard-state reversible-work reference. "
                "It cannot reduce the thermodynamic minimum by itself."
            ),
        ) / 100.0
        hprsw_catalyst_recovery_gain_pp = st.slider(
            "Catalyst gain in delivered H₂ recovery chain (percentage points)",
            0.0, 10.0, 0.0, 0.5,
            help="Exploratory recovery improvement; use zero unless supported by experiment or a deliberate sensitivity case.",
        )

    with st.expander("RF carrier + pulsed-envelope diagnostic", expanded=True):
        hprsw_rf_carrier_choice = st.selectbox(
            "RF carrier frequency",
            ["13.56 MHz", "27.12 MHz", "40.68 MHz", "Custom"],
            index=0,
            help=(
                "13.56, 27.12 and 40.68 MHz are common ISM centre frequencies. They are engineering choices, "
                "not assumed efficiency optima."
            ),
        )
        _rf_map = {"13.56 MHz": 13.56, "27.12 MHz": 27.12, "40.68 MHz": 40.68}
        hprsw_rf_carrier_mhz = (
            _rf_map[hprsw_rf_carrier_choice]
            if hprsw_rf_carrier_choice != "Custom"
            else st.number_input("Custom RF carrier (MHz)", 0.1, 200.0, 13.56, 0.1)
        )
        hprsw_pulse_rep_khz = st.slider(
            "Pulse-envelope repetition frequency (kHz)", 0.1, 100.0, 20.0, 0.5,
            help="Repetition of the RF burst envelope; this is not the RF carrier frequency.",
        )
        hprsw_pulse_width_us = st.number_input(
            "RF burst width (µs)", 0.1, 1000.0, 10.0, 0.5,
            help="Together with repetition frequency this defines the burst duty cycle.",
        )
        hprsw_rf_forward_peak_kw = st.number_input(
            "Forward RF power during burst (kW)", 0.1, 5000.0, 100.0, 5.0,
        )
        hprsw_rf_coupling_eff = st.slider(
            "RF generator + matching + plasma coupling efficiency (%)", 30, 99, 85, 1,
            help="Fraction of forward electrical power treated as absorbed by the plasma/reactor load.",
        ) / 100.0
        hprsw_pulse_overhead_reduction = st.slider(
            "Measured/assumed pulsing reduction of remaining plasma overhead (%)",
            0, 50, 0, 1,
            help=(
                "Frequency and duty cycle do not automatically earn an efficiency gain. This separate parameter is the "
                "measured or sensitivity-case reduction in the remaining non-thermodynamic plasma overhead."
            ),
        ) / 100.0

    with st.expander("Improved energy recovery", expanded=False):
        hprsw_heat_recovery_boost_pp = st.slider(
            "Additional steam-preheat heat recovery (percentage points)", 0.0, 30.0, 0.0, 1.0,
            help="Added to the base heat-recovery setting and capped at 99%.",
        )
        hprsw_additional_rejected_heat_kwh_th = st.number_input(
            "Additional rejected heat available for power recovery (kWh_th/kg gross H₂)",
            0.0, 100.0, 0.0, 0.5,
            help=(
                "Use only for a heat stream not already credited to steam preheat, to avoid double-counting recovered energy."
            ),
        )
        hprsw_heat_to_electric_eff = st.slider(
            "Rejected-heat → electricity conversion efficiency (%)", 0, 60, 0, 1,
            help="Exploratory conversion efficiency for the additional, otherwise-rejected heat stream.",
        ) / 100.0

    with st.expander("Argon recycle energy", expanded=False):
        hprsw_argon_recycle_specific_energy = st.number_input(
            "Ar recycle / cooling / compression electricity (kWh_e/kg Ar circulated)",
            0.0, 5.0, 0.0, 0.01, format="%.2f",
            help=(
                "Explicit parasitic electricity for the argon loop. Default zero preserves the V3.2 baseline; "
                "enter measured compressor/cooling/separation demand when available."
            ),
        )

    st.divider()
    st.subheader("V3.3 advanced theory — HPRS-W")
    st.caption(
        "Diagnostic-only physics inputs. These do not represent measured HydrogenOrg reactor data."
    )

    with st.expander("Thermodynamics, E/N, quench & sizing", expanded=False):
        hprsw_ambient_temp_c = st.number_input(
            "Reference ambient temperature (°C)",
            min_value=-20.0,
            max_value=80.0,
            value=25.0,
            step=5.0,
            help="Reference environment used in the simple heat-exergy factor.",
        )

        hprsw_heat_source_temp_c = st.number_input(
            "External heat-source temperature (°C)",
            min_value=50.0,
            max_value=1500.0,
            value=500.0,
            step=25.0,
            help=(
                "Used only to estimate the maximum exergy fraction of externally supplied heat "
                "through 1 - T0/Th. It is not a heat-exchanger model."
            ),
        )

        st.markdown("##### Electric-field / ion-steering diagnostic")
        hprsw_field_voltage_v = st.number_input(
            "Applied separation-zone voltage (V)",
            min_value=10.0,
            max_value=50000.0,
            value=500.0,
            step=10.0,
        )
        hprsw_electrode_gap_mm = st.number_input(
            "Electrode gap (mm)",
            min_value=0.1,
            max_value=200.0,
            value=10.0,
            step=0.5,
        )
        hprsw_separation_temp_c = st.number_input(
            "Separation-zone gas temperature (°C)",
            min_value=50.0,
            max_value=5000.0,
            value=1200.0,
            step=50.0,
        )
        hprsw_pressure_bar = st.number_input(
            "Separation-zone pressure (bar abs)",
            min_value=0.05,
            max_value=20.0,
            value=1.0,
            step=0.05,
            format="%.2f",
        )
        hprsw_ion_mobility_cm2_vs = st.number_input(
            "Effective ion mobility (cm²/V·s)",
            min_value=0.01,
            max_value=100.0,
            value=2.0,
            step=0.1,
            help=(
                "User-supplied effective mobility at the modeled gas state. Real mobilities depend "
                "on species, E/N, temperature, pressure and composition."
            ),
        )
        hprsw_separation_distance_mm = st.number_input(
            "Required lateral separation distance (mm)",
            min_value=0.1,
            max_value=100.0,
            value=5.0,
            step=0.5,
        )
        hprsw_residence_time_ms = st.number_input(
            "Charged-species residence time (ms)",
            min_value=0.01,
            max_value=1000.0,
            value=5.0,
            step=0.5,
        )

        st.markdown("##### Quench / recombination diagnostic")
        hprsw_plasma_temp_c = st.number_input(
            "Plasma-core temperature (°C)",
            min_value=500.0,
            max_value=10000.0,
            value=3500.0,
            step=100.0,
        )
        hprsw_quench_outlet_temp_c = st.number_input(
            "Quench outlet temperature (°C)",
            min_value=20.0,
            max_value=2000.0,
            value=300.0,
            step=25.0,
        )
        hprsw_quench_time_ms = st.number_input(
            "Quench time (ms)",
            min_value=0.01,
            max_value=100.0,
            value=5.0,
            step=0.5,
        )
        hprsw_recomb_tau_ms = st.number_input(
            "Effective first-order recombination time (ms)",
            min_value=0.01,
            max_value=5000.0,
            value=100.0,
            step=5.0,
            help=(
                "Exploratory lumped timescale, not a plasma-kinetics solution. It is used only "
                "for the optional exp(-t/tau) survival estimate."
            ),
        )
        hprsw_quench_loss_model = st.radio(
            "Quench-loss treatment",
            [
                "Use direct scenario loss",
                "Use first-order timescale estimate",
            ],
            index=0,
            help=(
                "The default preserves the direct scenario-loss slider. The optional timescale mode "
                "sets H2 survival to exp(-t_quench/tau_recomb)."
            ),
        )

        st.markdown("##### First-order reactor sizing")
        hprsw_reactor_aspect_ratio = st.number_input(
            "Equivalent core length / diameter",
            min_value=0.2,
            max_value=20.0,
            value=3.0,
            step=0.2,
        )
        hprsw_plasma_power_share = st.slider(
            "Plasma-core share of HPRS-W electricity (%)",
            min_value=1,
            max_value=100,
            value=70,
            step=1,
            help=(
                "Separates estimated core electrical power from total HPRS-W system electricity "
                "for the power-density proxy."
            ),
        ) / 100.0
        hprsw_effective_hot_gas_cp = st.number_input(
            "Effective hot-stream Cp (kJ/kg·K)",
            min_value=0.2,
            max_value=20.0,
            value=2.0,
            step=0.1,
            help=(
                "Lumped sensible-heat approximation only. High-temperature dissociation and "
                "composition-dependent heat capacities are not solved."
            ),
        )
        hprsw_coolant_delta_t_c = st.number_input(
            "Coolant allowable temperature rise (K)",
            min_value=1.0,
            max_value=150.0,
            value=30.0,
            step=5.0,
        )

    st.divider()
    st.subheader("V3.3 feasible-region search")
    st.caption(
        "Coupled search over plasma electricity, total H2 recovery, H2-engine efficiency "
        "and HPRS-W heat recovery. Standard-state thermodynamic guards are applied automatically."
    )

    with st.expander("Multi-parameter competitive-region solver", expanded=False):
        v29_plasma_search_range = st.slider(
            "Plasma electricity search range (kWh_e/kg gross H2)",
            min_value=20.0,
            max_value=70.0,
            value=(32.0, 50.0),
            step=1.0,
            help=(
                "The solver may scan below the standard-state Gibbs reference, but such points "
                "are rejected unless the modeled external heat supplies enough exergy and total energy."
            ),
        )
        v29_recovery_search_range_pct = st.slider(
            "Total H2 recovery-chain search range (%)",
            min_value=70,
            max_value=100,
            value=(84, 98),
            step=1,
            help=(
                "Lumped delivered/gross H2 recovery used only by the V3.3 search. It represents the "
                "combined effect of species steering, quench survival and purification recovery."
            ),
        )
        v29_engine_search_range_pct = st.slider(
            "H2-engine brake-efficiency search range (%)",
            min_value=25,
            max_value=60,
            value=(38, 50),
            step=1,
        )
        v29_heat_recovery_search_range_pct = st.slider(
            "HPRS-W heat-recovery search range (%)",
            min_value=0,
            max_value=99,
            value=(50, 95),
            step=1,
        )
        v29_grid_resolution = st.radio(
            "Feasible-region grid resolution",
            ["Coarse", "Standard", "Fine"],
            index=1,
            horizontal=True,
            help=(
                "Resolution changes the number of deterministic grid points, not the physics model. "
                "Standard is designed for interactive use."
            ),
        )

    st.divider()
    st.subheader("V3.3 prototype-target screen")
    st.caption(
        "Prototype-oriented limits are engineering screening assumptions, not measured HydrogenOrg hardware limits. "
        "The standard-state ΔH/ΔG guards remain the thermodynamic constraints."
    )

    with st.expander("Prototype-oriented target constraints", expanded=False):
        v31_proto_min_plasma = st.number_input(
            "Prototype plasma-electricity floor (kWh_e/kg gross H2)",
            min_value=32.0,
            max_value=60.0,
            value=39.4,
            step=0.1,
            help=(
                "Conservative prototype-screen floor used to avoid selecting very low electrical-intensity points "
                "as the first engineering target. This is NOT a thermodynamic lower bound on plasma electricity by itself; "
                "the physical screening guards remain total energy ≥ ΔH and modeled exergy ≥ ΔG."
            ),
        )
        v31_proto_max_recovery_pct = st.slider(
            "Maximum prototype H2 recovery chain (%)",
            min_value=85,
            max_value=100,
            value=95,
            step=1,
            help="Upper cap used to prevent the prototype target from relying on near-perfect H2 recovery.",
        )
        v31_proto_max_engine_bte_pct = st.slider(
            "Maximum prototype H2-engine BTE (%)",
            min_value=35,
            max_value=50,
            value=45,
            step=1,
            help="Upper cap for the prototype-oriented target search; it is not a claim of demonstrated engine performance.",
        )
        v31_proto_max_heat_recovery_pct = st.slider(
            "Maximum prototype heat recovery (%)",
            min_value=50,
            max_value=95,
            value=85,
            step=1,
            help="Upper cap to keep the first prototype target from depending on extreme heat recovery.",
        )

    st.divider()
    st.subheader("V3.3 rail application")
    st.caption(
        "Regional-train mission model for a fuel-cell/battery hybrid. Public FLIRT H2 values are context only; "
        "mass, resistance, route, auxiliary load and component sizing below are scenario inputs."
    )

    rail_reference = st.radio(
        "Rail reference view",
        [
            "Stadler FLIRT H₂ public guideposts",
            "Generic regional H₂ multiple unit",
        ],
        index=0,
        help=(
            "The Stadler option displays public guideposts (>460 km advertised range, 127 km/h, <30 min refuelling, "
            "116 seats, and an SBCTA duty description of roughly 480–600 km/day). It does not populate proprietary train data."
        ),
    )

    with st.expander("Rail mission, vehicle and hybrid-system inputs", expanded=False):
        rail_mission_km = st.number_input(
            "Mission distance (km)", 10.0, 1000.0, 100.0, 10.0,
            help="Distance for one modeled mission segment.",
        )
        rail_daily_km = st.number_input(
            "Daily distance (km/day)", 10.0, 2000.0, 500.0, 10.0,
            help="Used to estimate daily hydrogen, electricity and water demand.",
        )
        rail_mass_t = st.number_input(
            "Train operating mass (t) — scenario", 40.0, 500.0, 120.0, 5.0,
            help="Editable engineering assumption; not a public FLIRT H2 mass specification.",
        )
        rail_cruise_speed_kmh = st.slider(
            "Cruise speed for resistance calculation (km/h)", 30, 160, 100, 5,
        )
        rail_average_speed_kmh = st.slider(
            "Average mission speed incl. stops (km/h)", 20, 140, 65, 5,
        )
        rail_accel_speed_kmh = st.slider(
            "Acceleration/braking cycle speed (km/h)", 30, 140, 80, 5,
            help="Representative speed reached between station stops for the kinetic-energy cycle model.",
        )
        rail_accel_m_s2 = st.slider(
            "Peak acceleration assumption (m/s²)", 0.2, 1.2, 0.6, 0.05,
        )
        rail_stops_per_100km = st.slider(
            "Station stops per 100 km", 0, 30, 8, 1,
        )
        rail_elevation_gain_m_per_100km = st.number_input(
            "Positive elevation gain per 100 km (m)", 0.0, 3000.0, 300.0, 50.0,
            help="A matching descent is assumed for the regenerative-energy estimate.",
        )
        rail_crr = st.number_input(
            "Rolling-resistance coefficient", 0.0005, 0.0050, 0.0015, 0.0001, format="%.4f",
            help="First-order rolling-resistance assumption for the whole train.",
        )
        rail_cda_m2 = st.number_input(
            "Aerodynamic CdA (m²) — scenario", 2.0, 30.0, 8.0, 0.5,
            help="Combined drag coefficient × frontal area used in the simple steady-speed resistance model.",
        )
        rail_drive_eff = st.slider(
            "DC-bus to wheel efficiency (%)", 75, 98, 92, 1,
        ) / 100.0
        rail_regen_eff = st.slider(
            "End-to-end regenerative recovery (%)", 0, 90, 70, 5,
            help="Net fraction of braking/downhill mechanical energy returned to the electrical bus after losses.",
        ) / 100.0
        rail_aux_kw = st.number_input(
            "Average auxiliaries / HVAC load (kW)", 0.0, 500.0, 80.0, 10.0,
        )

        st.markdown("##### Fuel-cell + battery hybrid")
        rail_fc_eff = st.slider(
            "Fuel-cell system efficiency, H₂ LHV → DC bus (%)", 30, 65, 45, 1,
            help=(
                "Editable duty-cycle assumption. A DOE hydrail workshop cites typical duty-cycle primary-powertrain "
                "fuel-cell system efficiency around 45% and potentially higher; use route-specific measured data when available."
            ),
        ) / 100.0
        rail_fc_nominal_kw = st.number_input(
            "Fuel-cell net nominal power (kW)", 50.0, 3000.0, 400.0, 25.0,
            help="Scenario value. The battery is assumed to buffer short traction peaks above this level.",
        )
        rail_battery_usable_kwh = st.number_input(
            "Usable traction-battery energy (kWh)", 10.0, 3000.0, 250.0, 10.0,
            help="Scenario buffer capacity; no Stadler proprietary battery capacity is assumed.",
        )
        rail_h2_storage_kg = st.number_input(
            "Usable onboard H₂ storage (kg)", 10.0, 2000.0, 120.0, 10.0,
            help="Scenario storage mass used only to estimate range.",
        )
        rail_delivered_h2_price_chf_kg = st.number_input(
            "Delivered hydrogen price (CHF/kg)", 0.0, 40.0, 10.0, 0.5,
            help="Editable comparison price for externally produced and delivered hydrogen.",
        )
        rail_grid_to_dc_eff = st.slider(
            "Direct electric grid/catenary → DC-bus efficiency (%)", 75, 99, 94, 1,
            help="Reference pathway for direct electric operation or battery charging.",
        ) / 100.0

    st.divider()
    with st.expander("V3.3.6 · Rail depot: PV / PV+battery / PV+geothermal+battery", expanded=False):
        st.caption("Independent rail-depot study, using the same H₂ demand and HPRS-W reactor settings as this Rail model. No live synchronization with the standalone Hybrid app.")
        st.markdown("##### Geothermal V4.0 — screening assumptions")
        rh_geo_temp_c = st.number_input("Geothermal source temperature (°C)", 80.0, 380.0, 220.0, 5.0, key="rh_geo_t")
        rh_geo_reinj_c = st.number_input("Geothermal reinjection (°C)", 30.0, 180.0, 80.0, 5.0, key="rh_geo_reinj")
        rh_geo_flow_kg_s = st.number_input("Geothermal flow (kg/s)", 0.0, 1000.0, 135.0, 5.0, key="rh_geo_flow")
        rh_geo_steam_frac = st.slider("Usable steam/conversion fraction (%)", 0, 90, 42, key="rh_geo_steam") / 100.0
        rh_geo_turbine_eff = st.slider("Geothermal turbine efficiency (%)", 5, 60, 34, key="rh_geo_turbine") / 100.0
        rh_geo_gen_eff = st.slider("Geothermal generator efficiency (%)", 60, 99, 94, key="rh_geo_gen") / 100.0
        rh_geo_availability = st.slider("Geothermal plant availability (%)", 40, 100, 92, key="rh_geo_avail") / 100.0
        rh_geo_parasitic = st.slider("Geothermal parasitic consumption (%)", 0, 40, 8, key="rh_geo_parasitic") / 100.0
        rh_geo_heat_recov = st.slider("Geothermal heat recovery (modeled, %)", 0, 95, 68, key="rh_geo_heat") / 100.0
        rh_geo_alloc = st.slider("Share of geothermal electricity allocated to Rail H₂ (%)", 0, 100, 2, key="rh_geo_alloc") / 100.0
        rh_geo_heat_grade = st.slider("Portion of modeled heat usable at required temperature (%)", 0, 100, 0, key="rh_heat_grade") / 100.0
        rh_required_heat_temp_c = st.number_input("Minimum depot preheat supply temperature (°C)", 60.0, 500.0, 180.0, 10.0, key="rh_min_heat_temp")
        st.caption("Usable geothermal heat defaults to 0%. It is admitted only if the selected source temperature reaches the selected process preheat temperature. Plasma-core energy is not displaced.")
        st.markdown("##### Photovoltaic and stationary battery")
        rh_pv_kwp = st.number_input("Solar PV capacity (kWp)", 0.0, 100000.0, 1500.0, 100.0, key="rh_pv")
        rh_sun_hours = st.slider("Representative full-sun hours/day", 0.0, 9.0, 3.5, 0.1, key="rh_sun")
        rh_pv_pr = st.slider("Solar PV performance ratio (%)", 40, 100, 82, key="rh_pv_pr") / 100.0
        rh_battery_kwh = st.number_input("Stationary battery capacity (kWh)", 0.0, 500000.0, 3000.0, 250.0, key="rh_bat_energy")
        rh_battery_kw = st.number_input("Battery charge/discharge power (kW)", 0.0, 50000.0, 500.0, 50.0, key="rh_bat_power")
        rh_battery_eff = st.slider("Battery round-trip efficiency (%)", 50, 100, 88, key="rh_bat_eff") / 100.0
        st.markdown("##### Hydrogen and comparative economics")
        rh_pem_kwh_kg = st.number_input("PEM electrical energy (kWh/kg H₂ delivered)", 35.0, 100.0, 53.0, 1.0, key="rh_pem_sec")
        rh_grid_cost = st.number_input("Grid energy purchase price (CHF/kWh)", 0.0, 2.0, 0.22, 0.01, key="rh_grid_price")
        rh_renew_value = st.number_input("Renewable electricity transfer price (CHF/kWh; contract mode only)", 0.0, 2.0, 0.12, 0.01, key="rh_renew_val")
        rh_purchased_heat_price = st.number_input("Purchased supplementary heat (CHF/kWh_th)", 0.0, 1.0, 0.04, 0.01, key="rh_heat_price")
        rh_geo_heat_value = st.number_input("Geothermal heat transfer price (CHF/kWh_th; contract mode only)", 0.0, 1.0, 0.025, 0.005, key="rh_geo_heat_value")
        rh_extra_chf_kg = st.number_input("Additional process / compression OPEX (CHF/kg H₂)", 0.0, 30.0, 0.45, 0.05, key="rh_extra")
        st.markdown("##### Transparent capital amortization — editable screening assumptions")
        rh_days = st.slider("Operating days/year (same H₂ volume in every scenario)", 100, 365, 330, key="rh_days")
        rh_costing_mode = st.radio(
            "How renewable electricity and geothermal heat are paid for",
            ["Owned assets — annualized CAPEX + maintenance", "Purchased renewables — energy transfer contract"],
            index=0, key="rh_finance_mode", help=(
                "Choose one accounting boundary. Owned assets use attributable PV/geothermal CAPEX and OPEX "
                "and do NOT charge a second internal renewable kWh transfer price. "
                "A supply contract charges renewable kWh and qualified geothermal heat at transfer prices "
                "but excludes their generation CAPEX/OPEX. The hydrogen reactor and owned buffer battery "
                "remain investments in both cases."
            ),
        )
        rh_interest_pct = st.slider("Annual real discount / financing rate (%)", 0.0, 20.0, 6.0, 0.5, key="rh_interest")
        rh_interest = rh_interest_pct / 100.0
        rh_life_reactor = st.slider("HPRS-W / PEM plant life (years)", 5, 40, 15, key="rh_life_reactor")
        rh_life_pv = st.slider("PV plant life (years)", 10, 40, 25, key="rh_life_pv")
        rh_life_battery = st.slider("Stationary battery life (years)", 5, 25, 12, key="rh_life_battery")
        rh_life_geo = st.slider("Geothermal asset life (years)", 10, 50, 30, key="rh_life_geo")
        rh_fixed_opex_fraction = st.slider("Reactor annual fixed maintenance (% reactor CAPEX)", 0.0, 20.0, 3.0, 0.5, key="rh_fixed") / 100.0
        rh_pv_opex_pct = st.slider("PV annual fixed maintenance (% attributed PV CAPEX)", 0.0, 10.0, 1.5, 0.5, key="rh_fixed_pv") / 100.0
        rh_battery_opex_pct = st.slider("Battery annual fixed maintenance (% attributed battery CAPEX)", 0.0, 10.0, 2.0, 0.5, key="rh_fixed_bat") / 100.0
        rh_hprsw_capex = st.number_input("HPRS-W depot installed CAPEX (CHF)", 0.0, 500000000.0, 2200000.0, 100000.0, key="rh_cap_plasma")
        rh_pem_capex = st.number_input("PEM depot installed CAPEX (CHF)", 0.0, 500000000.0, 1800000.0, 100000.0, key="rh_cap_pem")
        rh_pv_capex = st.number_input("PV plant installed CAPEX (CHF)", 0.0, 500000000.0, 1600000.0, 100000.0, key="rh_cap_pv")
        rh_bat_capex = st.number_input("Stationary battery installed CAPEX (CHF)", 0.0, 500000000.0, 800000.0, 100000.0, key="rh_cap_bat")
        rh_pv_capex_alloc = st.slider("PV share of CAPEX attributed to Rail H₂ (%)", 0, 100, 100, key="rh_attrib_pv") / 100.0
        rh_bat_capex_alloc = st.slider("Stationary battery share attributed to Rail H₂ (%)", 0, 100, 100, key="rh_attrib_bat") / 100.0
        rh_geo_capex_allocated = st.number_input("Geothermal installed CAPEX attributable to Rail H₂ (CHF)", 0.0, 1000000000.0, 0.0, 100000.0, key="rh_cap_geo")
        rh_geo_opex_allocated = st.number_input("Geothermal annual fixed OPEX attributable to Rail H₂ (CHF/year)", 0.0, 100000000.0, 0.0, 10000.0, key="rh_geo_opex")
        st.caption(
            "All capital inputs are illustrative, not equipment quotations. Annual economic capital recovery uses "
            "CAPEX × r / [1 − (1+r)^(-n)]. Straight-line depreciation (CAPEX / n) is displayed separately "
            "but NOT added again to costs. Zero geothermal investment or maintenance makes owned hybrid "
            "scenarios incomplete until a justified allocation is entered."
        )

    st.divider()
    st.subheader("Operating-cost inputs")

    gasoline_price_chf_l = st.number_input(
        "Gasoline price (CHF/L)",
        min_value=0.0,
        max_value=5.0,
        value=2.16,
        step=0.05,
        help="Editable cost assumption. Default is an illustrative Swiss 95-octane reference.",
    )

    electricity_price_chf_kwh = st.number_input(
        "Electricity price (CHF/kWh)",
        min_value=0.0,
        max_value=1.5,
        value=0.277,
        step=0.01,
        format="%.3f",
        help="Editable cost assumption for externally supplied process electricity.",
    )

    thermal_energy_price_chf_kwh = st.number_input(
        "Supplemental thermal-energy price (CHF/kWh_th)",
        min_value=0.0,
        max_value=1.5,
        value=0.0,
        step=0.01,
        format="%.3f",
        help=(
            "Optional marginal price for unrecovered steam-route process heat. "
            "Leave at 0 if you want to report the heat requirement without assigning a cost."
        ),
    )

    water_price_chf_m3 = st.number_input(
        "Water price (CHF/m³)",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        step=0.5,
        help="Editable water-cost assumption.",
    )

    argon_price_chf_kg = st.number_input(
        "Argon make-up price (CHF/kg)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
        help="Optional scenario price. Default 0 avoids inventing an argon market value."
    )

    oxygen_value_chf_kg = st.number_input(
        "Recovered O₂ value (CHF/kg)",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.05,
        help="Optional coproduct credit. Default 0 keeps the comparison conservative."
    )

    fuel_density = st.number_input(
        "Fuel density (kg/L)", 0.68, 0.82, 0.745, 0.005, format="%.3f"
    )

    gasoline_lhv = st.number_input(
        "Fuel LHV reference (kWh/kg)", 10.0, 14.0, 12.0, 0.1
    )

h2_required_engine_kg_h = gross_engine_kw / (engine_eff * H2_LHV_KWH_KG)
effective_h2_yield = H2_KG_PER_KG_FUEL_IDEAL * reactor_conversion * h2_recovery
fuel_kg_h = h2_required_engine_kg_h / effective_h2_yield if effective_h2_yield > 0 else math.inf
fuel_l_h = fuel_kg_h / fuel_density

h2_gross_kg_h = fuel_kg_h * H2_KG_PER_KG_FUEL_IDEAL * reactor_conversion
h2_to_engine_kg_h = h2_gross_kg_h * h2_recovery

carbon_generated_kg_h = fuel_kg_h * C_KG_PER_KG_FUEL_IDEAL * reactor_conversion
carbon_captured_kg_h = carbon_generated_kg_h * carbon_capture
carbon_uncaptured_kg_h = carbon_generated_kg_h * (1.0 - carbon_capture)

if plasma_mode == "Continuous reference":
    plasma_gross_kw = h2_gross_kg_h * plasma_sei
    effective_plasma_sei = plasma_sei
else:
    plasma_gross_kw = derived_pulse_power_kw
    effective_plasma_sei = (
        plasma_gross_kw / h2_gross_kg_h
        if h2_gross_kg_h > 0
        else math.inf
    )

plasma_external_kw = plasma_gross_kw * (1.0 - recovery_offset)
shaft_draw_for_plasma_kw = (
    plasma_external_kw / generator_eff
    if generator_eff > 0
    else math.inf
)
net_shaft_kw = gross_engine_kw - shaft_draw_for_plasma_kw

thermo_floor_power_kw = h2_gross_kg_h * THERMO_MIN_KWH_PER_KG_H2
thermo_adequacy_ratio = (
    plasma_gross_kw / thermo_floor_power_kw
    if thermo_floor_power_kw > 0
    else math.inf
)
max_h2_at_thermo_floor_kg_h = (
    plasma_gross_kw / THERMO_MIN_KWH_PER_KG_H2
)

h2_chemical_kw = h2_to_engine_kg_h * H2_LHV_KWH_KG
fuel_chemical_kw = fuel_kg_h * gasoline_lhv
hprs_net_eff = (
    net_shaft_kw / fuel_chemical_kw
    if fuel_chemical_kw > 0
    else 0.0
)

co2_retention_equiv_kg_h = carbon_captured_kg_h * CO2_PER_C
uncaptured_c_oxidation_potential_kg_h = carbon_uncaptured_kg_h * CO2_PER_C
ideal_h2_energy_fraction = H2_KG_PER_KG_FUEL_IDEAL * H2_LHV_KWH_KG / gasoline_lhv

# Conventional gasoline benchmark — same nominal shaft output.
conv_same_gross_fuel_kg_h = (
    gross_engine_kw / (conventional_eff * gasoline_lhv)
)
conv_same_gross_fuel_l_h = conv_same_gross_fuel_kg_h / fuel_density
conv_same_gross_co2_kg_h = (
    conv_same_gross_fuel_kg_h * CO2_KG_PER_KG_FUEL_COMPLETE_OX
)

# Same useful net shaft output as HPRS after plasma burden.
same_net_target_kw = max(net_shaft_kw, 0.0)
conv_same_net_fuel_kg_h = (
    same_net_target_kw / (conventional_eff * gasoline_lhv)
    if same_net_target_kw > 0
    else 0.0
)
conv_same_net_fuel_l_h = (
    conv_same_net_fuel_kg_h / fuel_density
    if fuel_density > 0
    else 0.0
)
conv_same_net_co2_kg_h = (
    conv_same_net_fuel_kg_h * CO2_KG_PER_KG_FUEL_COMPLETE_OX
)
fuel_ratio_same_net = (
    fuel_kg_h / conv_same_net_fuel_kg_h
    if conv_same_net_fuel_kg_h > 0
    else math.inf
)

# ============================================================
# STEAM-ASSISTED GASOLINE + WATER COMPARISON
# ============================================================

if steam_route == "Steam reforming + WGS":
    steam_h2_yield_kg_per_kg_fuel = H2_KG_PER_KG_FUEL_STEAM_WGS
    steam_water_kg_per_kg_fuel = WATER_KG_PER_KG_FUEL_STEAM_WGS
    steam_reaction_floor_kwh_per_kg_h2 = STEAM_WGS_REACTION_KWH_PER_KG_H2
    steam_carbon_product = "CO2"
else:
    steam_h2_yield_kg_per_kg_fuel = H2_KG_PER_KG_FUEL_STEAM_SYNGAS
    steam_water_kg_per_kg_fuel = WATER_KG_PER_KG_FUEL_STEAM_SYNGAS
    steam_reaction_floor_kwh_per_kg_h2 = STEAM_SYNGAS_REACTION_KWH_PER_KG_H2
    steam_carbon_product = "CO"

steam_effective_h2_yield = (
    steam_h2_yield_kg_per_kg_fuel
    * reactor_conversion
    * h2_recovery
)

steam_fuel_kg_h = (
    h2_required_engine_kg_h / steam_effective_h2_yield
    if steam_effective_h2_yield > 0
    else math.inf
)

steam_fuel_l_h = (
    steam_fuel_kg_h / fuel_density
    if fuel_density > 0
    else math.inf
)

steam_h2_gross_kg_h = (
    steam_fuel_kg_h
    * steam_h2_yield_kg_per_kg_fuel
    * reactor_conversion
)

steam_h2_to_engine_kg_h = steam_h2_gross_kg_h * h2_recovery

steam_water_gross_kg_h = (
    steam_fuel_kg_h
    * steam_water_kg_per_kg_fuel
)

steam_water_makeup_kg_h = (
    steam_water_gross_kg_h
    * (1.0 - water_recycle)
)

# First-order density assumption for make-up water: 1 kg ~ 1 L.
steam_water_makeup_l_h = steam_water_makeup_kg_h

# V3.3 keeps steam-route thermal and electrical process energy separate.
steam_thermal_gross_kw = (
    steam_h2_gross_kg_h
    * steam_thermal_energy
)

steam_thermal_external_kw = (
    steam_thermal_gross_kw
    * (1.0 - steam_heat_recovery)
)

steam_electrical_aux_kw = (
    steam_h2_gross_kg_h
    * steam_electrical_aux
)

steam_electrical_shaft_burden_kw = (
    steam_electrical_aux_kw / generator_eff
    if generator_eff > 0
    else math.inf
)

# Recovered/external process heat is reported separately and is not silently
# converted into shaft burden. Only electrical auxiliaries reduce shaft output.
steam_net_shaft_kw = gross_engine_kw - steam_electrical_shaft_burden_kw

steam_fuel_chemical_kw = steam_fuel_kg_h * gasoline_lhv

steam_net_eff = (
    steam_net_shaft_kw / steam_fuel_chemical_kw
    if steam_fuel_chemical_kw > 0
    else 0.0
)

if steam_route == "Steam reforming + WGS":
    steam_co2_kg_h = (
        steam_fuel_kg_h
        * CO2_KG_PER_KG_FUEL_STEAM_WGS
        * reactor_conversion
    )
    steam_co_kg_h = 0.0
else:
    CO_MOLAR = 28.0101
    steam_co_kg_per_kg_fuel = (
        (8.0 * CO_MOLAR / 1000.0)
        / OCTANE_MOLAR_KG
    )
    steam_co_kg_h = (
        steam_fuel_kg_h
        * steam_co_kg_per_kg_fuel
        * reactor_conversion
    )
    steam_co2_kg_h = 0.0

# Operating-cost views.
conventional_fuel_cost_chf_h = (
    conv_same_gross_fuel_l_h
    * gasoline_price_chf_l
)

dry_hprs_fuel_cost_chf_h = (
    fuel_l_h
    * gasoline_price_chf_l
)

dry_hprs_external_energy_cost_chf_h = (
    plasma_external_kw
    * electricity_price_chf_kwh
)

dry_hprs_cost_external_power_chf_h = (
    dry_hprs_fuel_cost_chf_h
    + dry_hprs_external_energy_cost_chf_h
)

steam_fuel_cost_chf_h = (
    steam_fuel_l_h
    * gasoline_price_chf_l
)

steam_water_cost_chf_h = (
    (steam_water_makeup_l_h / 1000.0)
    * water_price_chf_m3
)

steam_electrical_cost_chf_h = (
    steam_electrical_aux_kw
    * electricity_price_chf_kwh
)

steam_thermal_cost_chf_h = (
    steam_thermal_external_kw
    * thermal_energy_price_chf_kwh
)

steam_cost_external_power_chf_h = (
    steam_fuel_cost_chf_h
    + steam_water_cost_chf_h
    + steam_electrical_cost_chf_h
    + steam_thermal_cost_chf_h
)

conventional_cost_per_kwh_shaft = (
    conventional_fuel_cost_chf_h / gross_engine_kw
    if gross_engine_kw > 0
    else math.inf
)

dry_hprs_fuel_cost_per_net_kwh = (
    dry_hprs_fuel_cost_chf_h / net_shaft_kw
    if net_shaft_kw > 0
    else math.inf
)

dry_hprs_external_cost_per_net_kwh = (
    dry_hprs_cost_external_power_chf_h / net_shaft_kw
    if net_shaft_kw > 0
    else math.inf
)

steam_fuel_water_cost_per_net_kwh = (
    (steam_fuel_cost_chf_h + steam_water_cost_chf_h)
    / steam_net_shaft_kw
    if steam_net_shaft_kw > 0
    else math.inf
)

steam_external_cost_per_net_kwh = (
    steam_cost_external_power_chf_h
    / steam_net_shaft_kw
    if steam_net_shaft_kw > 0
    else math.inf
)

# ============================================================
# V3.3 HPRS-W EXPERIMENTAL LEVERS
# Catalyst, RF/pulsed envelope, additional recovery and argon recycle.
# These modifiers are deliberately separated from thermodynamic reference values.
# ============================================================

# Catalyst/pulsing can only reduce the modeled electrical overhead above the
# standard-state reversible-work reference in this conservative screening model.
_hprsw_base_overhead_kwh = max(
    hprsw_plasma_electricity_base - WATER_SPLIT_REV_KWH_PER_KG_H2, 0.0
)
hprsw_plasma_after_catalyst = (
    WATER_SPLIT_REV_KWH_PER_KG_H2
    + _hprsw_base_overhead_kwh * (1.0 - hprsw_catalyst_overhead_reduction)
)
_hprsw_after_cat_overhead = max(
    hprsw_plasma_after_catalyst - WATER_SPLIT_REV_KWH_PER_KG_H2, 0.0
)
hprsw_plasma_after_pulsing = (
    WATER_SPLIT_REV_KWH_PER_KG_H2
    + _hprsw_after_cat_overhead * (1.0 - hprsw_pulse_overhead_reduction)
)

# Ar circulation is not free: this explicit parasitic term can be populated from
# measured recycle/compression/cooling data when available.
hprsw_argon_recycle_electricity_per_gross_h2 = (
    hprsw_argon_circulation * hprsw_argon_recycle_specific_energy
)

# Additional rejected-heat recovery is kept separate from steam-preheat recovery
# to prevent double counting. It is an internal electricity credit, not a new source.
hprsw_additional_electric_recovery_credit = (
    hprsw_additional_rejected_heat_kwh_th * hprsw_heat_to_electric_eff
)

hprsw_plasma_electricity_before_credit = (
    hprsw_plasma_after_pulsing + hprsw_argon_recycle_electricity_per_gross_h2
)
hprsw_plasma_electricity = max(
    0.0,
    hprsw_plasma_electricity_before_credit - hprsw_additional_electric_recovery_credit,
)

hprsw_heat_recovery = min(
    0.99,
    hprsw_heat_recovery_base + hprsw_heat_recovery_boost_pp / 100.0,
)

# RF burst diagnostics. Carrier frequency is intentionally not used as an
# efficiency multiplier; only duty, forward power and coupling determine average
# absorbed power. Any efficiency change must enter through the explicit measured/
# assumed pulsing-overhead parameter above.
hprsw_rf_duty_raw = hprsw_pulse_rep_khz * 1e3 * hprsw_pulse_width_us * 1e-6
hprsw_rf_duty = max(0.0, min(1.0, hprsw_rf_duty_raw))
hprsw_rf_avg_forward_kw = hprsw_rf_forward_peak_kw * hprsw_rf_duty
hprsw_rf_absorbed_kw = hprsw_rf_avg_forward_kw * hprsw_rf_coupling_eff
hprsw_rf_gross_h2_capacity_kg_h = (
    hprsw_rf_absorbed_kw / max(hprsw_plasma_after_pulsing, 1e-12)
)

# ============================================================
# HPRS-W PLASMA WATER-SPLITTING MODEL
# 2 H2O -> 2 H2 + O2
# ============================================================

# Optional first-order quench survival diagnostic.
hprsw_quench_time_s = max(hprsw_quench_time_ms * 1e-3, 1e-12)
hprsw_recomb_tau_s = max(hprsw_recomb_tau_ms * 1e-3, 1e-12)
hprsw_quench_survival_timescale = math.exp(
    -hprsw_quench_time_s / hprsw_recomb_tau_s
)
hprsw_quench_loss_timescale = 1.0 - hprsw_quench_survival_timescale
hprsw_quench_loss_effective = (
    hprsw_quench_loss
    if hprsw_quench_loss_model == "Use direct scenario loss"
    else hprsw_quench_loss_timescale
)

hprsw_recovery_chain_base = (
    hprsw_ion_separation_eff
    * (1.0 - hprsw_quench_loss_effective)
    * hprsw_purification_recovery
)
hprsw_recovery_chain = min(
    0.999,
    hprsw_recovery_chain_base + hprsw_catalyst_recovery_gain_pp / 100.0,
)
hprsw_rf_delivered_h2_capacity_kg_h = (
    hprsw_rf_gross_h2_capacity_kg_h * hprsw_recovery_chain
)

# Current architecture diagnostic at the gross H2-engine scale.
hprsw_h2_delivered_current_kg_h = h2_required_engine_kg_h
hprsw_h2_gross_current_kg_h = (
    hprsw_h2_delivered_current_kg_h / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)
hprsw_electric_current_kw = (
    hprsw_h2_gross_current_kg_h * hprsw_plasma_electricity
)
hprsw_thermal_gross_current_kw = (
    hprsw_h2_gross_current_kg_h * hprsw_steam_preheat
)
hprsw_thermal_external_current_kw = (
    hprsw_thermal_gross_current_kw * (1.0 - hprsw_heat_recovery)
)

# Stoichiometric water is consumed. Recycling applies only to steam circulated
# above the stoichiometric requirement.
hprsw_water_stoich_current_kg_h = (
    hprsw_h2_gross_current_kg_h * WATER_KG_PER_KG_H2_STOICH
)
hprsw_water_circulation_current_kg_h = (
    hprsw_water_stoich_current_kg_h * hprsw_steam_excess
)
hprsw_excess_water_current_kg_h = max(
    hprsw_water_circulation_current_kg_h - hprsw_water_stoich_current_kg_h, 0.0
)
hprsw_water_makeup_current_kg_h = (
    hprsw_water_stoich_current_kg_h
    + hprsw_excess_water_current_kg_h * (1.0 - hprsw_excess_steam_recycle)
)

hprsw_o2_gross_current_kg_h = (
    hprsw_h2_gross_current_kg_h * O2_KG_PER_KG_H2_STOICH
)
hprsw_o2_recovered_current_kg_h = (
    hprsw_o2_gross_current_kg_h * hprsw_o2_recovery
)

hprsw_argon_circulation_current_kg_h = (
    hprsw_h2_gross_current_kg_h * hprsw_argon_circulation
)
hprsw_argon_makeup_current_kg_h = (
    hprsw_argon_circulation_current_kg_h * (1.0 - hprsw_argon_recovery)
)

# Closed-loop diagnostic: if H2 is used in an engine and the engine-driven
# generator must power the same HPRS-W water splitter, the per-kg-H2 shaft
# margin is normally negative at present electricity intensities.
hprsw_shaft_per_kg_delivered_h2 = engine_eff * H2_LHV_KWH_KG
hprsw_electricity_per_kg_delivered_h2 = (
    hprsw_plasma_electricity / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)
hprsw_equiv_shaft_burden_per_kg_delivered_h2 = (
    hprsw_electricity_per_kg_delivered_h2 / generator_eff
    if generator_eff > 0 else math.inf
)
hprsw_closed_loop_margin_kwh_per_kg = (
    hprsw_shaft_per_kg_delivered_h2
    - hprsw_equiv_shaft_burden_per_kg_delivered_h2
)

# ============================================================
# V3.3 FOUR-PATHWAY SAME-NET-POWER NORMALIZATION
# ============================================================

comparison_net_kw = float(normalized_target_kw)

# Conventional gasoline: no modeled process parasitic load.
norm_conv_fuel_kg_h = comparison_net_kw / (conventional_eff * gasoline_lhv)
norm_conv_fuel_l_h = norm_conv_fuel_kg_h / fuel_density
norm_conv_co2_kg_h = norm_conv_fuel_kg_h * CO2_KG_PER_KG_FUEL_COMPLETE_OX
norm_conv_cost_chf_h = norm_conv_fuel_l_h * gasoline_price_chf_l

# Dry HPRS: use the current effective plasma SEI as a scalable specific-energy
# assumption. This is exact for the continuous-SEI model and a local scaling
# approximation for the pulsed operating point.
dry_h2_gross_per_kg_fuel = H2_KG_PER_KG_FUEL_IDEAL * reactor_conversion
dry_h2_delivered_per_kg_fuel = dry_h2_gross_per_kg_fuel * h2_recovery
dry_gross_shaft_per_kg_fuel = (
    dry_h2_delivered_per_kg_fuel * H2_LHV_KWH_KG * engine_eff
)
dry_plasma_gross_e_per_kg_fuel = dry_h2_gross_per_kg_fuel * effective_plasma_sei
dry_plasma_external_e_per_kg_fuel = (
    dry_plasma_gross_e_per_kg_fuel * (1.0 - recovery_offset)
)
dry_plasma_shaft_burden_per_kg_fuel = (
    dry_plasma_external_e_per_kg_fuel / generator_eff
    if generator_eff > 0 else math.inf
)
dry_net_shaft_per_kg_fuel = (
    dry_gross_shaft_per_kg_fuel - dry_plasma_shaft_burden_per_kg_fuel
)

if dry_net_shaft_per_kg_fuel > 0:
    norm_dry_fuel_kg_h = comparison_net_kw / dry_net_shaft_per_kg_fuel
    norm_dry_fuel_l_h = norm_dry_fuel_kg_h / fuel_density
    norm_dry_h2_gross_kg_h = norm_dry_fuel_kg_h * dry_h2_gross_per_kg_fuel
    norm_dry_h2_to_engine_kg_h = norm_dry_fuel_kg_h * dry_h2_delivered_per_kg_fuel
    norm_dry_plasma_external_kw = (
        norm_dry_fuel_kg_h * dry_plasma_external_e_per_kg_fuel
    )
    norm_dry_carbon_captured_kg_h = (
        norm_dry_fuel_kg_h
        * C_KG_PER_KG_FUEL_IDEAL
        * reactor_conversion
        * carbon_capture
    )
    norm_dry_uncaptured_c_kg_h = (
        norm_dry_fuel_kg_h
        * C_KG_PER_KG_FUEL_IDEAL
        * reactor_conversion
        * (1.0 - carbon_capture)
    )
    norm_dry_uncaptured_co2_potential_kg_h = (
        norm_dry_uncaptured_c_kg_h * CO2_PER_C
    )
    norm_dry_cost_chf_h = norm_dry_fuel_l_h * gasoline_price_chf_l
else:
    norm_dry_fuel_kg_h = math.inf
    norm_dry_fuel_l_h = math.inf
    norm_dry_h2_gross_kg_h = math.inf
    norm_dry_h2_to_engine_kg_h = math.inf
    norm_dry_plasma_external_kw = math.inf
    norm_dry_carbon_captured_kg_h = math.inf
    norm_dry_uncaptured_co2_potential_kg_h = math.inf
    norm_dry_cost_chf_h = math.inf

# Steam-assisted route. Thermal demand is reported separately; electrical
# auxiliaries are treated as an onboard parasitic shaft burden.
steam_h2_gross_per_kg_fuel = steam_h2_yield_kg_per_kg_fuel * reactor_conversion
steam_h2_delivered_per_kg_fuel = steam_h2_gross_per_kg_fuel * h2_recovery
steam_gross_shaft_per_kg_fuel = (
    steam_h2_delivered_per_kg_fuel * H2_LHV_KWH_KG * engine_eff
)
steam_electrical_per_kg_fuel = (
    steam_h2_gross_per_kg_fuel * steam_electrical_aux
)
steam_electrical_shaft_burden_per_kg_fuel = (
    steam_electrical_per_kg_fuel / generator_eff
    if generator_eff > 0 else math.inf
)
steam_net_shaft_per_kg_fuel = (
    steam_gross_shaft_per_kg_fuel - steam_electrical_shaft_burden_per_kg_fuel
)

if steam_net_shaft_per_kg_fuel > 0:
    norm_steam_fuel_kg_h = comparison_net_kw / steam_net_shaft_per_kg_fuel
    norm_steam_fuel_l_h = norm_steam_fuel_kg_h / fuel_density
    norm_steam_h2_gross_kg_h = norm_steam_fuel_kg_h * steam_h2_gross_per_kg_fuel
    norm_steam_h2_to_engine_kg_h = (
        norm_steam_fuel_kg_h * steam_h2_delivered_per_kg_fuel
    )
    norm_steam_water_gross_kg_h = (
        norm_steam_fuel_kg_h * steam_water_kg_per_kg_fuel
    )
    norm_steam_water_makeup_l_h = (
        norm_steam_water_gross_kg_h * (1.0 - water_recycle)
    )
    norm_steam_electrical_kw = (
        norm_steam_h2_gross_kg_h * steam_electrical_aux
    )
    norm_steam_thermal_gross_kw = (
        norm_steam_h2_gross_kg_h * steam_thermal_energy
    )
    norm_steam_thermal_external_kw = (
        norm_steam_thermal_gross_kw * (1.0 - steam_heat_recovery)
    )

    if steam_route == "Steam reforming + WGS":
        norm_steam_co2_kg_h = (
            norm_steam_fuel_kg_h
            * CO2_KG_PER_KG_FUEL_STEAM_WGS
            * reactor_conversion
        )
        norm_steam_co_kg_h = 0.0
        norm_steam_co2_equiv_from_co_kg_h = 0.0
    else:
        norm_steam_co_kg_h = (
            norm_steam_fuel_kg_h
            * steam_co_kg_per_kg_fuel
            * reactor_conversion
        )
        norm_steam_co2_kg_h = 0.0
        norm_steam_co2_equiv_from_co_kg_h = (
            norm_steam_co_kg_h * (44.0095 / 28.0101)
        )

    norm_steam_fuel_cost_chf_h = norm_steam_fuel_l_h * gasoline_price_chf_l
    norm_steam_water_cost_chf_h = (
        norm_steam_water_makeup_l_h / 1000.0 * water_price_chf_m3
    )
    norm_steam_thermal_cost_chf_h = (
        norm_steam_thermal_external_kw * thermal_energy_price_chf_kwh
    )
    # Electrical auxiliaries are modeled as onboard shaft burden in the main
    # normalized comparison, so their energy is already reflected in fuel use.
    norm_steam_cost_chf_h = (
        norm_steam_fuel_cost_chf_h
        + norm_steam_water_cost_chf_h
        + norm_steam_thermal_cost_chf_h
    )
else:
    norm_steam_fuel_kg_h = math.inf
    norm_steam_fuel_l_h = math.inf
    norm_steam_h2_gross_kg_h = math.inf
    norm_steam_h2_to_engine_kg_h = math.inf
    norm_steam_water_makeup_l_h = math.inf
    norm_steam_electrical_kw = math.inf
    norm_steam_thermal_gross_kw = math.inf
    norm_steam_thermal_external_kw = math.inf
    norm_steam_co2_kg_h = math.inf
    norm_steam_co_kg_h = math.inf
    norm_steam_co2_equiv_from_co_kg_h = math.inf
    norm_steam_cost_chf_h = math.inf

# HPRS-W water splitting: external electricity/heat -> H2 -> H2 engine.
# It contains no gasoline. External process electricity is an energy input, not
# silently subtracted from engine shaft output in the main normalized comparison.
norm_hprsw_h2_delivered_kg_h = (
    comparison_net_kw / (engine_eff * H2_LHV_KWH_KG)
    if engine_eff > 0 else math.inf
)
norm_hprsw_h2_gross_kg_h = (
    norm_hprsw_h2_delivered_kg_h / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)
norm_hprsw_electric_kw = (
    norm_hprsw_h2_gross_kg_h * hprsw_plasma_electricity
)
norm_hprsw_thermal_gross_kw = (
    norm_hprsw_h2_gross_kg_h * hprsw_steam_preheat
)
norm_hprsw_thermal_external_kw = (
    norm_hprsw_thermal_gross_kw * (1.0 - hprsw_heat_recovery)
)

norm_hprsw_water_stoich_kg_h = (
    norm_hprsw_h2_gross_kg_h * WATER_KG_PER_KG_H2_STOICH
)
norm_hprsw_water_circulation_kg_h = (
    norm_hprsw_water_stoich_kg_h * hprsw_steam_excess
)
norm_hprsw_water_excess_kg_h = max(
    norm_hprsw_water_circulation_kg_h - norm_hprsw_water_stoich_kg_h, 0.0
)
norm_hprsw_water_makeup_l_h = (
    norm_hprsw_water_stoich_kg_h
    + norm_hprsw_water_excess_kg_h * (1.0 - hprsw_excess_steam_recycle)
)

norm_hprsw_o2_recovered_kg_h = (
    norm_hprsw_h2_gross_kg_h
    * O2_KG_PER_KG_H2_STOICH
    * hprsw_o2_recovery
)
norm_hprsw_argon_makeup_kg_h = (
    norm_hprsw_h2_gross_kg_h
    * hprsw_argon_circulation
    * (1.0 - hprsw_argon_recovery)
)

norm_hprsw_water_cost_chf_h = (
    norm_hprsw_water_makeup_l_h / 1000.0 * water_price_chf_m3
)
norm_hprsw_electric_cost_chf_h = (
    norm_hprsw_electric_kw * electricity_price_chf_kwh
)
norm_hprsw_thermal_cost_chf_h = (
    norm_hprsw_thermal_external_kw * thermal_energy_price_chf_kwh
)
norm_hprsw_argon_cost_chf_h = (
    norm_hprsw_argon_makeup_kg_h * argon_price_chf_kg
)
norm_hprsw_o2_credit_chf_h = (
    norm_hprsw_o2_recovered_kg_h * oxygen_value_chf_kg
)
norm_hprsw_cost_chf_h = max(
    0.0,
    norm_hprsw_electric_cost_chf_h
    + norm_hprsw_thermal_cost_chf_h
    + norm_hprsw_water_cost_chf_h
    + norm_hprsw_argon_cost_chf_h
    - norm_hprsw_o2_credit_chf_h
)

norm_hprsw_total_input_kw = (
    norm_hprsw_electric_kw + norm_hprsw_thermal_external_kw
)
norm_hprsw_total_eff = (
    comparison_net_kw / norm_hprsw_total_input_kw
    if norm_hprsw_total_input_kw > 0 else 0.0
)

# ============================================================
# V3.3 ADVANCED THEORETICAL HPRS-W DIAGNOSTICS
# ============================================================

# 1) Standard-state water-splitting thermodynamics and simple exergy view.
hprsw_external_heat_per_gross_h2 = (
    hprsw_steam_preheat * (1.0 - hprsw_heat_recovery)
)
hprsw_total_external_energy_per_gross_h2 = (
    hprsw_plasma_electricity + hprsw_external_heat_per_gross_h2
)
hprsw_total_external_energy_per_delivered_h2 = (
    hprsw_total_external_energy_per_gross_h2 / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)
hprsw_electricity_per_delivered_h2_advanced = (
    hprsw_plasma_electricity / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)

hprsw_t0_k = hprsw_ambient_temp_c + 273.15
hprsw_heat_source_k = hprsw_heat_source_temp_c + 273.15
hprsw_heat_exergy_factor = (
    max(0.0, min(1.0, 1.0 - hprsw_t0_k / hprsw_heat_source_k))
    if hprsw_heat_source_k > hprsw_t0_k else 0.0
)
hprsw_external_heat_exergy_per_gross_h2 = (
    hprsw_external_heat_per_gross_h2 * hprsw_heat_exergy_factor
)
hprsw_external_exergy_per_gross_h2 = (
    hprsw_plasma_electricity + hprsw_external_heat_exergy_per_gross_h2
)
hprsw_external_exergy_per_delivered_h2 = (
    hprsw_external_exergy_per_gross_h2 / hprsw_recovery_chain
    if hprsw_recovery_chain > 0 else math.inf
)
hprsw_second_law_eff = (
    WATER_SPLIT_REV_KWH_PER_KG_H2 / hprsw_external_exergy_per_delivered_h2
    if hprsw_external_exergy_per_delivered_h2 > 0 else 0.0
)
hprsw_hhv_energy_eff = (
    WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2
    / hprsw_total_external_energy_per_delivered_h2
    if hprsw_total_external_energy_per_delivered_h2 > 0 else 0.0
)
hprsw_standard_energy_margin_gross = (
    hprsw_total_external_energy_per_gross_h2
    - WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2
)
hprsw_standard_exergy_margin_gross = (
    hprsw_external_exergy_per_gross_h2
    - WATER_SPLIT_REV_KWH_PER_KG_H2
)

# 2) Electric field and reduced field E/N.
hprsw_gap_m = max(hprsw_electrode_gap_mm * 1e-3, 1e-9)
hprsw_field_v_m = hprsw_field_voltage_v / hprsw_gap_m
hprsw_field_v_cm = hprsw_field_v_m / 100.0
hprsw_sep_temp_k = hprsw_separation_temp_c + 273.15
hprsw_pressure_pa = hprsw_pressure_bar * 1e5
hprsw_number_density_m3 = (
    hprsw_pressure_pa / (BOLTZMANN_J_K * hprsw_sep_temp_k)
    if hprsw_sep_temp_k > 0 else math.inf
)
hprsw_reduced_field_td = (
    hprsw_field_v_m / hprsw_number_density_m3 * 1e21
    if hprsw_number_density_m3 > 0 else math.inf
)

# 3) Ion-drift and quench timescale diagnostics.
hprsw_ion_mobility_m2_vs = hprsw_ion_mobility_cm2_vs * 1e-4
hprsw_ion_drift_velocity_m_s = hprsw_ion_mobility_m2_vs * hprsw_field_v_m
hprsw_sep_distance_m = hprsw_separation_distance_mm * 1e-3
hprsw_ion_separation_time_s = (
    hprsw_sep_distance_m / hprsw_ion_drift_velocity_m_s
    if hprsw_ion_drift_velocity_m_s > 0 else math.inf
)
hprsw_residence_time_s = max(hprsw_residence_time_ms * 1e-3, 1e-12)
hprsw_separation_timescale_index = (
    hprsw_residence_time_s / hprsw_ion_separation_time_s
    if hprsw_ion_separation_time_s > 0 and math.isfinite(hprsw_ion_separation_time_s)
    else 0.0
)
hprsw_ion_drift_distance_m = (
    hprsw_ion_drift_velocity_m_s * hprsw_residence_time_s
)

hprsw_plasma_temp_k = hprsw_plasma_temp_c + 273.15
hprsw_quench_outlet_temp_k = hprsw_quench_outlet_temp_c + 273.15
hprsw_quench_delta_t_k = max(
    hprsw_plasma_temp_k - hprsw_quench_outlet_temp_k, 0.0
)
hprsw_quench_cooling_rate_k_s = (
    hprsw_quench_delta_t_k / hprsw_quench_time_s
    if hprsw_quench_time_s > 0 else math.inf
)
hprsw_quench_vs_recomb_ratio = (
    hprsw_recomb_tau_s / hprsw_quench_time_s
    if hprsw_quench_time_s > 0 else math.inf
)

# 4) First-order reactor sizing on the same-net-power HPRS-W case.
hprsw_norm_argon_circulation_kg_h = (
    norm_hprsw_h2_gross_kg_h * hprsw_argon_circulation
)
hprsw_steam_mol_s = (
    norm_hprsw_water_circulation_kg_h / (WATER_MOLAR / 1000.0) / 3600.0
)
hprsw_argon_mol_s = (
    hprsw_norm_argon_circulation_kg_h / ARGON_MOLAR_KG / 3600.0
    if ARGON_MOLAR_KG > 0 else 0.0
)
hprsw_total_feed_mol_s = hprsw_steam_mol_s + hprsw_argon_mol_s
hprsw_feed_volumetric_m3_s = (
    hprsw_total_feed_mol_s * GAS_CONSTANT_J_MOL_K * hprsw_sep_temp_k
    / hprsw_pressure_pa
    if hprsw_pressure_pa > 0 else math.inf
)
hprsw_active_volume_m3 = hprsw_feed_volumetric_m3_s * hprsw_residence_time_s
hprsw_active_volume_l = hprsw_active_volume_m3 * 1000.0
hprsw_core_diameter_m = (
    (4.0 * hprsw_active_volume_m3 / (math.pi * hprsw_reactor_aspect_ratio)) ** (1.0 / 3.0)
    if hprsw_active_volume_m3 > 0 and hprsw_reactor_aspect_ratio > 0 else 0.0
)
hprsw_core_length_m = hprsw_core_diameter_m * hprsw_reactor_aspect_ratio
hprsw_core_electric_kw = norm_hprsw_electric_kw * hprsw_plasma_power_share
hprsw_power_density_kw_l = (
    hprsw_core_electric_kw / hprsw_active_volume_l
    if hprsw_active_volume_l > 0 else math.inf
)

hprsw_hot_stream_mass_kg_s = (
    (norm_hprsw_water_circulation_kg_h + hprsw_norm_argon_circulation_kg_h)
    / 3600.0
)
hprsw_quench_sensible_duty_kw = (
    hprsw_hot_stream_mass_kg_s
    * hprsw_effective_hot_gas_cp
    * hprsw_quench_delta_t_k
)
hprsw_coolant_flow_kg_s = (
    hprsw_quench_sensible_duty_kw / (4.18 * hprsw_coolant_delta_t_c)
    if hprsw_coolant_delta_t_c > 0 else math.inf
)
hprsw_coolant_flow_l_min = hprsw_coolant_flow_kg_s * 60.0

# 5) Automatic HPRS-W break-even solver versus conventional gasoline.
hprsw_shaft_kwh_per_kg_delivered = engine_eff * H2_LHV_KWH_KG
hprsw_allowed_total_gross_for_energy_parity = (
    hprsw_shaft_kwh_per_kg_delivered * hprsw_recovery_chain / conventional_eff
    if conventional_eff > 0 else math.inf
)
hprsw_max_plasma_kwhkg_energy_parity = (
    hprsw_allowed_total_gross_for_energy_parity
    - hprsw_external_heat_per_gross_h2
)
hprsw_energy_parity_thermoneutral_margin = (
    hprsw_allowed_total_gross_for_energy_parity
    - WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2
)
hprsw_required_recovery_chain_energy_parity = (
    conventional_eff * hprsw_total_external_energy_per_gross_h2
    / hprsw_shaft_kwh_per_kg_delivered
    if hprsw_shaft_kwh_per_kg_delivered > 0 else math.inf
)
hprsw_required_engine_eff_energy_parity = (
    conventional_eff * hprsw_total_external_energy_per_gross_h2
    / (H2_LHV_KWH_KG * hprsw_recovery_chain)
    if hprsw_recovery_chain > 0 else math.inf
)

if hprsw_steam_preheat > 0:
    hprsw_required_heat_recovery_energy_parity = 1.0 - (
        hprsw_allowed_total_gross_for_energy_parity - hprsw_plasma_electricity
    ) / hprsw_steam_preheat
else:
    hprsw_required_heat_recovery_energy_parity = 0.0

hprsw_water_makeup_per_gross_h2_l = (
    WATER_KG_PER_KG_H2_STOICH
    + WATER_KG_PER_KG_H2_STOICH
    * max(hprsw_steam_excess - 1.0, 0.0)
    * (1.0 - hprsw_excess_steam_recycle)
)
hprsw_argon_makeup_per_gross_h2_kg = (
    hprsw_argon_circulation * (1.0 - hprsw_argon_recovery)
)
hprsw_o2_recovered_per_gross_h2_kg = (
    O2_KG_PER_KG_H2_STOICH * hprsw_o2_recovery
)
hprsw_other_cost_per_gross_h2_chf = (
    hprsw_external_heat_per_gross_h2 * thermal_energy_price_chf_kwh
    + hprsw_water_makeup_per_gross_h2_l / 1000.0 * water_price_chf_m3
    + hprsw_argon_makeup_per_gross_h2_kg * argon_price_chf_kg
    - hprsw_o2_recovered_per_gross_h2_kg * oxygen_value_chf_kg
)
hprsw_conv_cost_benchmark_per_net_kwh = (
    norm_conv_cost_chf_h / comparison_net_kw
    if comparison_net_kw > 0 else math.inf
)
hprsw_allowed_cost_per_gross_h2_chf = (
    hprsw_conv_cost_benchmark_per_net_kwh
    * hprsw_shaft_kwh_per_kg_delivered
    * hprsw_recovery_chain
)

if electricity_price_chf_kwh > 0:
    hprsw_max_plasma_kwhkg_cost_parity = (
        hprsw_allowed_cost_per_gross_h2_chf - hprsw_other_cost_per_gross_h2_chf
    ) / electricity_price_chf_kwh
else:
    hprsw_max_plasma_kwhkg_cost_parity = math.inf

if hprsw_plasma_electricity > 0:
    hprsw_break_even_electricity_price_chf_kwh = (
        hprsw_allowed_cost_per_gross_h2_chf - hprsw_other_cost_per_gross_h2_chf
    ) / hprsw_plasma_electricity
else:
    hprsw_break_even_electricity_price_chf_kwh = math.inf

# ============================================================
# V3.3 MULTI-PARAMETER FEASIBLE-REGION SOLVER
# ============================================================
# This deterministic grid scan varies four coupled HPRS-W levers together:
# plasma electricity, total delivered/gross H2 recovery, H2-engine brake
# efficiency, and heat recovery. It is not a probabilistic Monte Carlo model.
#
# Two standard-state screening guards are enforced:
#   1) total external energy >= Delta H (thermoneutral reference), and
#   2) external exergy >= Delta G (reversible-work reference).
# External heat exergy is approximated with the same Carnot factor used in the
# V3.3 advanced exergy diagnostic. These guards do not replace temperature-
# dependent equilibrium or non-equilibrium plasma chemistry.

def _v29_linspace(lo, hi, n):
    lo = float(lo)
    hi = float(hi)
    n = max(int(n), 2)
    if hi <= lo:
        return [lo]
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]

_v29_resolution_counts = {
    "Coarse": (7, 6, 7, 6),
    "Standard": (11, 8, 11, 8),
    "Fine": (17, 12, 17, 12),
}
_v29_np, _v29_nr, _v29_ne, _v29_nh = _v29_resolution_counts[v29_grid_resolution]

_v29_plasma_values = _v29_linspace(
    v29_plasma_search_range[0], v29_plasma_search_range[1], _v29_np
)
_v29_recovery_values = [
    x / 100.0 for x in _v29_linspace(
        v29_recovery_search_range_pct[0],
        v29_recovery_search_range_pct[1],
        _v29_nr,
    )
]
_v29_engine_values = [
    x / 100.0 for x in _v29_linspace(
        v29_engine_search_range_pct[0],
        v29_engine_search_range_pct[1],
        _v29_ne,
    )
]
_v29_heat_recovery_values = [
    x / 100.0 for x in _v29_linspace(
        v29_heat_recovery_search_range_pct[0],
        v29_heat_recovery_search_range_pct[1],
        _v29_nh,
    )
]

v29_total_grid_points = (
    len(_v29_plasma_values)
    * len(_v29_recovery_values)
    * len(_v29_engine_values)
    * len(_v29_heat_recovery_values)
)

# Non-thermal operating-cost terms per kg gross H2 remain fixed during the scan.
v29_nonthermal_cost_per_gross_h2_chf = (
    hprsw_water_makeup_per_gross_h2_l / 1000.0 * water_price_chf_m3
    + hprsw_argon_makeup_per_gross_h2_kg * argon_price_chf_kg
    - hprsw_o2_recovered_per_gross_h2_kg * oxygen_value_chf_kg
)

v29_thermo_points = []
v29_energy_competitive_points = []
v29_dual_competitive_points = []
v29_cost_competitive_points = []

_v29_p_span = max(v29_plasma_search_range[1] - v29_plasma_search_range[0], 1e-9)
_v29_r_span = max(
    (v29_recovery_search_range_pct[1] - v29_recovery_search_range_pct[0]) / 100.0,
    1e-9,
)
_v29_e_span = max(
    (v29_engine_search_range_pct[1] - v29_engine_search_range_pct[0]) / 100.0,
    1e-9,
)
_v29_h_span = max(
    (v29_heat_recovery_search_range_pct[1] - v29_heat_recovery_search_range_pct[0]) / 100.0,
    1e-9,
)

for _p in _v29_plasma_values:
    for _r in _v29_recovery_values:
        for _eta in _v29_engine_values:
            for _hr in _v29_heat_recovery_values:
                _q_ext = hprsw_steam_preheat * (1.0 - _hr)
                _total_energy = _p + _q_ext
                _external_exergy = _p + _q_ext * hprsw_heat_exergy_factor
                _shaft_per_gross_h2 = H2_LHV_KWH_KG * _eta * _r

                _energy_guard_ok = (
                    _total_energy + 1e-9 >= WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2
                )
                _exergy_guard_ok = (
                    _external_exergy + 1e-9 >= WATER_SPLIT_REV_KWH_PER_KG_H2
                )
                _thermo_ok = _energy_guard_ok and _exergy_guard_ok

                _system_eff = (
                    _shaft_per_gross_h2 / _total_energy
                    if _total_energy > 0 else 0.0
                )

                _gross_cost = max(
                    0.0,
                    _p * electricity_price_chf_kwh
                    + _q_ext * thermal_energy_price_chf_kwh
                    + v29_nonthermal_cost_per_gross_h2_chf,
                )
                _cost_per_net_kwh = (
                    _gross_cost / _shaft_per_gross_h2
                    if _shaft_per_gross_h2 > 0 else math.inf
                )

                _energy_competitive = (
                    _thermo_ok and _system_eff + 1e-12 >= conventional_eff
                )
                _cost_competitive = (
                    _thermo_ok
                    and _cost_per_net_kwh <= hprsw_conv_cost_benchmark_per_net_kwh + 1e-12
                )

                # Balanced-stretch score: minimize the largest normalized movement
                # from the currently selected operating point. It intentionally does
                # not claim any one parameter is easier to improve experimentally.
                _stretch_components = [
                    abs(_p - hprsw_plasma_electricity) / _v29_p_span,
                    abs(_r - hprsw_recovery_chain) / _v29_r_span,
                    abs(_eta - engine_eff) / _v29_e_span,
                    abs(_hr - hprsw_heat_recovery) / _v29_h_span,
                ]
                _balanced_stretch = max(_stretch_components)
                _sum_stretch = sum(_stretch_components)

                _point = {
                    "plasma": _p,
                    "recovery": _r,
                    "engine_eff": _eta,
                    "heat_recovery": _hr,
                    "external_heat": _q_ext,
                    "total_energy": _total_energy,
                    "external_exergy": _external_exergy,
                    "shaft_per_gross_h2": _shaft_per_gross_h2,
                    "system_eff": _system_eff,
                    "cost_per_net_kwh": _cost_per_net_kwh,
                    "energy_guard_ok": _energy_guard_ok,
                    "exergy_guard_ok": _exergy_guard_ok,
                    "balanced_stretch": _balanced_stretch,
                    "sum_stretch": _sum_stretch,
                }

                if _thermo_ok:
                    v29_thermo_points.append(_point)
                if _energy_competitive:
                    v29_energy_competitive_points.append(_point)
                if _cost_competitive:
                    v29_cost_competitive_points.append(_point)
                if _energy_competitive and _cost_competitive:
                    v29_dual_competitive_points.append(_point)

v29_thermo_count = len(v29_thermo_points)
v29_energy_competitive_count = len(v29_energy_competitive_points)
v29_cost_competitive_count = len(v29_cost_competitive_points)
v29_dual_competitive_count = len(v29_dual_competitive_points)

v29_thermo_share = (
    v29_thermo_count / v29_total_grid_points if v29_total_grid_points else 0.0
)
v29_energy_share_of_thermo = (
    v29_energy_competitive_count / v29_thermo_count if v29_thermo_count else 0.0
)
v29_dual_share_of_thermo = (
    v29_dual_competitive_count / v29_thermo_count if v29_thermo_count else 0.0
)

v29_balanced_energy_candidate = (
    min(
        v29_energy_competitive_points,
        key=lambda x: (x["balanced_stretch"], x["sum_stretch"], x["total_energy"]),
    )
    if v29_energy_competitive_points else None
)
v29_lowest_energy_candidate = (
    min(
        v29_energy_competitive_points,
        key=lambda x: (x["total_energy"], -x["system_eff"]),
    )
    if v29_energy_competitive_points else None
)
v29_lowest_cost_dual_candidate = (
    min(
        v29_dual_competitive_points,
        key=lambda x: (x["cost_per_net_kwh"], x["total_energy"]),
    )
    if v29_dual_competitive_points else None
)


# ============================================================
# V3.3 PARETO-FRONTIER ANALYSIS
# ============================================================
# Primary Pareto definition:
#   - maximize screened total-energy-to-shaft efficiency
#   - minimize modeled operating cost per net kWh
# over thermodynamically feasible HPRS-W grid points.
#
# A point is on the 2D cost/efficiency frontier if no cheaper point
# has equal or higher efficiency. The research-stretch proxy is kept
# separate so the Pareto frontier is not silently turned into a weighted
# optimization problem.

def _v30_cost_eff_pareto(points):
    finite_points = [
        p for p in points
        if math.isfinite(p["cost_per_net_kwh"]) and math.isfinite(p["system_eff"])
    ]
    ordered = sorted(
        finite_points,
        key=lambda p: (
            p["cost_per_net_kwh"],
            -p["system_eff"],
            p["total_energy"],
            p["plasma"],
        ),
    )
    frontier = []
    best_eff_seen = -math.inf
    for p in ordered:
        if p["system_eff"] > best_eff_seen + 1e-12:
            frontier.append(p)
            best_eff_seen = p["system_eff"]
    return frontier


def _v30_stretch_eff_pareto(points):
    finite_points = [
        p for p in points
        if math.isfinite(p["balanced_stretch"]) and math.isfinite(p["system_eff"])
    ]
    ordered = sorted(
        finite_points,
        key=lambda p: (
            p["balanced_stretch"],
            -p["system_eff"],
            p["total_energy"],
        ),
    )
    frontier = []
    best_eff_seen = -math.inf
    for p in ordered:
        if p["system_eff"] > best_eff_seen + 1e-12:
            frontier.append(p)
            best_eff_seen = p["system_eff"]
    return frontier


def _v30_point_key(p):
    return (
        round(p["plasma"], 10),
        round(p["recovery"], 10),
        round(p["engine_eff"], 10),
        round(p["heat_recovery"], 10),
    )


v30_cost_eff_pareto_points = _v30_cost_eff_pareto(v29_thermo_points)
v30_stretch_eff_pareto_points = _v30_stretch_eff_pareto(v29_thermo_points)

_v30_pareto_keys = {_v30_point_key(p) for p in v30_cost_eff_pareto_points}
_v30_dual_keys = {_v30_point_key(p) for p in v29_dual_competitive_points}
v30_dual_pareto_points = [
    p for p in v30_cost_eff_pareto_points
    if _v30_point_key(p) in _v30_dual_keys
]

v30_lowest_cost_point = (
    min(v29_thermo_points, key=lambda p: (p["cost_per_net_kwh"], -p["system_eff"]))
    if v29_thermo_points else None
)
v30_max_efficiency_point = (
    max(v29_thermo_points, key=lambda p: (p["system_eff"], -p["cost_per_net_kwh"]))
    if v29_thermo_points else None
)
v30_lowest_plasma_dual_point = (
    min(
        v29_dual_competitive_points,
        key=lambda p: (p["plasma"], p["cost_per_net_kwh"], -p["system_eff"]),
    )
    if v29_dual_competitive_points else None
)
v30_min_stretch_dual_point = (
    min(
        v29_dual_competitive_points,
        key=lambda p: (
            p["balanced_stretch"],
            p["sum_stretch"],
            p["cost_per_net_kwh"],
        ),
    )
    if v29_dual_competitive_points else None
)

# Transparent "knee" proxy on the cost-efficiency Pareto frontier.
# It minimizes equal-weight normalized distance from the ideal corner:
# lowest cost + highest efficiency. It is only a decision aid.
if v30_cost_eff_pareto_points:
    _v30_cost_min = min(p["cost_per_net_kwh"] for p in v30_cost_eff_pareto_points)
    _v30_cost_max = max(p["cost_per_net_kwh"] for p in v30_cost_eff_pareto_points)
    _v30_eff_min = min(p["system_eff"] for p in v30_cost_eff_pareto_points)
    _v30_eff_max = max(p["system_eff"] for p in v30_cost_eff_pareto_points)
    _v30_cost_span = max(_v30_cost_max - _v30_cost_min, 1e-12)
    _v30_eff_span = max(_v30_eff_max - _v30_eff_min, 1e-12)

    for _pnt in v30_cost_eff_pareto_points:
        _cost_norm = (_pnt["cost_per_net_kwh"] - _v30_cost_min) / _v30_cost_span
        _eff_loss_norm = (_v30_eff_max - _pnt["system_eff"]) / _v30_eff_span
        _pnt["_v30_knee_score"] = math.sqrt(
            _cost_norm * _cost_norm + _eff_loss_norm * _eff_loss_norm
        )

    v30_knee_point = min(
        v30_cost_eff_pareto_points,
        key=lambda p: (p["_v30_knee_score"], p["balanced_stretch"]),
    )
else:
    v30_knee_point = None

v30_pareto_count = len(v30_cost_eff_pareto_points)
v30_dual_pareto_count = len(v30_dual_pareto_points)


# ============================================================
# V3.3 PROTOTYPE-ORIENTED TARGET SCREEN
# ============================================================
# This is deliberately a second-stage engineering screen layered on top of
# the thermodynamic guards. The limits below are user-selectable and are not
# physical laws or measured hardware limits. The default plasma-electricity
# floor is a conservative target-screen assumption; ΔH and ΔG remain the
# actual standard-state thermodynamic guards in this model.

v31_proto_max_recovery = v31_proto_max_recovery_pct / 100.0
v31_proto_max_engine_bte = v31_proto_max_engine_bte_pct / 100.0
v31_proto_max_heat_recovery = v31_proto_max_heat_recovery_pct / 100.0

v31_prototype_points = [
    p for p in v29_thermo_points
    if p["plasma"] + 1e-12 >= v31_proto_min_plasma
    and p["recovery"] <= v31_proto_max_recovery + 1e-12
    and p["engine_eff"] <= v31_proto_max_engine_bte + 1e-12
    and p["heat_recovery"] <= v31_proto_max_heat_recovery + 1e-12
]

v31_prototype_energy_points = [
    p for p in v31_prototype_points
    if p["system_eff"] + 1e-12 >= conventional_eff
]

v31_prototype_dual_points = [
    p for p in v31_prototype_energy_points
    if p["cost_per_net_kwh"] <= hprsw_conv_cost_benchmark_per_net_kwh + 1e-12
]

v31_prototype_target = (
    min(
        v31_prototype_energy_points,
        key=lambda p: (
            p["balanced_stretch"],
            p["sum_stretch"],
            p["cost_per_net_kwh"],
            p["total_energy"],
        ),
    )
    if v31_prototype_energy_points else None
)

v31_prototype_dual_target = (
    min(
        v31_prototype_dual_points,
        key=lambda p: (
            p["balanced_stretch"],
            p["sum_stretch"],
            p["cost_per_net_kwh"],
        ),
    )
    if v31_prototype_dual_points else None
)

# If no prototype-screen point reaches energy parity, retain the best available
# point so the UI can explain how far the constrained region is from parity.
v31_prototype_best_available = (
    max(
        v31_prototype_points,
        key=lambda p: (p["system_eff"], -p["cost_per_net_kwh"]),
    )
    if v31_prototype_points else None
)

v31_prototype_display_target = (
    v31_prototype_target
    if v31_prototype_target is not None
    else v31_prototype_best_available
)

v31_prototype_count = len(v31_prototype_points)
v31_prototype_energy_count = len(v31_prototype_energy_points)
v31_prototype_dual_count = len(v31_prototype_dual_points)


def _v31_break_even_electricity_price(p):
    if p is None or p["plasma"] <= 0 or p["shaft_per_gross_h2"] <= 0:
        return math.inf
    _allowable_gross_cost = (
        hprsw_conv_cost_benchmark_per_net_kwh * p["shaft_per_gross_h2"]
    )
    _non_electric_cost = (
        p["external_heat"] * thermal_energy_price_chf_kwh
        + v29_nonthermal_cost_per_gross_h2_chf
    )
    return max(0.0, (_allowable_gross_cost - _non_electric_cost) / p["plasma"])

v31_prototype_break_even_electricity_price = _v31_break_even_electricity_price(
    v31_prototype_display_target
)

# Current selected HPRS-W point under the same V3.3 guards.
v29_current_total_energy = hprsw_total_external_energy_per_gross_h2
v29_current_external_exergy = hprsw_external_exergy_per_gross_h2
v29_current_shaft_per_gross_h2 = H2_LHV_KWH_KG * engine_eff * hprsw_recovery_chain
v29_current_system_eff = (
    v29_current_shaft_per_gross_h2 / v29_current_total_energy
    if v29_current_total_energy > 0 else 0.0
)
v29_current_thermo_ok = (
    v29_current_total_energy + 1e-9 >= WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2
    and v29_current_external_exergy + 1e-9 >= WATER_SPLIT_REV_KWH_PER_KG_H2
)
v29_current_energy_competitive = (
    v29_current_thermo_ok and v29_current_system_eff + 1e-12 >= conventional_eff
)
v29_current_cost_per_net_kwh = (
    hprsw_other_cost_per_gross_h2_chf
    + hprsw_plasma_electricity * electricity_price_chf_kwh
) / v29_current_shaft_per_gross_h2 if v29_current_shaft_per_gross_h2 > 0 else math.inf
v29_current_cost_competitive = (
    v29_current_thermo_ok
    and v29_current_cost_per_net_kwh <= hprsw_conv_cost_benchmark_per_net_kwh + 1e-12
)

# Per-kWh-net indicators.
def per_net(value):
    return value / comparison_net_kw if comparison_net_kw > 0 else math.inf

norm_conv_l_per_kwh = per_net(norm_conv_fuel_l_h)
norm_conv_co2_per_kwh = per_net(norm_conv_co2_kg_h)
norm_conv_cost_per_kwh = per_net(norm_conv_cost_chf_h)

norm_dry_l_per_kwh = per_net(norm_dry_fuel_l_h)
norm_dry_h2_per_kwh = per_net(norm_dry_h2_to_engine_kg_h)
norm_dry_electric_per_kwh = per_net(norm_dry_plasma_external_kw)
norm_dry_captured_c_per_kwh = per_net(norm_dry_carbon_captured_kg_h)
norm_dry_uncaptured_co2_potential_per_kwh = per_net(
    norm_dry_uncaptured_co2_potential_kg_h
)
norm_dry_cost_per_kwh = per_net(norm_dry_cost_chf_h)

norm_steam_l_per_kwh = per_net(norm_steam_fuel_l_h)
norm_steam_h2_per_kwh = per_net(norm_steam_h2_to_engine_kg_h)
norm_steam_water_l_per_kwh = per_net(norm_steam_water_makeup_l_h)
norm_steam_electric_per_kwh = per_net(norm_steam_electrical_kw)
norm_steam_thermal_external_per_kwh = per_net(norm_steam_thermal_external_kw)
norm_steam_cost_per_kwh = per_net(norm_steam_cost_chf_h)

norm_hprsw_h2_per_kwh = per_net(norm_hprsw_h2_delivered_kg_h)
norm_hprsw_water_l_per_kwh = per_net(norm_hprsw_water_makeup_l_h)
norm_hprsw_electric_per_kwh = per_net(norm_hprsw_electric_kw)
norm_hprsw_thermal_external_per_kwh = per_net(norm_hprsw_thermal_external_kw)
norm_hprsw_o2_per_kwh = per_net(norm_hprsw_o2_recovered_kg_h)
norm_hprsw_argon_makeup_per_kwh = per_net(norm_hprsw_argon_makeup_kg_h)
norm_hprsw_cost_per_kwh = per_net(norm_hprsw_cost_chf_h)

if steam_route == "Steam reforming + WGS":
    norm_steam_carbon_metric = f"{per_net(norm_steam_co2_kg_h):.3f} kg CO₂/kWh net"
else:
    norm_steam_carbon_metric = (
        f"{per_net(norm_steam_co_kg_h):.3f} kg CO/kWh net; "
        f"{per_net(norm_steam_co2_equiv_from_co_kg_h):.3f} kg CO₂-eq if oxidized"
    )

norm_conv_total_eff = comparison_net_kw / (
    norm_conv_fuel_kg_h * gasoline_lhv
)
norm_dry_total_eff = (
    comparison_net_kw / (norm_dry_fuel_kg_h * gasoline_lhv)
    if math.isfinite(norm_dry_fuel_kg_h) else 0.0
)
norm_steam_fuel_eff = (
    comparison_net_kw / (norm_steam_fuel_kg_h * gasoline_lhv)
    if math.isfinite(norm_steam_fuel_kg_h) else 0.0
)
norm_steam_total_input_kw = (
    norm_steam_fuel_kg_h * gasoline_lhv + norm_steam_thermal_external_kw
    if math.isfinite(norm_steam_fuel_kg_h) else math.inf
)
norm_steam_total_eff = (
    comparison_net_kw / norm_steam_total_input_kw
    if norm_steam_total_input_kw > 0 and math.isfinite(norm_steam_total_input_kw)
    else 0.0
)

# Performance-target calculator: work backwards from desired net shaft power.
def max_plasma_gross_power_for_target(target_net_kw):
    available_shaft_kw = gross_engine_kw - target_net_kw
    if available_shaft_kw <= 0:
        return 0.0
    if (1.0 - recovery_offset) <= 0:
        return math.inf
    return available_shaft_kw * generator_eff / (1.0 - recovery_offset)

def max_plasma_sei_for_target(target_net_kw):
    allowed_plasma_kw = max_plasma_gross_power_for_target(target_net_kw)
    if h2_gross_kg_h <= 0:
        return math.inf
    return allowed_plasma_kw / h2_gross_kg_h

# Engineering checkpoints requested for comparison.
target_levels_kw = [x for x in (60.0, 80.0, 100.0) if x <= gross_engine_kw]
if float(gross_engine_kw) not in target_levels_kw:
    target_levels_kw.append(float(gross_engine_kw))
target_levels_kw = sorted(set(target_levels_kw))

# Best-case net shaft if plasma operates exactly at the ideal thermodynamic floor.
plasma_floor_kw = h2_gross_kg_h * THERMO_MIN_KWH_PER_KG_H2
plasma_floor_external_kw = plasma_floor_kw * (1.0 - recovery_offset)
plasma_floor_shaft_burden_kw = (
    plasma_floor_external_kw / generator_eff
    if generator_eff > 0
    else math.inf
)
max_net_at_thermo_floor_kw = gross_engine_kw - plasma_floor_shaft_burden_kw

# V3.3.6: Always-visible charts and compact navigation; physics unchanged.
st.markdown("---")
st.markdown('<span id="horg-graphics" class="horg-section-anchor"></span>', unsafe_allow_html=True)
st.subheader("Research graphics dashboard · V3.3.6")
st.caption(
    "These charts update with the sidebar assumptions. All automotive results use the same "
    f"net shaft-power target ({comparison_net_kw:.0f} kW). Values are model scenarios, not measurements."
)
_chart_paths = ["Conventional ICE", "Dry HPRS", "Gasoline + steam", "HPRS-W water"]
_chart_costs = [norm_conv_cost_per_kwh, norm_dry_cost_per_kwh,
                norm_steam_cost_per_kwh, norm_hprsw_cost_per_kwh]
_chart_electric = [0.0, norm_dry_electric_per_kwh,
                   norm_steam_electric_per_kwh, norm_hprsw_electric_per_kwh]
_chart_summary = pd.DataFrame({
    "Pathway": _chart_paths,
    "CHF / kWh net shaft": _chart_costs,
    "External electricity kWh / kWh net shaft": _chart_electric,
}).set_index("Pathway")
_ch1, _ch2 = st.columns(2)
with _ch1:
    st.markdown("**Operating-cost comparison**")
    st.bar_chart(_chart_summary[["CHF / kWh net shaft"]].replace([math.inf, -math.inf], float("nan")), height=360)
with _ch2:
    st.markdown("**External electrical demand**")
    st.bar_chart(_chart_summary[["External electricity kWh / kWh net shaft"]].replace([math.inf, -math.inf], float("nan")), height=360)
st.caption(
    "Electricity chart excludes chemical fuel energy and separately supplied heat; "
    "use the detailed comparison for total energy and carbon accounting. "
    "Unattainable/non-finite scenarios are omitted from bar heights."
)

if v29_thermo_points and v30_cost_eff_pareto_points:
    st.markdown("**HPRS-W feasible region and Pareto frontier · overview**")
    _preview_step = max(1, len(v29_thermo_points) // 700)
    _pareto_preview = [
        {"Cost CHF/kWh net": p["cost_per_net_kwh"],
         "Efficiency %": 100.0 * p["system_eff"],
         "Series": "Thermo-feasible"}
        for p in v29_thermo_points[::_preview_step]
    ]
    _pareto_preview.extend(
        {"Cost CHF/kWh net": p["cost_per_net_kwh"],
         "Efficiency %": 100.0 * p["system_eff"],
         "Series": "Pareto frontier"}
        for p in v30_cost_eff_pareto_points
    )
    st.scatter_chart(pd.DataFrame(_pareto_preview), x="Cost CHF/kWh net",
                     y="Efficiency %", color="Series", height=390)
else:
    st.info("No thermodynamically feasible Pareto points for the current search settings.")
st.caption(
    "The full Pareto, research-stretch, and theoretical diagnostics remain in the "
    "'HPRS-W advanced theory, feasible-region and Pareto analysis' section below. "
    "The Rail energy and cost graphs remain visible in the Rail section."
)

st.markdown("---")
st.markdown('<span id="horg-automotive" class="horg-section-anchor"></span>', unsafe_allow_html=True)
with st.expander("Automotive / legacy pathway results — open when needed", expanded=False):
    st.caption(f"Current comparison focus: **{comparison_focus}**")

    st.subheader("Scenario result")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fuel to reactor", f"{fuel_kg_h:.1f} kg/h", f"{fuel_l_h:.1f} L/h")
    c2.metric("H₂ to engine", f"{h2_to_engine_kg_h:.2f} kg/h")
    c3.metric("Solid C captured", f"{carbon_captured_kg_h:.1f} kg/h")
    c4.metric("Net shaft after plasma", f"{net_shaft_kw:.1f} kW")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Gross plasma demand", f"{plasma_gross_kw:.1f} kW")
    c6.metric("Effective plasma SEI", f"{effective_plasma_sei:.2f} kWh/kg H₂")
    c7.metric("CO₂-equivalent carbon retained*", f"{co2_retention_equiv_kg_h:.1f} kg/h")
    c8.metric("HPRS net fuel-to-shaft efficiency", f"{100*hprs_net_eff:.1f}%")

    st.caption(
        "*CO₂-equivalent carbon retained is the CO₂ mass the captured carbon could form if fully oxidized. "
        "It is not a lifecycle-emissions claim or a measured tailpipe value."
    )

    if thermo_adequacy_ratio < 1.0:
        st.error(
            "RED — below thermodynamic floor. The selected plasma electrical input "
            "is below the ideal standard-state decomposition floor for the modeled "
            "hydrogen production."
        )
    elif net_shaft_kw <= 0:
        st.error(
            "RED — plasma burden exceeds shaft output. The equivalent shaft demand "
            "required to supply the plasma is greater than the gross H₂-engine output."
        )
    elif hprs_net_eff >= conventional_eff:
        st.success(
            "GREEN — favourable within selected assumptions. The simplified HPRS "
            "net efficiency reaches or exceeds the selected conventional benchmark. "
            "This is a scenario result, not validated hardware performance."
        )
    else:
        st.warning(
            "ORANGE — carbon retention remains interesting, but the simplified net "
            "fuel-to-shaft efficiency is below the selected conventional gasoline benchmark."
        )

    st.subheader("Pulsed Plasma Control")

    if plasma_mode == "Pulsed plasma":
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Pulse frequency", f"{pulse_frequency_khz:.1f} kHz")
        p2.metric("Average pulsed electrical power", f"{derived_pulse_power_kw:.2f} kW")
        p3.metric("Per-cell duty cycle", f"{pulse_duty_cycle:.3f}%")
        p4.metric("Thermodynamic adequacy", f"{100*thermo_adequacy_ratio:.1f}%")

        p5, p6 = st.columns(2)
        p5.metric("Peak power per active cell", f"{pulse_peak_power_kw_per_cell:.1f} kW")
        p6.metric("Active plasma cells", f"{active_cells}")

        st.markdown(
            f"""
            <div class="horg-note">
            <b>Pulse-power equation:</b>
            P<sub>avg</sub> = E<sub>pulse</sub> × f × N<sub>cells</sub>.<br><br>
            {pulse_energy_mj:.1f} mJ/pulse ×
            {pulse_frequency_khz:.1f} kHz ×
            {active_cells} cells =
            <b>{derived_pulse_power_kw:.2f} kW average electrical power</b>.<br>
            At the current modeled H₂ production this corresponds to
            <b>{effective_plasma_sei:.2f} kWh/kg H₂</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="horg-note">
            <b>Frequency sensitivity:</b><br>
            With pulse energy fixed at <b>{pulse_energy_mj:.1f} mJ</b> and
            <b>{active_cells}</b> active cells, every +1 kHz increases average
            plasma electrical power by approximately
            <b>{pulse_energy_mj * active_cells / 1000.0:.3f} kW</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if thermo_adequacy_ratio < 1.0:
            st.error(
                f"Even at the ideal thermodynamic floor, these pulse settings could "
                f"support at most about {max_h2_at_thermo_floor_kg_h:.2f} kg H₂/h, "
                f"while the model currently assumes {h2_gross_kg_h:.2f} kg H₂/h gross production."
            )
    else:
        st.markdown(
            f"""
            <div class="horg-note">
            Continuous reference mode uses
            <b>{effective_plasma_sei:.2f} kWh/kg H₂</b>.
            Select <b>Pulsed plasma</b> in the sidebar to calculate average power
            from pulse energy, frequency and active cell count.
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.05, 0.95])
    with left:
        st.subheader("Mass balance")
        st.dataframe(
            {
                "Stream": [
                    "Fuel to plasma reactor",
                    "Gross H₂ produced",
                    "H₂ delivered to engine",
                    "Solid carbon generated",
                    "Solid carbon captured",
                    "Uncaptured solid-carbon fraction",
                ],
                "kg/h": [
                    fuel_kg_h,
                    h2_gross_kg_h,
                    h2_to_engine_kg_h,
                    carbon_generated_kg_h,
                    carbon_captured_kg_h,
                    carbon_uncaptured_kg_h,
                ],
            },
            width="stretch",
            hide_index=True,
        )
        st.markdown(
            f"""
            <div class="horg-note">
            <b>Ideal stoichiometry per 1 kg n-octane:</b><br>
            H₂ = {H2_KG_PER_KG_FUEL_IDEAL:.3f} kg · C(s) = {C_KG_PER_KG_FUEL_IDEAL:.3f} kg.<br><br>
            With {reactor_conversion*100:.0f}% overall conversion and {h2_recovery*100:.0f}% H₂ recovery,
            the effective scenario yield is {effective_h2_yield:.3f} kg H₂/kg fuel.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.subheader("Energy balance")
        st.dataframe(
            {
                "Quantity": [
                    "Fuel chemical input (reference LHV)",
                    "H₂ chemical energy to engine",
                    "Gross H₂-engine shaft output",
                    "Gross plasma electricity",
                    "Recovered-energy offset",
                    "External plasma electricity",
                    "Equivalent shaft draw for plasma",
                    "Net shaft after plasma burden",
                ],
                "kW": [
                    fuel_chemical_kw,
                    h2_chemical_kw,
                    gross_engine_kw,
                    plasma_gross_kw,
                    plasma_gross_kw * recovery_offset,
                    plasma_external_kw,
                    shaft_draw_for_plasma_kw,
                    net_shaft_kw,
                ],
            },
            width="stretch",
            hide_index=True,
        )
        st.markdown(
            f"""
            <div class="horg-note">
            <b>Thermodynamic floor:</b> ideal standard-state n-octane decomposition requires about
            <b>{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂</b> before real reactor, heat-transfer,
            separation and auxiliary losses.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Required Plasma Efficiency to Reach Target Power")
    st.caption(
        "Works backwards from desired net shaft power to the maximum plasma burden "
        "the system can tolerate under the selected recovery and generator assumptions."
    )

    # Show up to three requested engineering target cards.
    target_cols = st.columns(min(3, max(1, len(target_levels_kw))))
    for idx, target_kw in enumerate(target_levels_kw[:3]):
        allowed_kw = max_plasma_gross_power_for_target(target_kw)
        allowed_sei = max_plasma_sei_for_target(target_kw)
        delta_txt = (
            "above thermodynamic floor"
            if allowed_sei >= THERMO_MIN_KWH_PER_KG_H2
            else "below thermodynamic floor"
        )
        target_cols[idx].metric(
            f"Target {target_kw:.0f} kW net",
            f"{allowed_sei:.2f} kWh/kg H₂",
            delta_txt,
        )

    target_table = []
    for target_kw in target_levels_kw:
        allowed_kw = max_plasma_gross_power_for_target(target_kw)
        allowed_sei = max_plasma_sei_for_target(target_kw)
        reduction_needed = (
            max(0.0, 1.0 - allowed_sei / effective_plasma_sei) * 100.0
            if effective_plasma_sei > 0 and math.isfinite(allowed_sei)
            else 0.0
        )
        target_table.append({
            "Target net shaft": f"{target_kw:.0f} kW",
            "Max gross plasma power": f"{allowed_kw:.2f} kW",
            "Max plasma SEI": f"{allowed_sei:.2f} kWh/kg H₂",
            "SEI reduction vs current": f"{reduction_needed:.1f}%",
            "Thermodynamic check": (
                "Potentially compatible"
                if allowed_sei >= THERMO_MIN_KWH_PER_KG_H2
                else "Below thermodynamic floor"
            ),
        })

    st.dataframe(target_table, width="stretch", hide_index=True)

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Best-case thermodynamic ceiling for the current operating point:</b><br>
        At the ideal standard-state decomposition floor of
        <b>{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂</b>,
        the plasma would consume about <b>{plasma_floor_kw:.2f} kW</b> gross electricity.
        With the selected recovered-energy offset and generator efficiency,
        a {gross_engine_kw:.0f} kW gross H₂ engine would then leave about
        <b>{max_net_at_thermo_floor_kw:.1f} kW net shaft power</b>.
        This is an ideal thermodynamic ceiling, not a realistic reactor prediction.
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_target = int(min(80.0, float(gross_engine_kw)))
    target_net_kw = st.slider(
        "Custom target net shaft power (kW)",
        min_value=0,
        max_value=int(gross_engine_kw),
        value=default_target,
        step=5,
    )

    custom_allowed_plasma_kw = max_plasma_gross_power_for_target(target_net_kw)
    custom_allowed_sei = max_plasma_sei_for_target(target_net_kw)
    custom_reduction_pct = (
        max(0.0, 1.0 - custom_allowed_sei / effective_plasma_sei) * 100.0
        if effective_plasma_sei > 0 and math.isfinite(custom_allowed_sei)
        else 0.0
    )

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Allowed gross plasma power", f"{custom_allowed_plasma_kw:.2f} kW")
    q2.metric("Required max plasma SEI", f"{custom_allowed_sei:.2f} kWh/kg H₂")
    q3.metric("SEI reduction vs current", f"{custom_reduction_pct:.1f}%")
    q4.metric("Ideal thermodynamic floor", f"{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂")

    if custom_allowed_sei >= THERMO_MIN_KWH_PER_KG_H2:
        target_margin = custom_allowed_sei / THERMO_MIN_KWH_PER_KG_H2
        st.success(
            f"The {target_net_kw:.0f} kW net target is not excluded by the model's "
            f"standard-state thermodynamic floor. Plasma electricity would need to be "
            f"no more than {custom_allowed_sei:.2f} kWh/kg H₂ gross, giving a "
            f"{target_margin:.2f}× margin over the ideal floor."
        )
    else:
        st.error(
            f"The {target_net_kw:.0f} kW net target would require only "
            f"{custom_allowed_sei:.2f} kWh/kg H₂, below the ideal standard-state "
            f"floor of {THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂. With the current "
            f"gross engine power and selected recovery assumptions, this target is "
            f"not reachable in the simplified model."
        )

    if plasma_mode == "Pulsed plasma":
        per_cell_avg_kw = (
            pulse_energy_mj * 1e-3
            * pulse_frequency_khz * 1e3
            / 1000.0
        )
        max_cells_for_target = (
            math.floor(custom_allowed_plasma_kw / per_cell_avg_kw)
            if per_cell_avg_kw > 0 and math.isfinite(custom_allowed_plasma_kw)
            else 0
        )
        required_pulse_energy_mj_at_current_cells = (
            custom_allowed_plasma_kw * 1000.0
            / (pulse_frequency_khz * 1e3 * active_cells)
            * 1000.0
            if pulse_frequency_khz > 0 and active_cells > 0
            else math.inf
        )
        st.markdown(
            f"""
            <div class="horg-note">
            <b>Pulsed-plasma translation for the selected target:</b><br>
            At the current pulse energy and frequency, one active cell averages
            <b>{per_cell_avg_kw:.4f} kW</b> electrical power.
            To remain below the {target_net_kw:.0f} kW net-power ceiling, the purely
            electrical model allows approximately <b>{max_cells_for_target} active cells</b>.<br><br>
            Alternatively, keeping {active_cells} cells and {pulse_frequency_khz:.1f} kHz,
            the average pulse energy would need to be no more than about
            <b>{required_pulse_energy_mj_at_current_cells:.2f} mJ per pulse per cell</b>.<br><br>
            These are electrical ceilings only. They do not establish reactor throughput,
            conversion, hydrogen yield or carbon-removal performance.
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ============================================================
    # WHAT MUST CHANGE TO REACH THE SELECTED TARGET?
    # ============================================================

    st.subheader("What must change to reach the selected target?")

    st.caption(
        "Design diagnosis: each lever is varied one at a time while the other current "
        "assumptions are held fixed. These are model requirements, not validated hardware predictions."
    )

    def net_fraction_for_specific_plasma_energy(
        sei_kwh_per_kg_h2,
        engine_efficiency,
        recovery_fraction,
    ):
        """
        Fraction of gross H2-engine shaft power left after the modeled plasma
        electrical burden, assuming plasma specific electricity scales with H2 flow.
        """
        if (
            engine_efficiency <= 0
            or h2_recovery <= 0
            or generator_eff <= 0
        ):
            return -math.inf

        plasma_burden_fraction = (
            sei_kwh_per_kg_h2
            * (1.0 - recovery_fraction)
            / (
                generator_eff
                * engine_efficiency
                * H2_LHV_KWH_KG
                * h2_recovery
            )
        )
        return 1.0 - plasma_burden_fraction


    # 1) Gross engine power required if current plasma specific electricity is kept.
    current_specific_net_fraction = net_fraction_for_specific_plasma_energy(
        effective_plasma_sei,
        engine_eff,
        recovery_offset,
    )

    required_gross_engine_current_sei_kw = (
        target_net_kw / current_specific_net_fraction
        if target_net_kw > 0 and current_specific_net_fraction > 0
        else (0.0 if target_net_kw == 0 else math.inf)
    )

    # 2) Gross engine power required in the ideal thermodynamic-floor case.
    floor_specific_net_fraction = net_fraction_for_specific_plasma_energy(
        THERMO_MIN_KWH_PER_KG_H2,
        engine_eff,
        recovery_offset,
    )

    required_gross_engine_floor_kw = (
        target_net_kw / floor_specific_net_fraction
        if target_net_kw > 0 and floor_specific_net_fraction > 0
        else (0.0 if target_net_kw == 0 else math.inf)
    )

    # 3) H2 engine efficiency required at current gross engine power and current plasma SEI.
    if target_net_kw < gross_engine_kw:
        required_engine_eff = (
            gross_engine_kw
            * effective_plasma_sei
            * (1.0 - recovery_offset)
            / (
                (gross_engine_kw - target_net_kw)
                * H2_LHV_KWH_KG
                * h2_recovery
                * generator_eff
            )
        )
    elif (
        target_net_kw == gross_engine_kw
        and effective_plasma_sei == 0
    ):
        required_engine_eff = engine_eff
    else:
        required_engine_eff = math.inf

    # Same calculation if the plasma could reach the ideal thermodynamic floor.
    if target_net_kw < gross_engine_kw:
        required_engine_eff_at_floor = (
            gross_engine_kw
            * THERMO_MIN_KWH_PER_KG_H2
            * (1.0 - recovery_offset)
            / (
                (gross_engine_kw - target_net_kw)
                * H2_LHV_KWH_KG
                * h2_recovery
                * generator_eff
            )
        )
    else:
        required_engine_eff_at_floor = math.inf

    # 4) Recovered-energy offset required at current gross engine power and current plasma SEI.
    current_plasma_power_at_specific_sei_kw = (
        gross_engine_kw
        * effective_plasma_sei
        / (
            engine_eff
            * H2_LHV_KWH_KG
            * h2_recovery
        )
        if engine_eff > 0 and h2_recovery > 0
        else math.inf
    )

    if target_net_kw <= gross_engine_kw and current_plasma_power_at_specific_sei_kw > 0:
        required_recovery_offset = (
            1.0
            - (
                (gross_engine_kw - target_net_kw)
                * generator_eff
                / current_plasma_power_at_specific_sei_kw
            )
        )
        required_recovery_offset = max(0.0, required_recovery_offset)
    else:
        required_recovery_offset = math.inf

    # Same recovered-energy calculation at the thermodynamic-floor plasma input.
    floor_plasma_power_at_current_gross_kw = (
        gross_engine_kw
        * THERMO_MIN_KWH_PER_KG_H2
        / (
            engine_eff
            * H2_LHV_KWH_KG
            * h2_recovery
        )
        if engine_eff > 0 and h2_recovery > 0
        else math.inf
    )

    if target_net_kw <= gross_engine_kw and floor_plasma_power_at_current_gross_kw > 0:
        required_recovery_offset_at_floor = (
            1.0
            - (
                (gross_engine_kw - target_net_kw)
                * generator_eff
                / floor_plasma_power_at_current_gross_kw
            )
        )
        required_recovery_offset_at_floor = max(
            0.0,
            required_recovery_offset_at_floor,
        )
    else:
        required_recovery_offset_at_floor = math.inf


    def fmt_requirement(value, unit="", digits=1):
        if not math.isfinite(value):
            return "Not finite"
        return f"{value:.{digits}f}{unit}"


    d1, d2, d3, d4 = st.columns(4)

    d1.metric(
        "Gross H₂ engine needed @ current SEI",
        (
            f"{required_gross_engine_current_sei_kw:.1f} kW"
            if math.isfinite(required_gross_engine_current_sei_kw)
            else "Not reachable"
        ),
    )

    d2.metric(
        "Gross H₂ engine needed @ thermo floor",
        (
            f"{required_gross_engine_floor_kw:.1f} kW"
            if math.isfinite(required_gross_engine_floor_kw)
            else "Not reachable"
        ),
    )

    d3.metric(
        "H₂ engine efficiency needed @ current SEI",
        (
            f"{100*required_engine_eff:.1f}%"
            if math.isfinite(required_engine_eff)
            else "Not reachable"
        ),
    )

    d4.metric(
        "Recovered-energy offset needed @ current SEI",
        (
            f"{100*required_recovery_offset:.1f}%"
            if math.isfinite(required_recovery_offset)
            else "Not reachable"
        ),
    )

    diagnosis_rows = []

    # Plasma-SEI lever
    if custom_allowed_sei < THERMO_MIN_KWH_PER_KG_H2:
        sei_status = "Not physically reachable by SEI reduction alone"
    else:
        sei_status = "Not excluded by thermodynamic floor"

    diagnosis_rows.append(
        {
            "Design lever": "Plasma specific electricity",
            "Current": f"{effective_plasma_sei:.2f} kWh/kg H₂",
            "Required for target": f"≤ {custom_allowed_sei:.2f} kWh/kg H₂",
            "Model diagnosis": sei_status,
        }
    )

    # Gross-engine lever, using current SEI
    if not math.isfinite(required_gross_engine_current_sei_kw):
        gross_status = "Not reachable at current specific plasma burden"
    elif required_gross_engine_current_sei_kw <= 250:
        gross_status = "Within current simulator power range; throughput must scale too"
    else:
        gross_status = "Above current simulator power range"

    diagnosis_rows.append(
        {
            "Design lever": "Gross H₂-engine shaft power",
            "Current": f"{gross_engine_kw:.0f} kW",
            "Required for target": (
                f"≥ {required_gross_engine_current_sei_kw:.1f} kW"
                if math.isfinite(required_gross_engine_current_sei_kw)
                else "Not finite"
            ),
            "Model diagnosis": gross_status,
        }
    )

    # Engine-efficiency lever
    if not math.isfinite(required_engine_eff):
        engine_eff_status = "Not reachable at current gross power"
    elif required_engine_eff > 1.0:
        engine_eff_status = "Physically impossible (>100%)"
    elif required_engine_eff > 0.50:
        engine_eff_status = "Above current simulator efficiency range"
    else:
        engine_eff_status = "Within current simulator efficiency range"

    diagnosis_rows.append(
        {
            "Design lever": "H₂ engine brake efficiency",
            "Current": f"{100*engine_eff:.1f}%",
            "Required for target": (
                f"≥ {100*required_engine_eff:.1f}%"
                if math.isfinite(required_engine_eff)
                else "Not finite"
            ),
            "Model diagnosis": engine_eff_status,
        }
    )

    # Recovery-offset lever
    if not math.isfinite(required_recovery_offset):
        recovery_status = "Not reachable"
    elif required_recovery_offset > 1.0:
        recovery_status = "Physically impossible (>100%)"
    elif required_recovery_offset > 0.80:
        recovery_status = "Above current simulator recovery range"
    else:
        recovery_status = "Within model range; requires experimental validation"

    diagnosis_rows.append(
        {
            "Design lever": "Recovered-energy offset",
            "Current": f"{100*recovery_offset:.1f}%",
            "Required for target": (
                f"≥ {100*required_recovery_offset:.1f}%"
                if math.isfinite(required_recovery_offset)
                else "Not finite"
            ),
            "Model diagnosis": recovery_status,
        }
    )

    st.dataframe(
        diagnosis_rows,
        width="stretch",
        hide_index=True,
    )

    # A concise engineering interpretation.
    if custom_allowed_sei < THERMO_MIN_KWH_PER_KG_H2:
        st.warning(
            f"Plasma efficiency alone cannot deliver {target_net_kw:.0f} kW net at "
            f"{gross_engine_kw:.0f} kW gross: the required "
            f"{custom_allowed_sei:.2f} kWh/kg H₂ is below the ideal floor of "
            f"{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂."
        )
    else:
        st.success(
            f"At {gross_engine_kw:.0f} kW gross, the {target_net_kw:.0f} kW target "
            f"is not excluded by the thermodynamic floor if plasma electricity can "
            f"be reduced to ≤ {custom_allowed_sei:.2f} kWh/kg H₂."
        )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Alternative paths for the selected {target_net_kw:.0f} kW target:</b><br><br>

        • Keeping the current plasma specific electricity of
        <b>{effective_plasma_sei:.2f} kWh/kg H₂</b>, the simplified model requires
        approximately <b>{fmt_requirement(required_gross_engine_current_sei_kw, " kW", 1)}</b>
        gross H₂-engine shaft power.<br>

        • If the plasma could approach the ideal thermodynamic floor, the required
        gross H₂-engine power falls to approximately
        <b>{fmt_requirement(required_gross_engine_floor_kw, " kW", 1)}</b>.<br>

        • Holding gross engine power and plasma SEI fixed, the required H₂-engine
        brake efficiency is
        <b>{fmt_requirement(100*required_engine_eff, "%", 1)}</b>.<br>

        • Holding gross engine power, engine efficiency and plasma SEI fixed, the
        required recovered-energy offset is
        <b>{fmt_requirement(100*required_recovery_offset, "%", 1)}</b>.<br><br>

        Each line varies one lever independently. Combining moderate improvements
        across several levers can be more realistic than forcing any single
        parameter to an extreme value.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Ideal-floor cross-check for the selected target"):
        gross_floor_display = (
            f"{required_gross_engine_floor_kw:.1f} kW"
            if math.isfinite(required_gross_engine_floor_kw)
            else "Not finite"
        )

        engine_eff_floor_display = (
            f"{100 * required_engine_eff_at_floor:.1f}%"
            if math.isfinite(required_engine_eff_at_floor)
            else "Not finite"
        )

        recovery_floor_display = (
            f"{100 * required_recovery_offset_at_floor:.1f}%"
            if math.isfinite(required_recovery_offset_at_floor)
            else "Not finite"
        )

        st.markdown(
            f"""
            If the plasma specific electricity were exactly the ideal
            **{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂** floor:

            - gross H₂-engine power needed: **{gross_floor_display}**
            - H₂-engine efficiency needed at the current gross power:
              **{engine_eff_floor_display}**
            - recovered-energy offset needed at the current gross power:
              **{recovery_floor_display}**

            These are idealized model boundaries, not predictions of achievable
            reactor, engine or heat-recovery hardware.
            """
        )


    st.subheader("Hypothesis 3 — Gasoline + Water / Steam-Assisted Comparison")

    st.caption(
        "Water and gasoline are modeled as separate feeds mixed after vaporization. "
        "The water does not remain a liquid blend in the gasoline tank."
    )

    s1, s2, s3, s4 = st.columns(4)

    s1.metric(
        "Steam-route gasoline",
        f"{steam_fuel_l_h:.1f} L/h",
        f"{steam_fuel_kg_h:.1f} kg/h",
    )

    s2.metric(
        "Make-up water",
        f"{steam_water_makeup_l_h:.1f} L/h",
    )

    s3.metric(
        "H₂ to engine",
        f"{steam_h2_to_engine_kg_h:.2f} kg/h",
    )

    s4.metric(
        "Steam-route net shaft",
        f"{steam_net_shaft_kw:.1f} kW",
    )

    s5, s6, s7, s8 = st.columns(4)

    s5.metric(
        "Ideal H₂ yield from fuel",
        f"{steam_h2_yield_kg_per_kg_fuel:.3f} kg/kg",
    )

    s6.metric(
        "Thermal process demand",
        f"{steam_thermal_energy:.1f} kWh_th/kg H₂",
    )

    s7.metric(
        "Reaction-enthalpy reference",
        f"{steam_reaction_floor_kwh_per_kg_h2:.2f} kWh/kg H₂",
    )

    if steam_route == "Steam reforming + WGS":
        s8.metric(
            "CO₂ produced in route",
            f"{steam_co2_kg_h:.1f} kg/h",
        )
    else:
        s8.metric(
            "CO produced in syngas",
            f"{steam_co_kg_h:.1f} kg/h",
        )

    se1, se2, se3 = st.columns(3)
    se1.metric("Electrical auxiliaries", f"{steam_electrical_aux:.2f} kWh_e/kg H₂")
    se2.metric("External thermal demand", f"{steam_thermal_external_kw:.1f} kW_th")
    se3.metric("Electrical auxiliary demand", f"{steam_electrical_aux_kw:.1f} kW_e")

    st.dataframe(
        {
            "Metric": [
                "Gross H₂-engine shaft",
                "Net shaft after process burden",
                "Gasoline flow",
                "Make-up water",
                "H₂ to engine",
                "Fuel-to-net-shaft efficiency",
                "Carbon pathway",
            ],
            "Conventional gasoline ICE": [
                f"{gross_engine_kw:.1f} kW",
                f"{gross_engine_kw:.1f} kW",
                f"{conv_same_gross_fuel_l_h:.2f} L/h",
                "0 L/h",
                "0 kg/h",
                f"{100*conventional_eff:.1f}%",
                f"{conv_same_gross_co2_kg_h:.2f} kg/h CO₂",
            ],
            "Dry HPRS carbon-retention": [
                f"{gross_engine_kw:.1f} kW",
                f"{net_shaft_kw:.1f} kW",
                f"{fuel_l_h:.2f} L/h",
                "0 L/h",
                f"{h2_to_engine_kg_h:.2f} kg/h",
                f"{100*hprs_net_eff:.1f}%",
                f"{carbon_captured_kg_h:.2f} kg/h solid C captured",
            ],
            "Gasoline + steam route": [
                f"{gross_engine_kw:.1f} kW",
                f"{steam_net_shaft_kw:.1f} kW",
                f"{steam_fuel_l_h:.2f} L/h",
                f"{steam_water_makeup_l_h:.2f} L/h",
                f"{steam_h2_to_engine_kg_h:.2f} kg/h",
                f"{100*steam_net_eff:.1f}%",
                (
                    f"{steam_co2_kg_h:.2f} kg/h CO₂"
                    if steam_route == "Steam reforming + WGS"
                    else f"{steam_co_kg_h:.2f} kg/h CO in syngas"
                ),
            ],
        },
        width="stretch",
        hide_index=True,
    )


st.markdown('<span id="horg-rf" class="horg-section-anchor"></span>', unsafe_allow_html=True)
st.subheader("Hypothesis 4 — HPRS-W Plasma Water Splitting")

st.caption(
    "HTPR-QS-inspired architecture from the supplied diagram: superheated steam, argon-assisted "
    "RF/plasma dissociation, electric-field species steering, rapid quench, H₂/O₂ separation, "
    "heat recovery, catalyst-assisted research scenarios and argon/steam recirculation. Values below are scenario assumptions, not validated reactor data."
)

w1, w2, w3, w4 = st.columns(4)
w1.metric("Effective plasma-system electricity", f"{hprsw_plasma_electricity:.1f} kWh_e/kg H₂")
w2.metric("H₂ recovery chain", f"{100*hprsw_recovery_chain:.1f}%")
w3.metric("Stoichiometric water", f"{WATER_KG_PER_KG_H2_STOICH:.2f} kg/kg H₂")
w4.metric("O₂ coproduct (ideal)", f"{O2_KG_PER_KG_H2_STOICH:.2f} kg/kg H₂")

w5, w6, w7, w8 = st.columns(4)
w5.metric("External steam heat", f"{hprsw_steam_preheat*(1-hprsw_heat_recovery):.1f} kWh_th/kg H₂ gross")
w6.metric("DOE PEM 2026 system target", f"{DOE_PEM_2026_SYSTEM_KWH_KG_H2:.0f} kWh_e/kg H₂")
w7.metric("DOE HTE 2026 electrical target", f"{DOE_HTE_2026_ELECTRIC_KWH_KG_H2:.0f} kWh_e/kg H₂")
w8.metric("DOE HTE 2026 total-energy target", f"{DOE_HTE_2026_TOTAL_KWH_KG_H2:.0f} kWh/kg H₂")

st.markdown("#### V3.3 · Experimental efficiency levers")
v331, v332, v333, v334 = st.columns(4)
v331.metric("Baseline plasma electricity", f"{hprsw_plasma_electricity_base:.1f} kWh/kg")
v332.metric("V3.3 effective electricity", f"{hprsw_plasma_electricity:.1f} kWh/kg")
v333.metric("Effective heat recovery", f"{100*hprsw_heat_recovery:.1f}%")
v334.metric("Ar recovery", f"{100*hprsw_argon_recovery:.1f}%")

v335, v336, v337, v338 = st.columns(4)
v335.metric("RF carrier", f"{hprsw_rf_carrier_mhz:.2f} MHz")
v336.metric("Pulse-envelope duty", f"{100*hprsw_rf_duty:.1f}%")
v337.metric("Avg. absorbed RF power", f"{hprsw_rf_absorbed_kw:.1f} kW")
v338.metric("Estimated delivered H₂ capacity", f"{hprsw_rf_delivered_h2_capacity_kg_h:.2f} kg/h")

st.markdown(
    f"""
    <div class="horg-note">
    <b>Catalyst scenario:</b> {hprsw_catalyst_family}. The catalyst credit is applied only to the modeled
    electrical overhead above ΔG; ΔG and ΔH are unchanged. <b>Pulse frequency is not an efficiency multiplier:</b>
    {hprsw_pulse_rep_khz:.1f} kHz with {hprsw_pulse_width_us:.1f} µs bursts gives a {100*hprsw_rf_duty:.1f}% duty cycle.
    Any energy-efficiency benefit from pulsing enters only through the explicit measured/assumed overhead-reduction input.
    The Ar-loop parasitic term is {hprsw_argon_recycle_electricity_per_gross_h2:.3f} kWh/kg gross H₂ and the additional
    heat-to-electric credit is {hprsw_additional_electric_recovery_credit:.2f} kWh/kg gross H₂.
    </div>
    """,
    unsafe_allow_html=True,
)

_v33_freqs = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
_v33_rows = []
for _f_khz in _v33_freqs:
    _duty = max(0.0, min(1.0, _f_khz * 1e3 * hprsw_pulse_width_us * 1e-6))
    _avg_forward = hprsw_rf_forward_peak_kw * _duty
    _absorbed = _avg_forward * hprsw_rf_coupling_eff
    _gross_capacity = _absorbed / max(hprsw_plasma_after_pulsing, 1e-12)
    _delivered_capacity = _gross_capacity * hprsw_recovery_chain
    _v33_rows.append({
        "Pulse envelope (kHz)": _f_khz,
        "Duty cycle (%)": 100.0 * _duty,
        "Average forward RF (kW)": _avg_forward,
        "Absorbed RF (kW)": _absorbed,
        "Gross H2 capacity (kg/h)": _gross_capacity,
        "Delivered H2 capacity (kg/h)": _delivered_capacity,
    })

st.markdown("##### RF pulse frequency · H₂ output capacity")
st.line_chart(pd.DataFrame(_v33_rows).set_index("Pulse envelope (kHz)")[["Delivered H2 capacity (kg/h)"]], height=330)
st.caption("Capacity scaling only: constant pulse width, peak RF power, coupling and specific energy; not an efficiency gain.")

with st.expander("V3.3 pulse-frequency capacity sweep", expanded=False):
    st.caption(
        "This sweep holds burst width, peak forward RF power, coupling efficiency and specific energy constant. "
        "It therefore shows capacity/power scaling with pulse repetition frequency — not an assumed frequency-driven efficiency gain."
    )
    st.dataframe(
        pd.DataFrame(_v33_rows).style.format({
            "Pulse envelope (kHz)": "{:.1f}",
            "Duty cycle (%)": "{:.1f}",
            "Average forward RF (kW)": "{:.1f}",
            "Absorbed RF (kW)": "{:.1f}",
            "Gross H2 capacity (kg/h)": "{:.3f}",
            "Delivered H2 capacity (kg/h)": "{:.3f}",
        }),
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        "**Research interpretation:** scan carrier frequency, pulse-envelope frequency, burst width, catalyst packing, "
        "argon recycle and thermal recovery experimentally; then replace the zero-default benefit coefficients with measured values. "
        "That turns V3.3 from a sensitivity model into a calibration framework."
    )

if hprsw_closed_loop_margin_kwh_per_kg < 0:
    st.error(
        f"Closed-loop diagnostic: each kg of H₂ delivered to the engine produces about "
        f"{hprsw_shaft_per_kg_delivered_h2:.1f} kWh shaft at the selected engine efficiency, "
        f"but powering HPRS-W from an engine-driven generator would require about "
        f"{hprsw_equiv_shaft_burden_per_kg_delivered_h2:.1f} kWh shaft-equivalent per kg delivered H₂. "
        f"Margin = {hprsw_closed_loop_margin_kwh_per_kg:.1f} kWh/kg. The self-powered loop does not close."
    )
else:
    st.warning(
        "The simplified closed-loop arithmetic is non-negative, but this would still require full transient, "
        "thermal, separation, safety and durability validation before any self-sustaining claim."
    )

st.markdown(
    f"""
    <div class="horg-note">
    <b>Water accounting:</b> 2 H₂O → 2 H₂ + O₂ consumes at least
    <b>{WATER_KG_PER_KG_H2_STOICH:.2f} kg H₂O/kg gross H₂</b>.
    Steam recirculation only reduces the make-up associated with excess circulating steam;
    it cannot eliminate the stoichiometric water consumed in the reaction.<br><br>
    <b>Electric-field boundary:</b> the model treats ion/species separation efficiency as an
    experimental parameter. A DC field can steer charged species; it does not directly separate
    neutral H₂ and O₂ after recombination.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")
st.markdown('<span id="horg-advanced" class="horg-section-anchor"></span>', unsafe_allow_html=True)
with st.expander("HPRS-W advanced theory, feasible-region and Pareto analysis", expanded=False):
    st.subheader("V3.3 Advanced Theoretical Analysis — HPRS-W")
    st.caption(
        "These diagnostics are first-order theoretical calculations. They do not solve plasma kinetics, "
        "non-equilibrium chemistry, sheath physics, detailed CFD or electrode erosion."
    )

    st.markdown("#### 1 · Standard-state thermodynamic limits")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Reversible minimum ΔG", f"{WATER_SPLIT_REV_KWH_PER_KG_H2:.2f} kWh/kg H₂")
    t2.metric("Thermoneutral ΔH", f"{WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2:.2f} kWh/kg H₂")
    t3.metric("Reversible voltage", f"{WATER_SPLIT_REV_VOLTAGE_V:.3f} V")
    t4.metric("Thermoneutral voltage", f"{WATER_SPLIT_THERMONEUTRAL_VOLTAGE_V:.3f} V")

    t5, t6, t7, t8 = st.columns(4)
    t5.metric(
        "Actual external energy / delivered H₂",
        f"{hprsw_total_external_energy_per_delivered_h2:.1f} kWh/kg",
    )
    t6.metric(
        "External exergy / delivered H₂",
        f"{hprsw_external_exergy_per_delivered_h2:.1f} kWhₑₓ/kg",
    )
    t7.metric("Second-law efficiency proxy", f"{100*hprsw_second_law_eff:.1f}%")
    t8.metric("HHV energy-efficiency proxy", f"{100*hprsw_hhv_energy_eff:.1f}%")

    if hprsw_standard_energy_margin_gross < 0:
        st.error(
            f"Thermodynamic closure warning: the modeled external electricity + unrecovered heat "
            f"is {abs(hprsw_standard_energy_margin_gross):.2f} kWh/kg gross H₂ below the 298 K "
            f"standard-state ΔH reference. The scenario therefore requires an unmodeled energy source "
            f"or a different thermodynamic boundary."
        )
    elif hprsw_standard_exergy_margin_gross < 0:
        st.error(
            f"Exergy closure warning: the modeled external exergy is "
            f"{abs(hprsw_standard_exergy_margin_gross):.2f} kWh/kg gross H₂ below the standard-state ΔG reference."
        )
    else:
        st.success(
            f"Standard-state closure check is non-negative: energy margin "
            f"{hprsw_standard_energy_margin_gross:+.2f} kWh/kg gross H₂ and simple exergy margin "
            f"{hprsw_standard_exergy_margin_gross:+.2f} kWh/kg gross H₂."
        )

    st.markdown("#### 2 · Electric-field and reduced-field diagnostic")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Electric field E", f"{hprsw_field_v_cm:.1f} V/cm")
    e2.metric("Gas number density N", f"{hprsw_number_density_m3:.2e} m⁻³")
    e3.metric("Reduced field E/N", f"{hprsw_reduced_field_td:.2f} Td")
    e4.metric("Ion drift velocity", f"{hprsw_ion_drift_velocity_m_s:.2f} m/s")

    st.markdown(
        f"""
        <div class="horg-note">
        <b>E/N interpretation:</b> E/N is calculated from the user-selected bulk field,
        ideal-gas number density and separation-zone state. Local sheath fields, non-uniform
        plasma fields, electron-energy distributions and species-specific transport are not solved.
        The current input corresponds to <b>{hprsw_field_voltage_v:.0f} V</b> across
        <b>{hprsw_electrode_gap_mm:.1f} mm</b> at <b>{hprsw_pressure_bar:.2f} bar</b> and
        <b>{hprsw_separation_temp_c:.0f} °C</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 3 · Ion-separation and quench timescales")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric(
        "Ion separation time",
        f"{1000*hprsw_ion_separation_time_s:.2f} ms" if math.isfinite(hprsw_ion_separation_time_s) else "∞",
    )
    q2.metric("Residence / separation", f"{hprsw_separation_timescale_index:.2f}×")
    q3.metric("Quench cooling rate", f"{hprsw_quench_cooling_rate_k_s:.2e} K/s")
    q4.metric("Timescale H₂ survival", f"{100*hprsw_quench_survival_timescale:.1f}%")

    if hprsw_separation_timescale_index < 1.0:
        st.warning(
            f"Ion-steering diagnostic: with the selected effective mobility, the charged-species residence "
            f"time is shorter than the estimated drift time across {hprsw_separation_distance_mm:.1f} mm. "
            f"The simple separation index is {hprsw_separation_timescale_index:.2f}×."
        )
    else:
        st.success(
            f"Ion-steering timescale is favorable in the simple drift model: the residence time is "
            f"{hprsw_separation_timescale_index:.2f}× the calculated separation time. This is not a purity prediction."
        )

    st.caption(
        f"Quench model used in the mass balance: {hprsw_quench_loss_model}. "
        f"Effective H₂ quench/recombination loss = {100*hprsw_quench_loss_effective:.2f}%. "
        f"The first-order diagnostic uses τ_recomb = {hprsw_recomb_tau_ms:.1f} ms and "
        f"t_quench = {hprsw_quench_time_ms:.2f} ms."
    )

    st.markdown("#### 4 · First-order reactor sizing at the normalized power point")
    r1a, r2a, r3a, r4a = st.columns(4)
    r1a.metric("Estimated active gas volume", f"{hprsw_active_volume_l:.2f} L")
    r2a.metric("Equivalent core diameter", f"{1000*hprsw_core_diameter_m:.0f} mm")
    r3a.metric("Equivalent core length", f"{1000*hprsw_core_length_m:.0f} mm")
    r4a.metric("Core power-density proxy", f"{hprsw_power_density_kw_l:.2f} kW/L")

    r5a, r6a, r7a, r8a = st.columns(4)
    r5a.metric("Steam circulation", f"{norm_hprsw_water_circulation_kg_h:.1f} kg/h")
    r6a.metric("Argon circulation", f"{hprsw_norm_argon_circulation_kg_h:.2f} kg/h")
    r7a.metric("Sensible quench duty", f"{hprsw_quench_sensible_duty_kw:.1f} kW")
    r8a.metric("Coolant flow proxy", f"{hprsw_coolant_flow_l_min:.1f} L/min")

    st.markdown(
        """
        <div class="horg-note">
        <b>Sizing boundary:</b> active volume is inferred from ideal-gas volumetric flow × selected residence time.
        The equivalent diameter/length assumes a simple cylindrical core. The quench duty uses a lumped constant Cp;
        dissociation energy, radiative transfer, wall heat flux, electrode cooling and two-phase quench behavior are not solved.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 5 · Automatic HPRS-W break-even solver vs conventional gasoline")

    be1, be2, be3, be4 = st.columns(4)
    be1.metric(
        "Max plasma electricity for energy parity",
        f"{hprsw_max_plasma_kwhkg_energy_parity:.1f} kWh/kg H₂"
        if hprsw_max_plasma_kwhkg_energy_parity >= 0 else "Impossible at current heat load",
    )
    be2.metric(
        "Required total H₂ recovery chain",
        f"{100*hprsw_required_recovery_chain_energy_parity:.1f}%",
    )
    be3.metric(
        "Required H₂-engine efficiency",
        f"{100*hprsw_required_engine_eff_energy_parity:.1f}%",
    )

    if hprsw_required_heat_recovery_energy_parity <= 0:
        heat_req_text = "0%"
    elif hprsw_required_heat_recovery_energy_parity <= 1:
        heat_req_text = f"{100*hprsw_required_heat_recovery_energy_parity:.1f}%"
    else:
        heat_req_text = ">100% (impossible)"
    be4.metric("Required heat recovery", heat_req_text)

    if hprsw_energy_parity_thermoneutral_margin < 0:
        st.error(
            f"Fundamental parity warning: at the current H2-engine efficiency and H2 recovery chain, "
            f"the total gross energy ceiling required to equal the conventional {100*conventional_eff:.0f}% "
            f"efficiency is {hprsw_allowed_total_gross_for_energy_parity:.2f} kWh/kg gross H2, which is "
            f"{abs(hprsw_energy_parity_thermoneutral_margin):.2f} kWh/kg below the 298 K thermoneutral "
            f"water-splitting reference. Energy parity is therefore not thermodynamically closed until "
            f"engine efficiency and/or the H2 recovery chain improve."
        )
    else:
        st.success(
            f"The energy-parity ceiling is {hprsw_energy_parity_thermoneutral_margin:.2f} kWh/kg above "
            f"the 298 K thermoneutral reference before detailed reactor losses."
        )

    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric(
        "Max plasma electricity for cost parity",
        (
            f"{hprsw_max_plasma_kwhkg_cost_parity:.1f} kWh/kg H₂"
            if math.isfinite(hprsw_max_plasma_kwhkg_cost_parity)
            else "No electricity-price limit"
        ),
    )
    bc2.metric(
        "Break-even electricity price",
        f"CHF {hprsw_break_even_electricity_price_chf_kwh:.3f}/kWh"
        if math.isfinite(hprsw_break_even_electricity_price_chf_kwh)
        else "—",
    )
    bc3.metric("Current electricity price", f"CHF {electricity_price_chf_kwh:.3f}/kWh")
    bc4.metric("Conventional cost benchmark", f"CHF {hprsw_conv_cost_benchmark_per_net_kwh:.3f}/kWh net")

    energy_parity_possible = (
        hprsw_max_plasma_kwhkg_energy_parity >= 0
        and hprsw_required_recovery_chain_energy_parity <= 1.0
        and hprsw_required_engine_eff_energy_parity <= 1.0
        and hprsw_required_heat_recovery_energy_parity <= 1.0
    )
    cost_parity_possible = (
        hprsw_max_plasma_kwhkg_cost_parity >= 0
        if math.isfinite(hprsw_max_plasma_kwhkg_cost_parity)
        else True
    )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Break-even interpretation:</b><br>
        Energy-parity feasibility under the current one-at-a-time algebra: <b>{'mathematically reachable' if energy_parity_possible else 'not reachable without changing multiple assumptions'}</b>.<br>
        Cost-parity feasibility before capital cost, maintenance and lifecycle effects: <b>{'mathematically reachable' if cost_parity_possible else 'not reachable at the present non-electric operating costs'}</b>.<br><br>
        The solver compares HPRS-W total external energy to the selected conventional gasoline brake efficiency.
        It is a screening calculation, not an optimized reactor design.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 6 · V3.3 multi-parameter feasible region")

    st.caption(
        "The grid below changes plasma electricity, total H2 recovery, H2-engine efficiency "
        "and HPRS-W heat recovery simultaneously. Grid shares are deterministic search fractions, "
        "not probabilities of experimental success."
    )

    fg1, fg2, fg3, fg4 = st.columns(4)
    fg1.metric("Grid points scanned", f"{v29_total_grid_points:,}")
    fg2.metric(
        "Thermodynamically feasible",
        f"{v29_thermo_count:,} ({100*v29_thermo_share:.1f}%)",
    )
    fg3.metric(
        "Energy-competitive",
        f"{v29_energy_competitive_count:,}",
        help=(
            f"Thermodynamically feasible grid points with total-energy-to-shaft efficiency "
            f"at least the selected conventional benchmark ({100*conventional_eff:.1f}%)."
        ),
    )
    fg4.metric(
        "Energy + cost competitive",
        f"{v29_dual_competitive_count:,}",
        help="Points that satisfy both the energy benchmark and the current modeled operating-cost benchmark.",
    )

    current_status_parts = [
        "thermodynamically feasible" if v29_current_thermo_ok else "thermodynamically rejected",
        "energy-competitive" if v29_current_energy_competitive else "below energy benchmark",
        "cost-competitive" if v29_current_cost_competitive else "above cost benchmark",
    ]
    st.markdown(
        f"""
        <div class="horg-note">
        <b>Current selected HPRS-W point:</b> {', '.join(current_status_parts)}.<br>
        Current screened total-energy-to-shaft efficiency = <b>{100*v29_current_system_eff:.1f}%</b>;
        conventional benchmark = <b>{100*conventional_eff:.1f}%</b>.<br><br>
        <b>Thermodynamic guards used by V3.3:</b>
        total external energy must be at least <b>{WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2:.2f} kWh/kg H2</b>
        and modeled external exergy must be at least <b>{WATER_SPLIT_REV_KWH_PER_KG_H2:.2f} kWh/kg H2</b>.
        The heat-exergy contribution uses the selected heat-source temperature through a simple Carnot factor.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if v29_energy_competitive_points:
        _ep = v29_energy_competitive_points
        _p_min, _p_max = min(x["plasma"] for x in _ep), max(x["plasma"] for x in _ep)
        _r_min, _r_max = min(x["recovery"] for x in _ep), max(x["recovery"] for x in _ep)
        _e_min, _e_max = min(x["engine_eff"] for x in _ep), max(x["engine_eff"] for x in _ep)
        _h_min, _h_max = min(x["heat_recovery"] for x in _ep), max(x["heat_recovery"] for x in _ep)

        st.markdown("##### Coupled energy-competitive envelope")
        ce1, ce2, ce3, ce4 = st.columns(4)
        ce1.metric("Plasma electricity in competitive set", f"{_p_min:.1f}–{_p_max:.1f} kWh/kg H2")
        ce2.metric("Total H2 recovery in competitive set", f"{100*_r_min:.1f}–{100*_r_max:.1f}%")
        ce3.metric("H2-engine BTE in competitive set", f"{100*_e_min:.1f}–{100*_e_max:.1f}%")
        ce4.metric("Heat recovery in competitive set", f"{100*_h_min:.1f}–{100*_h_max:.1f}%")

        st.info(
            "This is a coupled envelope: the displayed minima and maxima do not form one single operating point. "
            "Each value occurs somewhere in a competitive combination with compensating values of the other variables."
        )

        def _v29_candidate_row(label, p):
            return {
                "Candidate": label,
                "Plasma kWh/kg H2": f"{p['plasma']:.1f}",
                "H2 recovery": f"{100*p['recovery']:.1f}%",
                "Engine BTE": f"{100*p['engine_eff']:.1f}%",
                "Heat recovery": f"{100*p['heat_recovery']:.1f}%",
                "External heat kWh/kg": f"{p['external_heat']:.2f}",
                "Total energy kWh/kg": f"{p['total_energy']:.2f}",
                "System efficiency": f"{100*p['system_eff']:.1f}%",
                "Modeled cost CHF/kWh net": f"{p['cost_per_net_kwh']:.3f}",
            }

        _candidate_rows = []
        _seen_candidates = set()
        for _label, _candidate in [
            ("Balanced stretch from current point", v29_balanced_energy_candidate),
            ("Lowest total external energy", v29_lowest_energy_candidate),
            ("Lowest cost with energy + cost parity", v29_lowest_cost_dual_candidate),
        ]:
            if _candidate is None:
                continue
            _key = (
                round(_candidate["plasma"], 8),
                round(_candidate["recovery"], 8),
                round(_candidate["engine_eff"], 8),
                round(_candidate["heat_recovery"], 8),
            )
            if _key not in _seen_candidates:
                _seen_candidates.add(_key)
                _candidate_rows.append(_v29_candidate_row(_label, _candidate))

        st.markdown("##### Representative feasible candidates")
        st.table(_candidate_rows)

        if v29_balanced_energy_candidate is not None:
            _b = v29_balanced_energy_candidate
            st.success(
                f"Balanced-search candidate: plasma {_b['plasma']:.1f} kWh/kg H2, "
                f"total H2 recovery {100*_b['recovery']:.1f}%, engine BTE {100*_b['engine_eff']:.1f}%, "
                f"heat recovery {100*_b['heat_recovery']:.1f}%. Under the selected standard-state guards, "
                f"this point gives about {100*_b['system_eff']:.1f}% total-energy-to-shaft efficiency."
            )
    else:
        st.error(
            "No energy-competitive point was found inside the selected V3.3 search ranges after applying "
            "the standard-state energy and exergy guards. Expand the search ranges or improve the assumed architecture."
        )


    # ============================================================
    # V3.3 PARETO FRONTIER — DECISION VIEW
    # ============================================================

    st.markdown("#### 7 · V3.3 Pareto Frontier — efficiency, cost and research stretch")

    st.caption(
        "The primary frontier below uses only two objectives: maximize screened system efficiency and minimize "
        "modeled operating cost. A Pareto point is not 'the winner'; it is a thermodynamically feasible grid point "
        "for which no cheaper point has equal or higher efficiency. Plasma electricity and research stretch remain "
        "visible as additional decision variables."
    )

    pf1, pf2, pf3, pf4 = st.columns(4)
    pf1.metric("Thermo-feasible points", f"{v29_thermo_count:,}")
    pf2.metric("Cost / efficiency Pareto points", f"{v30_pareto_count:,}")
    pf3.metric("Pareto + energy/cost competitive", f"{v30_dual_pareto_count:,}")
    pf4.metric(
        "Conventional benchmark",
        f"{100*conventional_eff:.1f}% · CHF {hprsw_conv_cost_benchmark_per_net_kwh:.3f}/kWh",
    )

    if v29_thermo_points and v30_cost_eff_pareto_points:
        # Keep the chart responsive while avoiding an unnecessarily heavy payload.
        _v30_stride = max(1, len(v29_thermo_points) // 2600)
        _v30_cloud_points = v29_thermo_points[::_v30_stride]

        _v30_chart_rows = []
        for _pnt in _v30_cloud_points:
            _v30_chart_rows.append(
                {
                    "Modeled cost CHF/kWh net": _pnt["cost_per_net_kwh"],
                    "System efficiency %": 100.0 * _pnt["system_eff"],
                    "Plasma kWh/kg H2": _pnt["plasma"],
                    "Research stretch %": 100.0 * _pnt["balanced_stretch"],
                    "Set": "Thermo-feasible grid",
                }
            )

        for _pnt in v30_cost_eff_pareto_points:
            _v30_chart_rows.append(
                {
                    "Modeled cost CHF/kWh net": _pnt["cost_per_net_kwh"],
                    "System efficiency %": 100.0 * _pnt["system_eff"],
                    "Plasma kWh/kg H2": _pnt["plasma"],
                    "Research stretch %": 100.0 * _pnt["balanced_stretch"],
                    "Set": "Pareto frontier",
                }
            )

        if v31_prototype_display_target is not None:
            _v30_chart_rows.append(
                {
                    "Modeled cost CHF/kWh net": v31_prototype_display_target["cost_per_net_kwh"],
                    "System efficiency %": 100.0 * v31_prototype_display_target["system_eff"],
                    "Plasma kWh/kg H2": v31_prototype_display_target["plasma"],
                    "Research stretch %": 100.0 * v31_prototype_display_target["balanced_stretch"],
                    "Set": "V3.3 prototype target",
                }
            )

        _v30_chart_df = pd.DataFrame(_v30_chart_rows)

        st.scatter_chart(
            _v30_chart_df,
            x="Modeled cost CHF/kWh net",
            y="System efficiency %",
            color="Set",
            size="Plasma kWh/kg H2",
            height=470,
        )

        st.caption(
            f"Reading the chart: lower cost is better on the x-axis and higher efficiency is better on the y-axis. "
            f"Bubble size represents plasma electricity. The conventional reference is "
            f"{100*conventional_eff:.1f}% and CHF {hprsw_conv_cost_benchmark_per_net_kwh:.3f}/kWh net. "
            "The chart is a deterministic projection of the selected grid, not a probability distribution."
        )

        def _v30_candidate_row(label, p):
            if p is None:
                return None
            return {
                "Decision point": label,
                "Plasma kWh/kg H2": f"{p['plasma']:.1f}",
                "H2 recovery": f"{100*p['recovery']:.1f}%",
                "Engine BTE": f"{100*p['engine_eff']:.1f}%",
                "Heat recovery": f"{100*p['heat_recovery']:.1f}%",
                "Total energy kWh/kg": f"{p['total_energy']:.2f}",
                "System efficiency": f"{100*p['system_eff']:.1f}%",
                "Modeled cost CHF/kWh": f"{p['cost_per_net_kwh']:.3f}",
                "Research stretch": f"{100*p['balanced_stretch']:.1f}%",
                "Cost/eff Pareto": "Yes" if _v30_point_key(p) in _v30_pareto_keys else "No",
            }

        _v30_decision_rows = []
        _v30_decision_seen = set()
        for _label, _candidate in [
            ("Pareto knee proxy", v30_knee_point),
            ("Lowest modeled cost", v30_lowest_cost_point),
            ("Highest screened efficiency", v30_max_efficiency_point),
            ("Lowest plasma in dual-competitive set", v30_lowest_plasma_dual_point),
            ("Minimum research stretch in dual set", v30_min_stretch_dual_point),
        ]:
            if _candidate is None:
                continue
            _key = _v30_point_key(_candidate)
            if _key in _v30_decision_seen:
                continue
            _v30_decision_seen.add(_key)
            _row = _v30_candidate_row(_label, _candidate)
            if _row is not None:
                _v30_decision_rows.append(_row)

        st.markdown("##### Representative V3.3 decision points")
        st.dataframe(_v30_decision_rows, width="stretch", hide_index=True)

        if v30_knee_point is not None:
            _k = v30_knee_point
            st.success(
                f"Pareto-knee proxy: plasma {_k['plasma']:.1f} kWh/kg H2, "
                f"H2 recovery {100*_k['recovery']:.1f}%, engine BTE {100*_k['engine_eff']:.1f}%, "
                f"heat recovery {100*_k['heat_recovery']:.1f}%, modeled system efficiency "
                f"{100*_k['system_eff']:.1f}% and cost CHF {_k['cost_per_net_kwh']:.3f}/kWh net."
            )

        # Second projection: efficiency versus normalized research stretch.
        _v30_stretch_rows = []
        for _pnt in v29_thermo_points[::_v30_stride]:
            _v30_stretch_rows.append(
                {
                    "Research stretch %": 100.0 * _pnt["balanced_stretch"],
                    "System efficiency %": 100.0 * _pnt["system_eff"],
                    "Plasma kWh/kg H2": _pnt["plasma"],
                    "Set": "Thermo-feasible grid",
                }
            )
        for _pnt in v30_stretch_eff_pareto_points:
            _v30_stretch_rows.append(
                {
                    "Research stretch %": 100.0 * _pnt["balanced_stretch"],
                    "System efficiency %": 100.0 * _pnt["system_eff"],
                    "Plasma kWh/kg H2": _pnt["plasma"],
                    "Set": "Stretch / efficiency frontier",
                }
            )

        if v31_prototype_display_target is not None:
            _v30_stretch_rows.append(
                {
                    "Research stretch %": 100.0 * v31_prototype_display_target["balanced_stretch"],
                    "System efficiency %": 100.0 * v31_prototype_display_target["system_eff"],
                    "Plasma kWh/kg H2": v31_prototype_display_target["plasma"],
                    "Set": "V3.3 prototype target",
                }
            )

        st.markdown("##### Efficiency vs research-stretch projection")
        st.scatter_chart(
            pd.DataFrame(_v30_stretch_rows),
            x="Research stretch %",
            y="System efficiency %",
            color="Set",
            size="Plasma kWh/kg H2",
            height=420,
        )

        st.info(
            "Research stretch is not a physical complexity measurement. It is the maximum normalized movement "
            "from the currently selected HPRS-W operating point across plasma electricity, H2 recovery, engine BTE "
            "and heat recovery. Lower values mean a smaller combined change inside the selected search box."
        )
    else:
        st.warning(
            "No Pareto frontier can be displayed because the selected search ranges contain no thermodynamically "
            "feasible points."
        )

    # ============================================================
    # V3.3 PROTOTYPE TARGET — CONSTRAINED ENGINEERING VIEW
    # ============================================================

    st.markdown("#### 8 · V3.3 Prototype Target — constrained engineering screen")

    st.caption(
        "This view intentionally limits the search to a more conservative first-prototype envelope. "
        "It does not claim that the selected limits are experimentally demonstrated or easy to achieve."
    )

    pt1, pt2, pt3, pt4 = st.columns(4)
    pt1.metric("Prototype-screen points", f"{v31_prototype_count:,}")
    pt2.metric("Energy-competitive", f"{v31_prototype_energy_count:,}")
    pt3.metric("Energy + cost competitive", f"{v31_prototype_dual_count:,}")
    pt4.metric(
        "Target criterion",
        "Energy parity" if v31_prototype_target is not None else "Best available",
    )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Prototype-screen limits:</b>
        plasma electricity ≥ <b>{v31_proto_min_plasma:.1f} kWh/kg H2</b>,
        total H2 recovery ≤ <b>{v31_proto_max_recovery_pct:.0f}%</b>,
        H2-engine BTE ≤ <b>{v31_proto_max_engine_bte_pct:.0f}%</b>,
        heat recovery ≤ <b>{v31_proto_max_heat_recovery_pct:.0f}%</b>.<br><br>
        These are engineering-screen assumptions. The plasma floor is deliberately conservative and is
        <b>not</b> a thermodynamic law on electrical input by itself. Standard-state total-energy and
        exergy guards remain ΔH = <b>{WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2:.2f} kWh/kg H2</b> and
        ΔG = <b>{WATER_SPLIT_REV_KWH_PER_KG_H2:.2f} kWh/kg H2</b> in this model.
        </div>
        """,
        unsafe_allow_html=True,
    )


    def _v31_comparison_row(label, p, current=False):
        if current:
            return {
                "Point": label,
                "Plasma kWh/kg H2": f"{hprsw_plasma_electricity:.1f}",
                "H2 recovery": f"{100*hprsw_recovery_chain:.1f}%",
                "Engine BTE": f"{100*engine_eff:.1f}%",
                "Heat recovery": f"{100*hprsw_heat_recovery:.1f}%",
                "Total energy kWh/kg": f"{v29_current_total_energy:.2f}",
                "System efficiency": f"{100*v29_current_system_eff:.1f}%",
                "Modeled cost CHF/kWh": f"{v29_current_cost_per_net_kwh:.3f}",
                "Energy parity": "Yes" if v29_current_energy_competitive else "No",
                "Cost parity": "Yes" if v29_current_cost_competitive else "No",
            }
        if p is None:
            return None
        return {
            "Point": label,
            "Plasma kWh/kg H2": f"{p['plasma']:.1f}",
            "H2 recovery": f"{100*p['recovery']:.1f}%",
            "Engine BTE": f"{100*p['engine_eff']:.1f}%",
            "Heat recovery": f"{100*p['heat_recovery']:.1f}%",
            "Total energy kWh/kg": f"{p['total_energy']:.2f}",
            "System efficiency": f"{100*p['system_eff']:.1f}%",
            "Modeled cost CHF/kWh": f"{p['cost_per_net_kwh']:.3f}",
            "Energy parity": "Yes" if p['system_eff'] + 1e-12 >= conventional_eff else "No",
            "Cost parity": "Yes" if p['cost_per_net_kwh'] <= hprsw_conv_cost_benchmark_per_net_kwh + 1e-12 else "No",
        }

    _v31_rows = [_v31_comparison_row("Current selected HPRS-W", None, current=True)]
    if v31_prototype_display_target is not None:
        _v31_rows.append(
            _v31_comparison_row(
                "V3.3 Prototype Target" if v31_prototype_target is not None else "Best point inside prototype screen",
                v31_prototype_display_target,
            )
        )
    if v30_knee_point is not None:
        _v31_rows.append(_v31_comparison_row("Pareto knee — theoretical decision proxy", v30_knee_point))

    st.markdown("##### Current point vs prototype target vs Pareto knee")
    st.dataframe(_v31_rows, width="stretch", hide_index=True)

    if v31_prototype_target is not None:
        _pt = v31_prototype_target
        _pt_cost_gap = _pt["cost_per_net_kwh"] - hprsw_conv_cost_benchmark_per_net_kwh
        st.success(
            f"Prototype-oriented energy-parity target: plasma {_pt['plasma']:.1f} kWh/kg H2, "
            f"H2 recovery {100*_pt['recovery']:.1f}%, engine BTE {100*_pt['engine_eff']:.1f}%, "
            f"heat recovery {100*_pt['heat_recovery']:.1f}%. Modeled total-energy-to-shaft efficiency "
            f"= {100*_pt['system_eff']:.1f}% versus {100*conventional_eff:.1f}% conventional."
        )
        if _pt_cost_gap <= 1e-12:
            st.info(
                f"This prototype target also meets the current modeled cost benchmark: "
                f"CHF {_pt['cost_per_net_kwh']:.3f}/kWh net versus CHF {hprsw_conv_cost_benchmark_per_net_kwh:.3f}/kWh net."
            )
        else:
            st.warning(
                f"Energy parity is reached, but modeled operating cost is still CHF {_pt_cost_gap:.3f}/kWh net above "
                f"the conventional benchmark. With the other selected cost assumptions unchanged, electricity would need "
                f"to be about CHF {v31_prototype_break_even_electricity_price:.3f}/kWh or lower for cost parity at this point."
            )
    elif v31_prototype_best_available is not None:
        _pb = v31_prototype_best_available
        st.warning(
            f"No point inside the current prototype-oriented limits reaches the {100*conventional_eff:.1f}% energy benchmark. "
            f"The best screened point reaches {100*_pb['system_eff']:.1f}% with plasma {_pb['plasma']:.1f} kWh/kg H2, "
            f"H2 recovery {100*_pb['recovery']:.1f}%, engine BTE {100*_pb['engine_eff']:.1f}% and "
            f"heat recovery {100*_pb['heat_recovery']:.1f}%."
        )
    else:
        st.error(
            "The current prototype-oriented constraints contain no thermodynamically feasible grid point. "
            "Relax one or more prototype-screen limits or widen the V3.3 feasible-region search ranges."
        )

    if v31_prototype_dual_target is not None:
        _pd = v31_prototype_dual_target
        st.caption(
            f"A point satisfying both energy and modeled-cost parity exists inside the prototype screen: "
            f"{_pd['plasma']:.1f} kWh/kg H2 plasma, {100*_pd['recovery']:.1f}% H2 recovery, "
            f"{100*_pd['engine_eff']:.1f}% engine BTE and {100*_pd['heat_recovery']:.1f}% heat recovery."
        )
    else:
        st.caption(
            "No energy+cost-parity point exists inside the current prototype-oriented limits at the selected prices. "
            "That does not imply physical impossibility; it identifies an economic gap within this deterministic screen."
        )


    st.markdown(
        f"""
        <div class="horg-callout">
        <b>V3.3 interpretation boundary:</b> a grid point marked feasible is only feasible within this
        lumped screening model. The scan does not solve temperature-dependent Gibbs equilibrium,
        electron-energy distributions, detailed H/O/OH kinetics, sheath fields, CFD, electrode erosion,
        membrane selectivity, H2/O2 flammability management, transient control or capital cost.
        A competitive grid point is therefore a <b>research target combination</b>, not a validated reactor design.
        </div>
        """,
        unsafe_allow_html=True,
    )



# ============================================================
# V3.3 RAIL APPLICATION — REGIONAL H2 TRAIN / HPRS-W
# ============================================================

st.markdown("---")
st.markdown('<span id="horg-rail" class="horg-section-anchor"></span>', unsafe_allow_html=True)
st.subheader("V3.3.6 Rail Application — HPRS-W for a regional hydrogen train")
st.caption(
    "The rail layer keeps the train electrically driven. It asks where the hydrogen comes from and whether HPRS-W "
    "is better treated as a depot hydrogen-production process or as an onboard reactor. Public FLIRT H2 figures are "
    "contextual guideposts only; the route/vehicle physics below are user-selected first-order assumptions."
)

# First-order route physics.
rail_mass_kg = rail_mass_t * 1000.0
rail_distance_m = rail_mission_km * 1000.0
rail_cruise_v_m_s = rail_cruise_speed_kmh / 3.6
rail_accel_v_m_s = rail_accel_speed_kmh / 3.6
rail_trip_h = rail_mission_km / max(rail_average_speed_kmh, 1e-9)

rail_roll_force_n = rail_mass_kg * GRAVITY_M_S2 * rail_crr
rail_aero_force_n = 0.5 * AIR_DENSITY_KG_M3 * rail_cda_m2 * rail_cruise_v_m_s ** 2
rail_steady_wheel_kwh = (rail_roll_force_n + rail_aero_force_n) * rail_distance_m / 3.6e6

rail_elevation_gain_m = rail_elevation_gain_m_per_100km * rail_mission_km / 100.0
rail_climb_wheel_kwh = rail_mass_kg * GRAVITY_M_S2 * rail_elevation_gain_m / 3.6e6
rail_descent_recovered_kwh = rail_climb_wheel_kwh * rail_regen_eff

rail_cycle_count = max(1.0, rail_stops_per_100km * rail_mission_km / 100.0)
rail_kinetic_per_cycle_kwh = 0.5 * rail_mass_kg * rail_accel_v_m_s ** 2 / 3.6e6
rail_accel_wheel_kwh = rail_cycle_count * rail_kinetic_per_cycle_kwh
rail_brake_recovered_kwh = rail_accel_wheel_kwh * rail_regen_eff

rail_positive_wheel_kwh = rail_steady_wheel_kwh + rail_climb_wheel_kwh + rail_accel_wheel_kwh
rail_recovered_dc_kwh = rail_descent_recovered_kwh + rail_brake_recovered_kwh
rail_traction_dc_kwh = max(rail_positive_wheel_kwh / max(rail_drive_eff, 1e-9) - rail_recovered_dc_kwh, 0.0)
rail_aux_kwh = rail_aux_kw * rail_trip_h
rail_dc_bus_kwh = rail_traction_dc_kwh + rail_aux_kwh
rail_dc_kwh_per_km = rail_dc_bus_kwh / max(rail_mission_km, 1e-9)
rail_avg_dc_kw = rail_dc_bus_kwh / max(rail_trip_h, 1e-9)

# Peak traction/battery support proxy.
rail_resist_force_at_accel_n = rail_mass_kg * GRAVITY_M_S2 * rail_crr + 0.5 * AIR_DENSITY_KG_M3 * rail_cda_m2 * rail_accel_v_m_s ** 2
rail_peak_wheel_kw = (rail_mass_kg * rail_accel_m_s2 + rail_resist_force_at_accel_n) * rail_accel_v_m_s / 1000.0
rail_peak_dc_kw = rail_peak_wheel_kw / max(rail_drive_eff, 1e-9) + rail_aux_kw
rail_battery_peak_support_kw = max(rail_peak_dc_kw - rail_fc_nominal_kw, 0.0)
rail_battery_support_min = (
    rail_battery_usable_kwh / rail_battery_peak_support_kw * 60.0
    if rail_battery_peak_support_kw > 0 else math.inf
)

# Stored-H2 + fuel-cell baseline.
rail_h2_mission_kg = rail_dc_bus_kwh / max(rail_fc_eff * H2_LHV_KWH_KG, 1e-9)
rail_h2_kg_per_km = rail_h2_mission_kg / max(rail_mission_km, 1e-9)
rail_h2_daily_kg = rail_h2_kg_per_km * rail_daily_km
rail_storage_range_km = rail_h2_storage_kg / max(rail_h2_kg_per_km, 1e-12)
rail_h2_cost_mission_chf = rail_h2_mission_kg * rail_delivered_h2_price_chf_kg
rail_h2_cost_per_km = rail_h2_cost_mission_chf / max(rail_mission_km, 1e-9)
rail_h2_tank_energy_kwh_per_km = rail_h2_kg_per_km * H2_LHV_KWH_KG

# Direct electric/catenary reference.
rail_direct_external_kwh = rail_dc_bus_kwh / max(rail_grid_to_dc_eff, 1e-9)
rail_direct_external_kwh_per_km = rail_direct_external_kwh / max(rail_mission_km, 1e-9)
rail_direct_cost_chf = rail_direct_external_kwh * electricity_price_chf_kwh
rail_direct_cost_per_km = rail_direct_cost_chf / max(rail_mission_km, 1e-9)

# HPRS-W depot production using the currently selected reactor assumptions.
rail_hprsw_gross_h2_kg = rail_h2_mission_kg / max(hprsw_recovery_chain, 1e-12)
rail_hprsw_electric_kwh = rail_hprsw_gross_h2_kg * hprsw_plasma_electricity
rail_hprsw_external_heat_kwh = rail_hprsw_gross_h2_kg * hprsw_steam_preheat * (1.0 - hprsw_heat_recovery)
rail_hprsw_total_external_kwh = rail_hprsw_electric_kwh + rail_hprsw_external_heat_kwh
rail_hprsw_external_kwh_per_km = rail_hprsw_total_external_kwh / max(rail_mission_km, 1e-9)

rail_hprsw_water_per_gross_h2 = (
    WATER_KG_PER_KG_H2_STOICH
    + WATER_KG_PER_KG_H2_STOICH * max(hprsw_steam_excess - 1.0, 0.0) * (1.0 - hprsw_excess_steam_recycle)
)
rail_hprsw_water_mission_l = rail_hprsw_gross_h2_kg * rail_hprsw_water_per_gross_h2
rail_hprsw_o2_mission_kg = rail_hprsw_gross_h2_kg * O2_KG_PER_KG_H2_STOICH * hprsw_o2_recovery
rail_hprsw_argon_makeup_kg = rail_hprsw_gross_h2_kg * hprsw_argon_circulation * (1.0 - hprsw_argon_recovery)

rail_hprsw_cost_mission_chf = max(
    0.0,
    rail_hprsw_electric_kwh * electricity_price_chf_kwh
    + rail_hprsw_external_heat_kwh * thermal_energy_price_chf_kwh
    + rail_hprsw_water_mission_l / 1000.0 * water_price_chf_m3
    + rail_hprsw_argon_makeup_kg * argon_price_chf_kg
    - rail_hprsw_o2_mission_kg * oxygen_value_chf_kg,
)
rail_hprsw_cost_per_km = rail_hprsw_cost_mission_chf / max(rail_mission_km, 1e-9)
rail_hprsw_chain_eff_dc = rail_dc_bus_kwh / max(rail_hprsw_total_external_kwh, 1e-12)

# HPRS-W break-even electricity price versus purchased H2 for the same train mission.
rail_hprsw_non_electric_cost_chf = (
    rail_hprsw_external_heat_kwh * thermal_energy_price_chf_kwh
    + rail_hprsw_water_mission_l / 1000.0 * water_price_chf_m3
    + rail_hprsw_argon_makeup_kg * argon_price_chf_kg
    - rail_hprsw_o2_mission_kg * oxygen_value_chf_kg
)
rail_hprsw_break_even_elec_price = (
    (rail_h2_cost_mission_chf - rail_hprsw_non_electric_cost_chf) / rail_hprsw_electric_kwh
    if rail_hprsw_electric_kwh > 0 else math.inf
)

# Onboard HPRS-W loop-closure diagnostic: fuel-cell DC output per delivered kg H2 versus
# the selected HPRS-W external process energy per delivered kg H2.
rail_fc_dc_per_delivered_h2 = H2_LHV_KWH_KG * rail_fc_eff
rail_hprsw_process_energy_per_delivered_h2 = hprsw_total_external_energy_per_delivered_h2
rail_onboard_loop_margin_kwh_per_kg = rail_fc_dc_per_delivered_h2 - rail_hprsw_process_energy_per_delivered_h2
rail_onboard_loop_ratio = (
    rail_fc_dc_per_delivered_h2 / rail_hprsw_process_energy_per_delivered_h2
    if rail_hprsw_process_energy_per_delivered_h2 > 0 else math.inf
)

# Prototype-oriented HPRS-W rail projection using the V3.3 target if one exists.
rail_proto_chain_eff = None
rail_proto_total_external_per_delivered = None
if v31_prototype_display_target is not None:
    _rp = v31_prototype_display_target
    rail_proto_total_external_per_delivered = _rp["total_energy"] / max(_rp["recovery"], 1e-12)
    rail_proto_chain_eff = H2_LHV_KWH_KG * rail_fc_eff / max(rail_proto_total_external_per_delivered, 1e-12)

if rail_reference == "Stadler FLIRT H₂ public guideposts":
    st.info(
        f"Public FLIRT H₂ guideposts: advertised range >{RAIL_PUBLIC_RANGE_KM:.0f} km, maximum speed "
        f"{RAIL_PUBLIC_MAX_SPEED_KMH:.0f} km/h, refuelling <{RAIL_PUBLIC_REFUEL_MIN:.0f} min, {RAIL_PUBLIC_SEATS} seats. "
        f"Stadler describes the SBCTA service case as roughly {RAIL_PUBLIC_DAILY_KM_LOW:.0f}–{RAIL_PUBLIC_DAILY_KM_HIGH:.0f} km/day. "
        "These values are context only; the model does not infer proprietary H2 storage mass, train mass, fuel-cell power or battery capacity."
    )

st.markdown("#### 9 · Rail mission energy and hybrid sizing")
rm1, rm2, rm3, rm4 = st.columns(4)
rm1.metric("Mission DC-bus energy", f"{rail_dc_bus_kwh:.0f} kWh")
rm2.metric("Electrical intensity", f"{rail_dc_kwh_per_km:.2f} kWh/km")
rm3.metric("Average DC demand", f"{rail_avg_dc_kw:.0f} kW")
rm4.metric("Peak DC-power proxy", f"{rail_peak_dc_kw:.0f} kW")

rm5, rm6, rm7, rm8 = st.columns(4)
rm5.metric("Stored-H₂ need", f"{rail_h2_mission_kg:.1f} kg / mission")
rm6.metric("H₂ intensity", f"{rail_h2_kg_per_km:.3f} kg/km")
rm7.metric("Scenario range from H₂ storage", f"{rail_storage_range_km:.0f} km")
rm8.metric("Daily H₂ at selected duty", f"{rail_h2_daily_kg:.1f} kg/day")

st.markdown(
    f"""
    <div class="horg-note">
    <b>Hybrid interpretation:</b> selected fuel-cell nominal power = <b>{rail_fc_nominal_kw:.0f} kW</b>.
    The first-order acceleration calculation gives a peak DC demand of <b>{rail_peak_dc_kw:.0f} kW</b>, so the battery
    would buffer about <b>{rail_battery_peak_support_kw:.0f} kW</b> of short-duration peak power under this scenario.
    The selected usable battery energy of <b>{rail_battery_usable_kwh:.0f} kWh</b> corresponds to about
    <b>{rail_battery_support_min:.1f} min</b> at that full peak-support level
    {'' if math.isfinite(rail_battery_support_min) else '(no peak support required at the selected fuel-cell rating)'}.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("#### 10 · Rail architecture comparison")
rail_compare_rows = [
    {
        "Rail pathway": "Direct electric / catenary or battery charge",
        "External / tank energy (kWh/km)": rail_direct_external_kwh_per_km,
        "H2 (kg/km)": 0.0,
        "Modeled operating energy cost (CHF/km)": rail_direct_cost_per_km,
        "Water makeup (L/km)": 0.0,
        "Point-of-use CO2": "0 in modeled electric traction",
    },
    {
        "Rail pathway": "Stored H2 + fuel cell/battery",
        "External / tank energy (kWh/km)": rail_h2_tank_energy_kwh_per_km,
        "H2 (kg/km)": rail_h2_kg_per_km,
        "Modeled operating energy cost (CHF/km)": rail_h2_cost_per_km,
        "Water makeup (L/km)": 0.0,
        "Point-of-use CO2": "0 direct",
    },
    {
        "Rail pathway": "Depot HPRS-W -> H2 -> fuel cell/battery",
        "External / tank energy (kWh/km)": rail_hprsw_external_kwh_per_km,
        "H2 (kg/km)": rail_h2_kg_per_km,
        "Modeled operating energy cost (CHF/km)": rail_hprsw_cost_per_km,
        "Water makeup (L/km)": rail_hprsw_water_mission_l / max(rail_mission_km, 1e-9),
        "Point-of-use CO2": "0 direct; upstream depends on electricity/heat",
    },
]
rail_compare_df = pd.DataFrame(rail_compare_rows)
st.dataframe(
    rail_compare_df.style.format({
        "External / tank energy (kWh/km)": "{:.2f}",
        "H2 (kg/km)": "{:.3f}",
        "Modeled operating energy cost (CHF/km)": "{:.2f}",
        "Water makeup (L/km)": "{:.3f}",
    }),
    width="stretch",
    hide_index=True,
)

rc1, rc2 = st.columns(2)
with rc1:
    st.markdown("##### Input-energy comparison")
    _rail_energy_chart = pd.DataFrame({
        "Pathway": ["Direct electric", "Stored H2", "Depot HPRS-W"],
        "kWh input / train-km": [rail_direct_external_kwh_per_km, rail_h2_tank_energy_kwh_per_km, rail_hprsw_external_kwh_per_km],
    }).set_index("Pathway")
    st.bar_chart(_rail_energy_chart, height=365)
with rc2:
    st.markdown("##### Modeled energy-cost comparison")
    _rail_cost_chart = pd.DataFrame({
        "Pathway": ["Direct electric", "Stored H2", "Depot HPRS-W"],
        "CHF / train-km": [rail_direct_cost_per_km, rail_h2_cost_per_km, rail_hprsw_cost_per_km],
    }).set_index("Pathway")
    st.bar_chart(_rail_cost_chart, height=365)

st.markdown("#### 11 · HPRS-W rail diagnosis")
rd1, rd2, rd3, rd4 = st.columns(4)
rd1.metric("Depot HPRS-W external energy", f"{rail_hprsw_external_kwh_per_km:.2f} kWh/km")
rd2.metric("HPRS-W -> fuel-cell DC efficiency", f"{100*rail_hprsw_chain_eff_dc:.1f}%")
rd3.metric("HPRS-W water makeup", f"{rail_hprsw_water_mission_l/rail_mission_km:.3f} L/km")
rd4.metric(
    "HPRS-W electricity break-even vs bought H₂",
    f"CHF {rail_hprsw_break_even_elec_price:.3f}/kWh" if math.isfinite(rail_hprsw_break_even_elec_price) else "—",
)

if rail_onboard_loop_margin_kwh_per_kg >= 0:
    st.success(
        f"Onboard loop diagnostic: fuel-cell DC output is {rail_fc_dc_per_delivered_h2:.1f} kWh per delivered kg H2, "
        f"while the selected HPRS-W process requires {rail_hprsw_process_energy_per_delivered_h2:.1f} kWh/kg delivered. "
        f"The simple energy margin is +{rail_onboard_loop_margin_kwh_per_kg:.1f} kWh/kg before auxiliaries. "
        "This still would not demonstrate a self-sustaining reactor; transient and thermodynamic coupling would require dedicated validation."
    )
else:
    st.error(
        f"Onboard self-powered loop does not close at the selected assumptions: the fuel cell returns about "
        f"{rail_fc_dc_per_delivered_h2:.1f} kWh DC per delivered kg H2, while HPRS-W requires about "
        f"{rail_hprsw_process_energy_per_delivered_h2:.1f} kWh external energy per delivered kg. "
        f"Margin = {rail_onboard_loop_margin_kwh_per_kg:.1f} kWh/kg; output/input ratio = {rail_onboard_loop_ratio:.2f}. "
        "For a rail prototype, the scientifically cleaner first architecture is therefore depot HPRS-W feeding an existing fuel-cell/battery PowerPack, "
        "or an onboard reactor supplied by a genuinely external source such as catenary/grid energy."
    )

if rail_proto_chain_eff is not None:
    st.info(
        f"Using the V3.3 prototype-oriented HPRS-W target instead of the current reactor point, the modeled external-to-fuel-cell-DC "
        f"chain efficiency would rise to about {100*rail_proto_chain_eff:.1f}% at the selected {100*rail_fc_eff:.0f}% fuel-cell efficiency. "
        f"That target still requires laboratory validation and is not a Stadler performance claim."
    )

# ============================================================
# V3.3.6 RAIL DEPOT: PV-ONLY vs GEOTHERMAL + PV, TRANSPARENT AMORTIZATION
# Compare independent plants at exactly the same rail H2 production volume.
# ============================================================
st.markdown('<span id="horg-hybrid-rail" class="horg-section-anchor"></span>', unsafe_allow_html=True)
st.markdown("#### 12 · Rail depot economics — PV-only versus PV + geothermal (V3.3.6)")
st.caption(
    "Six independent scenarios, all serving the SAME daily rail H₂ demand: PV without battery, "
    "PV with battery, and PV + geothermal with battery; each evaluated for HPRS-W and PEM. "
    "Every plant includes its own annualized CAPEX and OPEX. Grid backup is permitted in all cases. "
    "This is a screening model, not a site-specific energy or investment forecast."
)

rh_thermal_kw = rh_geo_flow_kg_s * 4.18 * max(rh_geo_temp_c - rh_geo_reinj_c, 0.0)
rh_thermal_kwh_day = rh_thermal_kw * 24.0 * rh_geo_availability
rh_geo_gross_electric_day = rh_thermal_kwh_day * rh_geo_steam_frac * rh_geo_turbine_eff * rh_geo_gen_eff
rh_geo_net_electric_day = rh_geo_gross_electric_day * (1.0 - rh_geo_parasitic)
rh_geo_recoverable_heat_day = (
    rh_thermal_kwh_day * max(0.0, 1.0 - rh_geo_steam_frac * rh_geo_turbine_eff) * rh_geo_heat_recov
)
rh_geo_eligible_heat_day = (
    rh_geo_recoverable_heat_day * rh_geo_heat_grade
    if rh_geo_temp_c >= rh_required_heat_temp_c else 0.0
)
rh_daily_kg = rail_h2_daily_kg
rh_hprs_sec = hprsw_plasma_electricity / max(hprsw_recovery_chain, 1e-12)
rh_hprsw_heat_req_day = (
    rh_daily_kg / max(hprsw_recovery_chain, 1e-12)
    * hprsw_steam_preheat * (1.0 - hprsw_heat_recovery)
)
rh_hprs_water_m3_day = (
    rh_daily_kg / max(hprsw_recovery_chain, 1e-12)
    * rail_hprsw_water_per_gross_h2 / 1000.0
)
rh_hprs_argon_kg_day = (
    rh_daily_kg / max(hprsw_recovery_chain, 1e-12)
    * hprsw_argon_circulation * (1.0 - hprsw_argon_recovery)
)
rh_hprs_o2_kg_day = (
    rh_daily_kg / max(hprsw_recovery_chain, 1e-12)
    * O2_KG_PER_KG_H2_STOICH * hprsw_o2_recovery
)
rh_pem_water_m3_day = rh_daily_kg * WATER_KG_PER_KG_H2_STOICH / 1000.0
rh_owned_assets = rh_costing_mode.startswith("Owned assets")
rh_lifetimes = {
    'Reactor H₂': rh_life_reactor,
    'PV allocated': rh_life_pv,
    'Battery allocated': rh_life_battery,
    'Geothermal allocated': rh_life_geo,
}
rh_annual_h2 = max(rh_daily_kg * rh_days, 1e-12)


def rail_depot_scenario(technology, with_geothermal, use_battery=True,
                        scenario_operating_days=None, scenario_sun_hours=None):
    """Independent alternative with explicit costing boundary and CAPEX schedule."""
    specific_energy = rh_hprs_sec if technology == 'HPRS-W' else rh_pem_kwh_kg
    actual_days = rh_days if scenario_operating_days is None else int(scenario_operating_days)
    actual_sun_hours = rh_sun_hours if scenario_sun_hours is None else float(scenario_sun_hours)
    actual_battery_capacity = rh_battery_kwh if use_battery else 0.0
    actual_battery_power = rh_battery_kw if use_battery else 0.0
    geo_day = rh_geo_net_electric_day if with_geothermal else 0.0
    geo_fraction = rh_geo_alloc if with_geothermal else 0.0
    dispatch = rail_hybrid_dispatch(
        rh_pv_kwp, actual_sun_hours, rh_pv_pr, geo_day, geo_fraction,
        actual_battery_capacity, actual_battery_power, rh_battery_eff,
        rh_daily_kg, specific_energy,
    )
    reactor_capex = rh_hprsw_capex if technology == 'HPRS-W' else rh_pem_capex
    asset_caps = {
        'Reactor H₂': reactor_capex,
        'PV allocated': rh_pv_capex * rh_pv_capex_alloc if rh_owned_assets else 0.0,
        'Battery allocated': rh_bat_capex * rh_bat_capex_alloc if use_battery else 0.0,
        'Geothermal allocated': (
            rh_geo_capex_allocated if with_geothermal and rh_owned_assets else 0.0
        ),
    }
    schedule = rail_asset_cost_schedule(asset_caps, rh_lifetimes, rh_interest)
    annual_capital = sum(asset['Economic annuity CHF/year'] for asset in schedule)
    annual_depreciation = sum(asset['Straight-line depreciation CHF/year'] for asset in schedule)
    fixed_opex = {
        'Reactor maintenance': reactor_capex * rh_fixed_opex_fraction,
        'PV maintenance': asset_caps['PV allocated'] * rh_pv_opex_pct,
        'Battery maintenance': asset_caps['Battery allocated'] * rh_battery_opex_pct,
        'Geothermal allocated OPEX': (
            rh_geo_opex_allocated if with_geothermal and rh_owned_assets else 0.0
        ),
    }
    annual_fixed = sum(fixed_opex.values())
    geo_heat_used = (
        min(rh_hprsw_heat_req_day, rh_geo_eligible_heat_day)
        if technology == 'HPRS-W' and with_geothermal else 0.0
    )
    purchased_heat_day = (
        rh_hprsw_heat_req_day - geo_heat_used if technology == 'HPRS-W' else 0.0
    )
    operating_lines = {
        'Purchased grid electricity': dispatch['grid_kwh_day'] * rh_grid_cost,
        'Renewables under transfer contract': (
            dispatch['renewable_used_kwh_day'] * rh_renew_value
            if not rh_owned_assets else 0.0
        ),
        'Process water': (
            rh_hprs_water_m3_day if technology == 'HPRS-W' else rh_pem_water_m3_day
        ) * water_price_chf_m3,
        'Argon make-up': (
            rh_hprs_argon_kg_day * argon_price_chf_kg if technology == 'HPRS-W' else 0.0
        ),
        'Externally supplied process heat': purchased_heat_day * rh_purchased_heat_price,
        'Geothermal heat under transfer contract': (
            geo_heat_used * rh_geo_heat_value if not rh_owned_assets else 0.0
        ),
        'Variable process/compression OPEX': rh_daily_kg * rh_extra_chf_kg,
        'Recovered O₂ credit': (
            -rh_hprs_o2_kg_day * oxygen_value_chf_kg if technology == 'HPRS-W' else 0.0
        ),
    }
    variable_per_day = sum(operating_lines.values())
    variable_per_year = variable_per_day * actual_days
    annual_h2_in_scenario = max(rh_daily_kg * actual_days, 1e-12)
    full_annual = variable_per_year + annual_capital + annual_fixed
    eligible_for_ranking = True
    missing_cost_reason = ''
    if rh_owned_assets:
        if rh_pv_kwp > 0 and (rh_pv_capex_alloc <= 0 or rh_pv_capex <= 0):
            eligible_for_ranking = False
            missing_cost_reason = 'PV CAPEX / cost allocation missing'
        if use_battery and actual_battery_capacity > 0 and (
            rh_bat_capex <= 0 or rh_bat_capex_alloc <= 0
        ):
            eligible_for_ranking = False
            missing_cost_reason = 'Battery CAPEX / allocation missing'
        if with_geothermal and rh_geo_alloc > 0 and (
            rh_geo_capex_allocated <= 0 or rh_geo_opex_allocated <= 0
        ):
            eligible_for_ranking = False
            missing_cost_reason = 'Geothermal CAPEX/OPEX allocation missing'
    elif rh_renew_value <= 0 and dispatch['renewable_used_kwh_day'] > 0:
        eligible_for_ranking = False
        missing_cost_reason = 'Renewable transfer price missing'
    if reactor_capex <= 0:
        eligible_for_ranking = False
        missing_cost_reason = 'Hydrogen plant CAPEX missing'
    total_demand_kwh_day = rh_daily_kg * specific_energy
    system_label = ('PV + geothermal + battery' if with_geothermal and use_battery
                    else 'PV + battery' if use_battery else 'PV without battery')
    result = {
        'Label': f"{system_label} / {technology}",
        'Technology': technology, 'With geothermal': with_geothermal,
        'Uses battery': bool(use_battery), 'Operating days/year': actual_days,
        'Full-sun hours/day': actual_sun_hours,
        'Dispatch': dispatch, 'CAPEX schedule': schedule,
        'Fixed OPEX details': fixed_opex, 'Variable OPEX details': operating_lines,
        'Daily H₂ kg': rh_daily_kg, 'Annual H₂ kg': annual_h2_in_scenario,
        'Annual capital recovery CHF': annual_capital,
        'Annual straight-line depreciation CHF': annual_depreciation,
        'Annual fixed OPEX CHF': annual_fixed,
        'Annual variable OPEX CHF': variable_per_year,
        'Full annual cost CHF': full_annual,
        'Cost CHF/kg H₂': full_annual / annual_h2_in_scenario,
        'Variable CHF/kg': variable_per_year / annual_h2_in_scenario,
        'Capital CHF/kg': annual_capital / annual_h2_in_scenario,
        'Fixed OPEX CHF/kg': annual_fixed / annual_h2_in_scenario,
        'Cost CHF/train-km': full_annual / annual_h2_in_scenario * rail_h2_kg_per_km,
        'Grid share percent': (
            100.0 * dispatch['grid_kwh_day'] / max(total_demand_kwh_day, 1e-9)
        ),
        'Process heat geothermal kWh/day': geo_heat_used,
        'Purchased process heat kWh/day': purchased_heat_day,
        'Complete': eligible_for_ranking,
        'Cost limitation': missing_cost_reason,
    }
    return result


rh_scenarios = [
    rail_depot_scenario('HPRS-W', False, use_battery=False),
    rail_depot_scenario('PEM', False, use_battery=False),
    rail_depot_scenario('HPRS-W', False, use_battery=True),
    rail_depot_scenario('PEM', False, use_battery=True),
    rail_depot_scenario('HPRS-W', True, use_battery=True),
    rail_depot_scenario('PEM', True, use_battery=True),
]
if rh_daily_kg <= 0:
    st.warning('No positive rail H₂ demand; cost comparison cannot be interpreted.')

if rh_owned_assets and rh_geo_alloc > 0 and (
    rh_geo_capex_allocated <= 0 or rh_geo_opex_allocated <= 0
):
    st.warning(
        'Geothermal + PV is an INCOMPLETE economic scenario: enter the attributable '
        'geothermal investment and annual fixed OPEX in the left sidebar. Its CHF/kg '
        'will be displayed, but it will not be ranked as a fully costed alternative. '
        'The PV-only alternatives require no geothermal investment.'
    )

st.markdown('##### Hydrogen cost comparison — six plant alternatives and purchased H₂')
rh_comparison_rows = [
    {
        'Pathway': s['Label'],
        'Cost CHF/kg H₂': s['Cost CHF/kg H₂'],
        'Cost CHF/train-km': s['Cost CHF/train-km'],
        'Capital CHF/kg': s['Capital CHF/kg'],
        'Fixed OPEX CHF/kg': s['Fixed OPEX CHF/kg'],
        'Variable CHF/kg': s['Variable CHF/kg'],
        'Grid share %': s['Grid share percent'],
        'Status': 'Costed' if s['Complete'] else 'Incomplete allocation',
    }
    for s in rh_scenarios
]
rh_comparison_rows.append({
    'Pathway': 'Purchased delivered H₂',
    'Cost CHF/kg H₂': rail_delivered_h2_price_chf_kg,
    'Cost CHF/train-km': rail_h2_cost_per_km,
    'Capital CHF/kg': 0.0, 'Fixed OPEX CHF/kg': 0.0,
    'Variable CHF/kg': rail_delivered_h2_price_chf_kg,
    'Grid share %': float('nan'), 'Status': 'Reference purchase price',
})
rh_compare = pd.DataFrame(rh_comparison_rows)
st.dataframe(
    rh_compare.style.format({
        'Cost CHF/kg H₂': '{:,.2f}', 'Cost CHF/train-km': '{:,.2f}',
        'Capital CHF/kg': '{:,.2f}', 'Fixed OPEX CHF/kg': '{:,.2f}',
        'Variable CHF/kg': '{:,.2f}', 'Grid share %': '{:.1f}',
    }, na_rep='—'), width='stretch', hide_index=True,
)
st.caption(
    'PV without battery, PV + battery, and PV + geothermal + battery are independently evaluated. '
    'Grid backup is permitted and charged. Every scenario serves the same modeled H₂ demand; no battery CAPEX/OPEX '
    'is charged to the no-battery alternatives. Plants are alternatives, not simultaneous purchases. '
    'Purchased H₂ is a user-entered reference price.'
)

rh_costed = [s for s in rh_scenarios if s['Complete']]
if rh_costed and rh_daily_kg > 0:
    rh_winner = min(rh_costed, key=lambda s: s['Cost CHF/kg H₂'])
    rh_best_cost = min(rh_winner['Cost CHF/kg H₂'], rail_delivered_h2_price_chf_kg)
    cheapest = (
        rh_winner['Label'] if rh_winner['Cost CHF/kg H₂'] <= rail_delivered_h2_price_chf_kg
        else 'Purchased delivered H₂'
    )
    st.info(
        f'Lowest displayed complete-cost alternative under THESE assumptions: **{cheapest}**, '
        f'about **CHF {rh_best_cost:,.2f}/kg H₂**. '
        'This is not a site-validated or bankable estimate.'
    )
else:
    st.info('No fully costed own-production alternative; complete the cost inputs.')

hrc1, hrc2 = st.columns(2)
with hrc1:
    st.markdown('##### Cost per kg H₂ — includes annualized CAPEX')
    st.bar_chart(rh_compare.set_index('Pathway')[['Cost CHF/kg H₂']], height=330)
with hrc2:
    st.markdown('##### Cost composition — CHF/kg H₂')
    st.bar_chart(
        rh_compare.set_index('Pathway')[
            ['Capital CHF/kg', 'Fixed OPEX CHF/kg', 'Variable CHF/kg']
        ], stack=True, height=330,
    )

st.markdown('##### Transparent amortization — inspect one alternative')
rh_selected_name = st.selectbox(
    'Choose the alternative for detailed capital/depreciation calculations',
    [scenario['Label'] for scenario in rh_scenarios],
    key='rh_detail_pick',
)
rh_selected = next(s for s in rh_scenarios if s['Label'] == rh_selected_name)
rh_am1, rh_am2, rh_am3, rh_am4 = st.columns(4)
rh_am1.metric('Attributed initial CAPEX', f"CHF {sum(x['Attributed CAPEX CHF'] for x in rh_selected['CAPEX schedule']):,.0f}")
rh_am2.metric('Economic annualized CAPEX', f"CHF {rh_selected['Annual capital recovery CHF']:,.0f}/yr")
rh_am3.metric('Straight-line depreciation (info only)', f"CHF {rh_selected['Annual straight-line depreciation CHF']:,.0f}/yr")
rh_am4.metric('Annual production', f"{rh_selected['Annual H₂ kg']:,.0f} kg/yr")

with st.expander('Amortization formula, per-asset schedule, operating cost and power dispatch', expanded=True):
    st.latex(r'\mathrm{Annualized\ CAPEX}=\sum_i C_i\frac{r(1+r)^{n_i}}{(1+r)^{n_i}-1}')
    st.caption(
        f'Annual real financing rate r = {rh_interest_pct:.1f}%. Each asset has its own lifetime. '
        'Economic annualized CAPEX is included in CHF/kg. Accounting depreciation is displayed '
        'for transparency ONLY, not added again to the price. Annual operating days: '
        f'{rh_days}; annual output: {rh_selected["Annual H₂ kg"]:,.0f} kg.'
    )
    rh_schedule_df = pd.DataFrame(rh_selected['CAPEX schedule'])
    st.dataframe(rh_schedule_df.style.format({
        'Attributed CAPEX CHF': '{:,.0f}',
        'Straight-line depreciation CHF/year': '{:,.0f}',
        'Economic annuity CHF/year': '{:,.0f}',
    }), width='stretch', hide_index=True)
    rh_line_items = []
    rh_line_items.extend({
        'Annual cost item': name, 'CHF/year': amount * rh_selected['Operating days/year'],
        'CHF/kg H₂': amount / max(rh_selected['Daily H₂ kg'], 1e-9),
    } for name, amount in rh_selected['Variable OPEX details'].items())
    rh_line_items.extend({
        'Annual cost item': name, 'CHF/year': amount,
        'CHF/kg H₂': amount / rh_selected['Annual H₂ kg'],
    } for name, amount in rh_selected['Fixed OPEX details'].items())
    rh_line_items.extend({
        'Annual cost item': f"Annualized capital: {a['Asset']}",
        'CHF/year': a['Economic annuity CHF/year'],
        'CHF/kg H₂': a['Economic annuity CHF/year'] / rh_selected['Annual H₂ kg'],
    } for a in rh_selected['CAPEX schedule'])
    rh_line_items.append({
        'Annual cost item': 'TOTAL (do not add depreciation again)',
        'CHF/year': rh_selected['Full annual cost CHF'],
        'CHF/kg H₂': rh_selected['Cost CHF/kg H₂'],
    })
    rh_line_df = pd.DataFrame(rh_line_items)
    st.dataframe(rh_line_df.style.format({
        'CHF/year': '{:,.2f}', 'CHF/kg H₂': '{:,.3f}',
    }), width='stretch', hide_index=True)
    rd = rh_selected['Dispatch']
    rdisp = pd.DataFrame(rd['rows']).set_index('Hour')
    st.line_chart(
        rdisp[['PV kWh', 'Geothermal kWh', 'Process demand kWh', 'Grid imports kWh']],
        height=310,
    )
    st.bar_chart(rdisp[['Battery charged kWh', 'Battery discharged kWh']], height=230)
    rh_dm1, rh_dm2, rh_dm3, rh_dm4 = st.columns(4)
    rh_dm1.metric('PV modeled electricity', f"{rd['pv_kwh_day']:,.0f} kWh/day")
    rh_dm2.metric('Geothermal electricity allocated', f"{rd['geo_allocated_kwh_day']:,.0f} kWh/day")
    rh_dm3.metric('Grid purchase', f"{rd['grid_kwh_day']:,.0f} kWh/day")
    rh_dm4.metric('Renewable surplus', f"{rd['surplus_kwh_day']:,.0f} kWh/day")
    st.caption(
        f"Steady-day battery SOC: {rd['battery_start_kwh']:,.0f} → "
        f"{rd['battery_end_kwh']:,.0f} kWh. Generated but unused PV/geo energy has "
        'no fictitious sale revenue. Grid prices are user assumptions.'
    )
    st.write(
        f"HPRS-W preheat needed **{rh_hprsw_heat_req_day:,.0f} kWh_th/day**; "
        f"geothermal heat credited in this alternative **{rh_selected['Process heat geothermal kWh/day']:,.0f} kWh_th/day**; "
        f"purchased heat **{rh_selected['Purchased process heat kWh/day']:,.0f} kWh_th/day**. "
        'No geothermal heat is assumed in the PV-only scenario.'
    )
    st.download_button(
        'Download full amortization and OPEX breakdown (CSV)',
        rh_line_df.to_csv(index=False).encode('utf-8'),
        file_name='hydrogenorg_rail_amortization_v336.csv', mime='text/csv',
    )
    st.download_button(
        'Download selected 24 h dispatch (CSV)',
        rdisp.reset_index().to_csv(index=False).encode('utf-8'),
        file_name='hydrogenorg_rail_dispatch_v336.csv', mime='text/csv',
    )

st.download_button(
    'Download all seven hydrogen cost alternatives (CSV)',
    rh_compare.to_csv(index=False).encode('utf-8'),
    file_name='hydrogenorg_rail_all_pathways_v336.csv', mime='text/csv',
)

# ============================================================
# V3.3.6 INVESTMENT / AMORTIZATION / PV-ONLY FINANCIAL DASHBOARD
# No fictitious production gains or free renewable energy are assumed.
# ============================================================
st.markdown('##### 12A · Investment & amortization — side-by-side comparison')
st.caption(
    'Cash CAPEX is allocated once, annualized through a real capital recovery factor, '
    'and maintenance is charged separately. Straight-line depreciation is INFORMATION only. '
    'The six production plants are independent alternatives; each produces the same rail H₂ per operating day.'
)
rh_investment_rows = []
for _rs in rh_scenarios:
    rh_investment_rows.append({
        'Alternative': _rs['Label'],
        'Complete costs': 'Yes' if _rs['Complete'] else 'NO — missing costs',
        'Initial CAPEX CHF': sum(a['Attributed CAPEX CHF'] for a in _rs['CAPEX schedule']),
        'Capital recovery CHF/year': _rs['Annual capital recovery CHF'],
        'Maintenance CHF/year': _rs['Annual fixed OPEX CHF'],
        'Variable CHF/year': _rs['Annual variable OPEX CHF'],
        'Annual H₂ kg': _rs['Annual H₂ kg'],
        'Final CHF/kg': _rs['Cost CHF/kg H₂'],
        'Grid electricity %': _rs['Grid share percent'],
    })
rh_investment_df = pd.DataFrame(rh_investment_rows)
st.dataframe(
    rh_investment_df.style.format({
        'Initial CAPEX CHF': '{:,.0f}', 'Capital recovery CHF/year': '{:,.0f}',
        'Maintenance CHF/year': '{:,.0f}', 'Variable CHF/year': '{:,.0f}',
        'Annual H₂ kg': '{:,.0f}', 'Final CHF/kg': '{:,.2f}',
        'Grid electricity %': '{:.1f}',
    }), width='stretch', hide_index=True,
)
st.download_button(
    'Download investment comparison (CSV)',
    rh_investment_df.to_csv(index=False).encode('utf-8'),
    file_name='hydrogenorg_rail_investment_comparison_v336.csv', mime='text/csv',
)

st.markdown('##### 12B · CHF 10/kg challenge — production utilisation and capital gap')
rh_target_chfkg = st.number_input(
    'Target full-cost price (CHF/kg H₂)', min_value=0.1, max_value=100.0,
    value=10.0, step=0.5, key='rh_target_chfkg',
    help='Decision threshold only; NOT a performance assumption.',
)
st.caption(
    'The target test preserves daily production capacity, current plant sizing, fixed CAPEX and maintenance. '
    'It varies operating days/year ONLY. The assumed representative hourly PV profile and grid backup '
    'do not guarantee real seasonal production, component durability or market demand.'
)
rh_break_even_rows = []
for _rs in rh_scenarios:
    _daily = _rs['Daily H₂ kg']
    _variable_day = (_rs['Annual variable OPEX CHF'] /
                     max(_rs['Operating days/year'], 1))
    _variable_kg = _variable_day / max(_daily, 1e-12)
    _fixed_year = _rs['Annual capital recovery CHF'] + _rs['Annual fixed OPEX CHF']
    _fixed_margin_day = _daily * rh_target_chfkg - _variable_day
    _required_days = (_fixed_year / _fixed_margin_day
                      if _fixed_margin_day > 1e-12 else math.inf)
    _annual_budget_for_capital = (
        rh_target_chfkg * _rs['Annual H₂ kg']
        - _rs['Annual variable OPEX CHF'] - _rs['Annual fixed OPEX CHF']
    )
    _capital_gap = max(0.0, _rs['Annual capital recovery CHF'] -
                       max(0.0, _annual_budget_for_capital))
    _zero_capex_cost = (
        _variable_kg + _rs['Annual fixed OPEX CHF'] / max(_rs['Annual H₂ kg'], 1e-12)
    )
    _required_capital_reduction = (
        100.0 * _capital_gap / _rs['Annual capital recovery CHF']
        if _rs['Annual capital recovery CHF'] > 0 else 0.0
    )
    _cost_365 = (_variable_kg + _fixed_year / (365.0 * max(_daily, 1e-12)))
    _feasible_label = (
        'Uncosted — do not rank' if not _rs['Complete'] else
        'Already at/below target' if _rs['Cost CHF/kg H₂'] <= rh_target_chfkg else
        'Not even with zero CAPEX at current days' if _annual_budget_for_capital < 0 else
        'Possible at <=365 days (screen only)' if _required_days <= 365 else
        'Not met at 365 days' if math.isfinite(_required_days) else
        'Impossible with current variable cost'
    )
    rh_break_even_rows.append({
        'Alternative': _rs['Label'],
        'Cost today CHF/kg': _rs['Cost CHF/kg H₂'],
        'Variable floor CHF/kg': _variable_kg,
        'Cost at zero CAPEX CHF/kg': _zero_capex_cost,
        'Cost at 365 d CHF/kg': _cost_365,
        'Operating days needed for target': _required_days if math.isfinite(_required_days) else None,
        'Annual capital gap CHF': _capital_gap,
        'Capital gap % (fixed OPEX unchanged)': _required_capital_reduction,
        'Interpretation': _feasible_label,
    })
rh_target_df = pd.DataFrame(rh_break_even_rows)
st.dataframe(rh_target_df.style.format({
    'Cost today CHF/kg': '{:,.2f}',
    'Variable floor CHF/kg': '{:,.2f}',
    'Cost at zero CAPEX CHF/kg': '{:,.2f}',
    'Cost at 365 d CHF/kg': '{:,.2f}',
    'Operating days needed for target': '{:,.0f}',
    'Annual capital gap CHF': '{:,.0f}',
    'Capital gap % (fixed OPEX unchanged)': '{:.1f}%',
}, na_rep='—'), width='stretch', hide_index=True)
st.caption(
    'Capital gap is the required reduction in ANNUALIZED capital cost at the current H₂ output, '
    'holding fixed OPEX constant. It is not automatically an achievable reduction in equipment size, '
    'and does not credit any additional energy or hydrogen production. A negative annual capital '
    'budget is clipped to zero; the target is then impossible even at zero CAPEX.'
)

st.markdown('##### 12C · Utilisation stress test — same assets, 200–365 operating days')
rh_util_days = [200, 250, 300, rh_days, 330, 365]
rh_util_days = sorted(set(rh_util_days))
rh_util_data = []
for _s in rh_scenarios:
    if not _s['Complete']:
        continue
    for _d in rh_util_days:
        _scaled = rail_depot_scenario(
            _s['Technology'], _s['With geothermal'],
            use_battery=_s['Uses battery'], scenario_operating_days=_d,
        )
        rh_util_data.append({
            'Days/year': _d, 'Alternative': _s['Label'],
            'Cost CHF/kg': _scaled['Cost CHF/kg H₂'],
        })
if rh_util_data:
    rh_util_df = pd.DataFrame(rh_util_data)
    st.line_chart(
        rh_util_df.pivot(index='Days/year', columns='Alternative', values='Cost CHF/kg'),
        height=345,
    )
    st.download_button(
        'Download utilisation sensitivity (CSV)',
        rh_util_df.to_csv(index=False).encode('utf-8'),
        file_name='hydrogenorg_rail_utilisation_v336.csv', mime='text/csv',
    )
else:
    st.warning('Enter all necessary investment and operating costs before testing utilisation.')

st.info(
    'Critical modelling limits: 365 operating days is not a verified PV/plant availability estimate. '
    'Annual production, demand, grid capacity, curtailment, winter solar irradiation, battery cycling, '
    'future battery replacement, permits, site-specific geothermal drilling and safety are NOT proven. '
    'Zero geothermal costs and zero hydrogen-plant CAPEX invalidate an investment comparison. '
    'A target below CHF 10/kg must be DEMONSTRATED by validated technology and site data, not assumed.'
)

st.info(
    'Methodological boundaries: Geothermal V4.0 uses a simplified lumped heat-to-power model. '
    'PV production is a repeated representative day, not a Swiss hourly weather year; neither winter production '
    'nor seasonal PV/storage economics are captured. Grid back-up is permitted. '
    'HPRS-W plasma consumption/recovery are unvalidated experimental inputs. '
    'In owned-asset mode, PV and geothermal electricity already carry their amortization and maintenance, '
    'so the renewable internal transfer price is NOT added. Under a renewable-energy supply contract, '
    'PV/geo CAPEX and geo OPEX are excluded, replaced by an editable electricity/heat transfer price. '
    'Battery and H₂ plant are owned in both cases. Cost analysis excludes project taxes, replacement overhauls, '
    'land/permits, financing fees, hydrogen storage/distribution infrastructure and detailed plant degradation. '
    'Zero allocated geothermal capital/maintenance makes the owned hybrid comparison incomplete. '
    'PV without batteries is compared explicitly (grid backup allowed). '
    'PV with batteries and PV + geothermal carry separate asset annualization.'
)
st.link_button(
    'Open separate HydrogenOrg Hybrid Energy simulator',
    'https://hydrogenorg-hybrid-frxmeevahxd7vcng3uk3em.streamlit.app/',
)

st.markdown(
    f"""
    <div class="horg-callout">
    <b>Rail model boundary:</b> this is not a longitudinal train-dynamics, timetable or homologation model. It uses simple rolling and aerodynamic resistance,
    an equivalent positive elevation gain, repeated acceleration/braking cycles, an average auxiliary load and user-selected drivetrain efficiencies.
    It does not include wheel/rail adhesion limits, detailed gradients/curves, passenger load variation, compressor losses, H2 storage thermal behavior,
    fuel-cell degradation, battery SOC control, HVAC transients, redundancy, fire safety, crash requirements, capital cost or maintenance.
    Public Stadler values are contextual guideposts only. A partner study should replace the scenario inputs with route and PowerPack data supplied by the rail OEM.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Rail public references and model equations"):
    st.markdown(
        f"""
        **Public FLIRT H2 guideposts**  
        Stadler states for the SBCTA FLIRT H2: range **> {RAIL_PUBLIC_RANGE_KM:.0f} km**, maximum speed **{RAIL_PUBLIC_MAX_SPEED_KMH:.0f} km/h**,
        refuelling **< {RAIL_PUBLIC_REFUEL_MIN:.0f} min**, and **{RAIL_PUBLIC_SEATS} seats**. The SBCTA reference page describes up to 16 trips/day and
        roughly **{RAIL_PUBLIC_DAILY_KM_LOW:.0f}–{RAIL_PUBLIC_DAILY_KM_HIGH:.0f} km/day**. The PowerPack uses modular fuel cells, H2 tanks and batteries,
        with regenerative braking stored in the traction batteries.

        Sources:  
        - https://www.stadlerrail.com/en/solutions/rolling-stock/mainline-flirt-h2  
        - https://www.stadlerrail.com/en/solutions/references/flirt-h2-sbcta  
        - https://www.stadlerrail.com/api/docs/x/cede610cde/flirt-h2_sbcta_en.pdf

        **Fuel-cell efficiency context**  
        A U.S. DOE hydrail workshop presentation cites typical duty-cycle primary-powertrain fuel-cell system efficiency around **45% and higher possible**,
        with additional fuel reduction possible from regenerative braking. This is used only to motivate the editable default, not as a Stadler specification.

        Source:  
        - https://www.energy.gov/documents/fcto-h2-rail-workshop-2019-hoffrichterpdf

        **First-order equations**  
        `F_roll = m g Crr`  
        `F_aero = 0.5 rho CdA v^2`  
        `E_accel = 0.5 m v^2`  
        `E_climb = m g h`  
        `H2 = E_DC / (eta_FC * LHV_H2)`  
        `HPRS-W depot energy = H2_delivered * HPRS-W external energy per delivered kg H2`
        """
    )


st.markdown("---")
st.markdown('<span id="horg-references" class="horg-section-anchor"></span>', unsafe_allow_html=True)
with st.expander("Full scientific comparison, automotive hypotheses and references", expanded=False):
    st.subheader("V3.3 Scientific Comparison — Same Net Shaft Power")

    st.caption(
        f"All four pathways below are normalized to the same useful mechanical output: "
        f"{comparison_net_kw:.0f} kW net shaft. HPRS-W uses external electricity/heat rather than gasoline."
    )

    n1, n2, n3, n4 = st.columns(4)
    n1.metric(
        "Conventional gasoline",
        f"{norm_conv_l_per_kwh:.3f} L/kWh net",
        delta=None,
    )
    n2.metric(
        "Dry HPRS",
        (
            f"{norm_dry_l_per_kwh:.3f} L/kWh net"
            if math.isfinite(norm_dry_l_per_kwh) else "Not self-sustaining"
        ),
        delta=None,
    )
    n3.metric(
        "Gasoline + steam",
        (
            f"{norm_steam_l_per_kwh:.3f} L/kWh net"
            if math.isfinite(norm_steam_l_per_kwh) else "Not self-sustaining"
        ),
        delta=None,
    )

    n4.metric(
        "HPRS-W water splitting",
        f"{norm_hprsw_electric_per_kwh:.2f} kWh_e/kWh net",
        delta=None,
    )

    st.dataframe(
        {
            "Normalized metric": [
                "Net shaft basis",
                "Gasoline consumption",
                "H₂ delivered to engine",
                "Make-up water",
                "Process electricity",
                "External process heat",
                "Fuel-to-net-shaft efficiency",
                "Total-energy-to-net efficiency",
                "Carbon / CO₂ indicator",
                "Solid carbon captured",
                "Operating cost",
            ],
            "Conventional gasoline ICE": [
                f"{comparison_net_kw:.0f} kW net",
                f"{norm_conv_l_per_kwh:.3f} L/kWh net",
                "0 kg/kWh net",
                "0 L/kWh net",
                "0 kWh_e/kWh net",
                "0 kWh_th/kWh net",
                f"{100*norm_conv_total_eff:.1f}%",
                f"{100*norm_conv_total_eff:.1f}%",
                f"{norm_conv_co2_per_kwh:.3f} kg CO₂/kWh net",
                "0 kg/kWh net",
                f"CHF {norm_conv_cost_per_kwh:.3f}/kWh net",
            ],
            "Dry HPRS carbon-retention": [
                f"{comparison_net_kw:.0f} kW net",
                (
                    f"{norm_dry_l_per_kwh:.3f} L/kWh net"
                    if math.isfinite(norm_dry_l_per_kwh) else "Not self-sustaining"
                ),
                (
                    f"{norm_dry_h2_per_kwh:.4f} kg/kWh net"
                    if math.isfinite(norm_dry_h2_per_kwh) else "—"
                ),
                "0 L/kWh net",
                (
                    f"{norm_dry_electric_per_kwh:.3f} kWh_e/kWh net"
                    if math.isfinite(norm_dry_electric_per_kwh) else "—"
                ),
                "Not modeled in this route",
                (
                    f"{100*norm_dry_total_eff:.1f}%"
                    if math.isfinite(norm_dry_fuel_kg_h) else "—"
                ),
                (
                    f"{100*norm_dry_total_eff:.1f}%"
                    if math.isfinite(norm_dry_fuel_kg_h) else "—"
                ),
                (
                    f"{norm_dry_uncaptured_co2_potential_per_kwh:.3f} kg CO₂/kWh net "
                    "uncaptured-C oxidation potential"
                    if math.isfinite(norm_dry_uncaptured_co2_potential_per_kwh) else "—"
                ),
                (
                    f"{norm_dry_captured_c_per_kwh:.3f} kg C/kWh net"
                    if math.isfinite(norm_dry_captured_c_per_kwh) else "—"
                ),
                (
                    f"CHF {norm_dry_cost_per_kwh:.3f}/kWh net"
                    if math.isfinite(norm_dry_cost_per_kwh) else "—"
                ),
            ],
            "Gasoline + steam route": [
                f"{comparison_net_kw:.0f} kW net",
                (
                    f"{norm_steam_l_per_kwh:.3f} L/kWh net"
                    if math.isfinite(norm_steam_l_per_kwh) else "Not self-sustaining"
                ),
                (
                    f"{norm_steam_h2_per_kwh:.4f} kg/kWh net"
                    if math.isfinite(norm_steam_h2_per_kwh) else "—"
                ),
                (
                    f"{norm_steam_water_l_per_kwh:.3f} L/kWh net"
                    if math.isfinite(norm_steam_water_l_per_kwh) else "—"
                ),
                (
                    f"{norm_steam_electric_per_kwh:.3f} kWh_e/kWh net"
                    if math.isfinite(norm_steam_electric_per_kwh) else "—"
                ),
                (
                    f"{norm_steam_thermal_external_per_kwh:.3f} kWh_th/kWh net"
                    if math.isfinite(norm_steam_thermal_external_per_kwh) else "—"
                ),
                (
                    f"{100*norm_steam_fuel_eff:.1f}%"
                    if math.isfinite(norm_steam_fuel_kg_h) else "—"
                ),
                (
                    f"{100*norm_steam_total_eff:.1f}%"
                    if math.isfinite(norm_steam_fuel_kg_h) else "—"
                ),
                norm_steam_carbon_metric,
                "0 kg/kWh net in selected ideal steam chemistry",
                (
                    f"CHF {norm_steam_cost_per_kwh:.3f}/kWh net"
                    if math.isfinite(norm_steam_cost_per_kwh) else "—"
                ),
            ],
            "HPRS-W plasma water splitting": [
                f"{comparison_net_kw:.0f} kW net",
                "0 L/kWh net",
                f"{norm_hprsw_h2_per_kwh:.4f} kg/kWh net",
                f"{norm_hprsw_water_l_per_kwh:.3f} L/kWh net",
                f"{norm_hprsw_electric_per_kwh:.3f} kWh_e/kWh net",
                f"{norm_hprsw_thermal_external_per_kwh:.3f} kWh_th/kWh net",
                "N/A — no gasoline fuel",
                f"{100*norm_hprsw_total_eff:.1f}%",
                "0 kg direct CO₂/kWh net (electricity lifecycle not modeled)",
                "0 kg solid C/kWh net",
                f"CHF {norm_hprsw_cost_per_kwh:.3f}/kWh net",
            ],
        },
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>How to read V3.3:</b><br>
        • Conventional gasoline is the reference at the same {comparison_net_kw:.0f} kW net.<br>
        • Dry HPRS includes its onboard plasma electrical burden through increased fuel demand.
          The displayed electrical value is the remaining plasma electricity after the selected
          recovered-energy offset; it is <b>not added again to cost</b>, avoiding double counting.<br>
        • The steam route includes electrical auxiliaries as onboard parasitic load, while thermal
          process demand is reported separately. Only unrecovered thermal demand is included in the
          total-energy efficiency, and it affects cost only if a non-zero thermal-energy price is entered.<br>
        • In pulsed-plasma mode, the normalized Dry-HPRS result assumes the current effective
          kWh/kg H₂ scales locally with hydrogen throughput; that scaling must be validated experimentally.
        • HPRS-W assumes externally supplied electricity/heat. Direct CO₂ is zero in the modeled reaction,
          but lifecycle emissions depend on how that electricity and heat are produced. Its O₂ coproduct
          is reported separately and receives no economic credit unless a non-zero O₂ value is entered.<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Current operating-point costs (non-normalized)"):
        st.write(
            f"Conventional gasoline: CHF {conventional_fuel_cost_chf_h:.2f}/h at "
            f"{gross_engine_kw:.1f} kW gross shaft."
        )
        st.write(
            f"Dry HPRS fuel: CHF {dry_hprs_fuel_cost_chf_h:.2f}/h at "
            f"{net_shaft_kw:.1f} kW net after plasma burden."
        )
        st.write(
            f"Steam route fuel + water: CHF "
            f"{(steam_fuel_cost_chf_h + steam_water_cost_chf_h):.2f}/h at "
            f"{steam_net_shaft_kw:.1f} kW net, excluding any priced supplemental heat."
        )
        if thermal_energy_price_chf_kwh > 0:
            st.write(
                f"Steam supplemental thermal cost: CHF {steam_thermal_cost_chf_h:.2f}/h."
            )
        st.write(
            f"HPRS-W normalized external electricity at {comparison_net_kw:.0f} kW net: "
            f"{norm_hprsw_electric_kw:.1f} kW_e; external process heat: "
            f"{norm_hprsw_thermal_external_kw:.1f} kW_th."
        )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Steam-route chemistry in the selected model:</b><br>
        {
            "C₈H₁₈ + 16 H₂O → 8 CO₂ + 25 H₂"
            if steam_route == "Steam reforming + WGS"
            else "C₈H₁₈ + 8 H₂O → 8 CO + 17 H₂"
        }<br><br>
        Ideal H₂ yield: <b>{steam_h2_yield_kg_per_kg_fuel:.3f} kg H₂/kg fuel</b>.<br>
        Stoichiometric gross water feed:
        <b>{steam_water_kg_per_kg_fuel:.3f} kg H₂O/kg fuel</b> before any recycle.<br>
        The thermal and electrical process inputs are separated in V3.3. The reaction-enthalpy
        reference is only an ideal thermodynamic reference and does not represent complete hardware losses.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if steam_route == "Steam reforming + WGS":
        st.warning(
            "The steam + WGS route increases hydrogen yield because part of the hydrogen "
            "comes from water, but it converts the fuel carbon primarily to CO₂. "
            "It is therefore not a solid-carbon-retention pathway unless a separate CO₂ "
            "capture/conversion stage is added."
        )
    else:
        st.warning(
            "The syngas route avoids full conversion to CO₂ in this simplified reaction, "
            "but produces substantial CO. CO is toxic and must be shifted, oxidized, "
            "separated or otherwise handled before any vehicle exhaust claim can be made."
        )

    st.subheader("Hypothesis 1 — Conventional Gasoline Engine Benchmark")
    st.caption("Same fuel reference. Same engine-scale comparison. Different carbon pathway.")

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Conventional efficiency", f"{100*conventional_eff:.0f}%")
    b2.metric(
        "Gasoline for same gross shaft",
        f"{conv_same_gross_fuel_kg_h:.1f} kg/h",
        f"{conv_same_gross_fuel_l_h:.1f} L/h",
    )
    b3.metric(
        "Theoretical CO₂ at same gross shaft",
        f"{conv_same_gross_co2_kg_h:.1f} kg/h",
    )
    b4.metric(
        "HPRS / conventional net efficiency",
        f"{(hprs_net_eff/conventional_eff):.2f}×",
    )

    st.dataframe(
        {
            "Metric": [
                "Power basis",
                "Fuel flow",
                "Fuel volume",
                "Reference fuel-to-shaft efficiency",
                "Direct complete-oxidation CO₂",
                "Captured solid carbon",
                "Plasma equivalent shaft burden",
            ],
            "Conventional gasoline ICE": [
                f"{gross_engine_kw:.1f} kW gross shaft",
                f"{conv_same_gross_fuel_kg_h:.2f} kg/h",
                f"{conv_same_gross_fuel_l_h:.2f} L/h",
                f"{100*conventional_eff:.1f}%",
                f"{conv_same_gross_co2_kg_h:.2f} kg/h",
                "0 kg/h",
                "0 kW",
            ],
            "HPRS Automotive": [
                f"{net_shaft_kw:.1f} kW net after plasma",
                f"{fuel_kg_h:.2f} kg/h",
                f"{fuel_l_h:.2f} L/h",
                f"{100*hprs_net_eff:.1f}%",
                "Not calculated as tailpipe CO₂",
                f"{carbon_captured_kg_h:.2f} kg/h",
                f"{shaft_draw_for_plasma_kw:.2f} kW",
            ],
        },
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        f"""
        <div class="horg-note">
        <b>Same-net-power comparison:</b><br>
        HPRS currently leaves <b>{same_net_target_kw:.1f} kW</b> net shaft power.
        A conventional gasoline engine at {100*conventional_eff:.0f}% brake efficiency
        would require about <b>{conv_same_net_fuel_kg_h:.2f} kg/h</b>
        ({conv_same_net_fuel_l_h:.2f} L/h) to deliver the same useful shaft output,
        corresponding to about <b>{conv_same_net_co2_kg_h:.2f} kg/h</b>
        theoretical complete-oxidation CO₂ for the n-octane surrogate.<br><br>
        Under the selected assumptions HPRS uses
        <b>{fuel_ratio_same_net:.2f}×</b> the fuel mass of that same-net-power
        conventional benchmark.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Hypothesis 2 — Dry HPRS Carbon-Retention Interpretation")
    r1, r2, r3 = st.columns(3)
    r1.metric("Carbon collection", f"{carbon_capture*100:.0f}%")
    r2.metric("Captured carbon", f"{carbon_captured_kg_h:.1f} kg/h")
    r3.metric("Uncaptured-C oxidation potential", f"{uncaptured_c_oxidation_potential_kg_h:.1f} kg CO₂/h")

    st.markdown(
        """
        <div class="horg-callout">
        <b>Scientific boundary:</b> this model does not calculate NOₓ, transient reactor behavior,
        catalyst/electrode life, carbon morphology, soot filtration, startup energy, safety systems,
        fuel impurities, compressor demand, hydrogen-purity specifications, thermal-management hardware,
        lifecycle emissions or regulatory compliance. Hydrogen combustion with air can still form NOₓ.
        A real claim of “non-polluting” operation therefore requires measured emissions and independent validation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Model basis and references"):
        st.markdown(
            f"""
            **Stoichiometric model**  
            `C8H18 → 8 C(s) + 9 H2`

            Ideal n-octane surrogate yield: **{H2_KG_PER_KG_FUEL_IDEAL:.3f} kg H₂** and
            **{C_KG_PER_KG_FUEL_IDEAL:.3f} kg solid carbon** per kg fuel.

            **Reference constants**
            - NIST Chemistry WebBook, n-octane: standard liquid enthalpy of formation ≈ **−250 kJ/mol**.
              This gives a standard-state decomposition floor of ≈ **{THERMO_MIN_KWH_PER_KG_H2:.2f} kWh/kg H₂**.
            - U.S. Department of Energy: hydrogen LHV = **33.3 kWh/kg H₂**.

            **Design-target diagnosis**

            The V3.3 design diagnosis varies one lever at a time and solves the
            simplified balance backwards for the selected net-power target.
            It can estimate the required gross engine power, H₂-engine efficiency,
            recovered-energy offset, or plasma specific electricity. A value being
            mathematically reachable in the model is not evidence that the required
            hardware performance is experimentally achievable.

            **V3.3 four-pathway same-net-power normalization**

            The primary comparison rescales all four pathways to the same selected net shaft power.  
            Dry-HPRS plasma electricity is treated as an onboard parasitic load.  
            Steam-route thermal demand and electrical auxiliaries are reported separately.  
            Unrecovered process heat is included in total-energy efficiency but is priced only when a thermal-energy price is entered.

            **Steam-assisted comparison**

            Two idealized n-octane references are available:

            `C8H18 + 8 H2O -> 8 CO + 17 H2`

            and, after complete water-gas shift:

            `C8H18 + 16 H2O -> 8 CO2 + 25 H2`

            The steam route increases hydrogen yield because water supplies additional
            hydrogen atoms. In the complete-WGS case, however, the fuel carbon becomes
            CO2 rather than retained solid carbon. The process-energy input and heat
            recovery are editable scenario assumptions.

            **Pulsed-plasma interpretation**  
    `P_avg = energy_per_pulse × pulse_frequency × active_cells`  
    Pulse width is used to estimate instantaneous peak power and electrical duty cycle. These values are research controls, not validated automotive reactor specifications.

    **Boundary:** gasoline is a mixture. n-octane is only a transparent first surrogate;
            real fuel requires species-resolved chemistry and laboratory data.
            """
        )

    with st.expander("HPRS-W model basis and benchmark references"):
        st.markdown(
            f"""
            **Architecture source used for this model**

            The supplied HTPR-QS diagram proposes: steam preheat/vaporization, argon mixing,
            a high-temperature plasma core, DC-field species separation, rapid quench,
            H₂/O₂ separation, heat recovery and steam recirculation. The diagram's stated
            performance values are treated as **targets/assumptions**, not measured validation data.

            **Stoichiometry**

            `2 H2O -> 2 H2 + O2`

            - minimum water consumed: **{WATER_KG_PER_KG_H2_STOICH:.3f} kg/kg H₂**
            - ideal oxygen coproduct: **{O2_KG_PER_KG_H2_STOICH:.3f} kg/kg H₂**

            **External benchmark guideposts (U.S. DOE 2026 system targets)**

            - PEM electrolysis: **{DOE_PEM_2026_SYSTEM_KWH_KG_H2:.0f} kWh_e/kg H₂** system energy
            - high-temperature electrolysis: **{DOE_HTE_2026_ELECTRIC_KWH_KG_H2:.0f} kWh_e/kg H₂** electrical
            - high-temperature electrolysis: **{DOE_HTE_2026_TOTAL_KWH_KG_H2:.0f} kWh/kg H₂** total energy

            References:
            - https://www.energy.gov/cmei/fuels/technical-targets-proton-exchange-membrane-electrolysis
            - https://stage.energy.gov/cmei/fuels/technical-targets-high-temperature-electrolysis

            **V3.3 plasma-catalysis / RF research references**

            - Li et al., *Journal of Cleaner Production* 387 (2023) 135913: H₂O/Ar non-thermal plasma water splitting with catalyst packing; optimized 0.2 wt.% Au/(10 wt.% TiO₂/SBA-15) is reported as a strong performance-improvement case. V3.3 does **not** convert that published rate improvement into an automatic energy credit.
            - ACS Catalysis 2024 review, DOI 10.1021/acscatal.3c05434: plasma hydrogen production depends on discharge power/frequency, SEI, flow, reactor geometry and catalyst properties; system input power exceeds plasma discharge power because auxiliaries and matching losses matter.
            - ITU-R ISM guideposts: 13.56, 27.12 and 40.68 MHz are standard ISM centre frequencies. V3.3 treats them as selectable engineering carriers, not performance optima.

            **V3.3 standard-state thermodynamic references**

            NIST-JANAF water(l), 298.15 K, 1 bar:
            - reaction Gibbs requirement: **{WATER_SPLIT_REV_KWH_PER_KG_H2:.2f} kWh/kg H₂**
            - reaction enthalpy / thermoneutral reference: **{WATER_SPLIT_THERMONEUTRAL_KWH_PER_KG_H2:.2f} kWh/kg H₂**
            - corresponding reversible voltage: **{WATER_SPLIT_REV_VOLTAGE_V:.3f} V**
            - corresponding thermoneutral voltage: **{WATER_SPLIT_THERMONEUTRAL_VOLTAGE_V:.3f} V**

            References:
            - https://janaf.nist.gov/tables/H-063.html
            - https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/46676.pdf

            **V3.3 advanced diagnostic boundary**

            E/N uses an ideal-gas bulk number density. Ion drift uses a user-supplied effective mobility.
            Quench survival uses an optional first-order lumped timescale. Reactor volume is inferred from
            ideal-gas flow × residence time. The V3.3 feasible-region solver then scans coupled values of
            plasma electricity, total H₂ recovery, H₂-engine efficiency and heat recovery. It rejects points
            that fail the standard-state ΔH energy guard or the simple ΔG exergy guard before comparing them
            with the conventional gasoline efficiency and operating-cost benchmarks. Grid fractions are
            deterministic search results, not probabilities. These remain screening equations only; V3.3
            still does not solve non-equilibrium plasma kinetics, electron-energy distributions, sheath physics,
            detailed CFD, electrode erosion, radiative heat transfer, membrane selectivity, H₂/O₂ flammability
            management, startup energy or transient vehicle dynamics. The V3.3 rail extension adds a first-order
            regional-train mission model but does not replace OEM route simulation or rail homologation analysis.
            """
        )

    st.caption("HPRS Automotive + Rail V3.3.6 · renewable rail-depot H₂ + Pareto + prototype target · Simulation → laboratory validation → proof of concept")
