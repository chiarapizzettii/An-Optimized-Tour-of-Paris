# 🗺️ Visiting Paris — Multimodal Itinerary Optimizer
A **Mixed-Integer Linear Programming (MILP)** model that generates an optimized
tourist itinerary for Paris, maximizing user satisfaction under time, budget,
and transportation constraints.

Built with **Pyomo** and solved via **GLPK**.

## Problem

Planning a tourist day in Paris is complex: attractions have different opening
hours, entrance fees, and distances between them. This project formulates the
problem as a **Multimodal Orienteering Problem with Time Windows (OPTW)**,
selecting the best subset of Points of Interest (POIs) and sequencing them into
a feasible route that maximizes a user-defined preference score.

## How It Works

- The user assigns a **preference score (1–10)** to each attraction
- The model selects which POIs to visit and in which order
- Transport mode is chosen dynamically:
  - 🚶 **Walking** if travel time ≤ 30 minutes
  - 🚇 **Metro** otherwise (cost: 2.55 €/trip)
- The solution respects:
  - Opening and closing hours of each attraction
  - Maximum tour duration (default: 10 hours)
  - Maximum total budget (default: 100 €)
 
## How to Run

**Step 1** — Generate the Excel data file:

```bash
python dati_museo.py
```

**Step 2** — Download `export.geojson` from [OpenStreetMap / Overpass API](https://overpass-turbo.eu/)
using the query provided at the top of `dati_museo.py`, and place it in the
project folder.

**Step 3** — Run the optimizer:

```bash
python Project_Code.py
```

## Authors

Marzia Comincini · Chiara Pizzetti · Karina Trelles

Supervised by Prof. Claudia Archetti and Prof. Valentina Morandi —
*Università degli Studi di Brescia*
 

