# HydrogenOrg HPRS Rail Research Simulator V1.0

Dedicated Streamlit research simulator for the rail application of HPRS-W.

## Purpose

The model compares three rail energy pathways for the same user-selected mission:

1. Direct electric / catenary reference
2. Delivered hydrogen + fuel-cell/battery hybrid
3. Depot HPRS-W hydrogen production + fuel-cell/battery hybrid

It also performs an onboard HPRS-W loop-closure diagnostic.

## Scientific boundary

This is a first-order research/scenario model. It is not a homologation-grade train dynamics model and does not represent validated reactor performance.

## Repository files

- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `.streamlit/config.toml` — HydrogenOrg light theme
- `assets/hprs_rail_hero.png` — rail + reactor concept visual
- `assets/reactor_v4.png` — reactor concept image
- `assets/plasma_water_splitting.png` — process architecture image

## Streamlit Cloud deployment

Create a **new Streamlit app** for this repository rather than replacing the Automotive app.

Suggested repository name: `hprs-rail`

Main file path: `app.py`

## Important

Public Stadler rail data shown in the app are contextual guideposts only. They are not used to infer proprietary train mass, H2 storage, fuel-cell rating, battery capacity or detailed duty-cycle data.
