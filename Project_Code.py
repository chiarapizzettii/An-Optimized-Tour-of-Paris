from pyomo.environ import *
import math
import json
import pandas as pd
import folium

# ─────────────────────────────────────────
# 1. DATA FROM EXCEL
# ─────────────────────────────────────────

try:
    df_excel = pd.read_excel("dati_parigi.xlsx")
except FileNotFoundError:
    print("Error: 'dati_parigi.xlsx' not found.")
    exit()

def time_to_min(time_str):
    h, m = map(int, str(time_str).split(':'))
    return h * 60 + m

def min_to_time(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"

p        = {0: 0, 10: 0}
s        = {0: 0, 10: 0}
a        = {0: 0, 10: 0}
b        = {0: 1440, 10: 1440}
Ticket_M = {0: 0, 10: 0}
labels   = {0: "Hotel (Louvre)", 10: "Return Hotel"}

for _, row in df_excel.iterrows():
    idx           = int(row['ID'])
    p[idx]        = int(row['Score'])
    s[idx]        = int(row['Visiting_Time'])
    a[idx]        = time_to_min(row['Opening'])
    b[idx]        = time_to_min(row['Closing'])
    Ticket_M[idx] = float(row['Ticket_M'])
    labels[idx]   = row['Name']

osm_to_node = {row['Name']: int(row['ID']) for _, row in df_excel.iterrows()}

# ─────────────────────────────────────────
# 2. COORDINATE FROM GEOJSON (Open Street Map)
# ─────────────────────────────────────────

lat = {0: 48.8631, 10: 48.8631}
lon = {0: 2.3358, 10: 2.3358}

with open("export.geojson", "r", encoding="utf-8") as f:
    geojson = json.load(f)

for feature in geojson["features"]:
    name = feature["properties"].get("name", "")
    if not name:
        continue
    for osm_name, node_idx in osm_to_node.items():
        if osm_name.lower() in name.lower() or name.lower() in osm_name.lower():
            if node_idx not in lat:
                coords = feature["geometry"]["coordinates"]
                lat[node_idx] = coords[1]
                lon[node_idx] = coords[0]
                print(f"  Matched: '{name}' → nodo {node_idx} ({labels[node_idx]})")
            break

nodes = sorted(labels.keys())
for i in nodes:
    if i not in lat:
        raise ValueError(f"Missing coordinates for node {i} ({labels[i]}). Check the GeoJSON!")

# ─────────────────────────────────────────
# 3. TRAVEL TIME AND PARAMETERS
# ─────────────────────────────────────────

T_PARTENZA    = 480    # 08:00
Tmax          = 600    # 10 hours tour
Cmax          = 100.0  # total budget (€)
Ticket        = 2.55   # ticket metro (€)
SOGLIA_WALK   = 30     # minutes threshold for walking vs metro, below 30 min walk, above 30 min metro

time_walk  = {}
time_metro = {}
for i in nodes:
    for j in nodes:
        d = math.sqrt((lat[i]-lat[j])**2 + (lon[i]-lon[j])**2) * 111
        time_walk[i,j]  = d * 12
        time_metro[i,j] = d * 3 + 5

M_time = T_PARTENZA + Tmax + max(s.values()) + max(time_metro[i,j] for i in nodes for j in nodes if i != j)
M_cost = Cmax + max(Ticket_M.values()) + Ticket
print(f"\nM_time={M_time:.1f}, M_cost={M_cost:.1f}\n")

# ─────────────────────────────────────────
# 4. PYOMO MODEL
# ─────────────────────────────────────────

model   = ConcreteModel()
model.I = Set(initialize=nodes)
model.V = Set(initialize=[i for i in nodes if i not in [0, 10]])

model.x = Var(model.I, model.I, domain=Binary)       # arc by foot
model.y = Var(model.I, model.I, domain=Binary)       # arc by metro
model.u = Var(model.I, domain=NonNegativeReals)      # arrival time (min from midnight)
model.c = Var(model.I, domain=NonNegativeReals)      # cumulative cost (€) 

model.obj = Objective(
    expr=sum(
        p[i] * sum(model.x[i,j] + model.y[i,j] for j in model.I if j != i)
        for i in model.V
    ),
    sense=maximize
)

model.cons = ConstraintList()

# ── flow constraints ──
model.cons.add(sum(model.x[0,j] + model.y[0,j] for j in model.I if j != 0) == 1)
model.cons.add(sum(model.x[i,10] + model.y[i,10] for i in model.I if i != 10) == 1)

for k in model.V:
    in_flow  = sum(model.x[i,k] + model.y[i,k] for i in model.I if i != k)
    out_flow = sum(model.x[k,j] + model.y[k,j] for j in model.I if j != k)
    model.cons.add(in_flow == out_flow)
    model.cons.add(in_flow <= 1)

# ── foot vs metro ──         
for i in model.I:
    for j in model.I:
        if i != j:
            # for each arc consider the possibility of walking or taking the metro, but not both
            model.cons.add(model.x[i,j] + model.y[i,j] <= 1)

            if time_walk[i,j] <= SOGLIA_WALK:
                model.cons.add(model.y[i,j] == 0)
            else:
                model.cons.add(model.x[i,j] == 0)

# ── travel time constraints ──
model.cons.add(model.u[0] == T_PARTENZA)
model.cons.add(model.u[10] - model.u[0] <= Tmax)

for i in model.I:
    for j in model.I:
        if i != j:
            model.cons.add(
                model.u[j] >= model.u[i] + s[i]
                + time_walk[i,j]  * model.x[i,j]
                + time_metro[i,j] * model.y[i,j]
                - M_time * (1 - (model.x[i,j] + model.y[i,j]))
            )

# ── TW constraints ──
for i in model.V:
    model.cons.add(model.u[i] >= a[i])
    model.cons.add(model.u[i] + s[i] <= b[i])

# ── economic constraints ──
model.cons.add(model.c[0] == 0)

for i in model.I:
    for j in model.I:
        if i != j:
            arco    = model.x[i,j] + model.y[i,j]
            c_metro = Ticket      * model.y[i,j]
            c_museo = Ticket_M[j] * arco
            model.cons.add(
                model.c[j] >= model.c[i] + c_metro + c_museo - M_cost * (1 - arco)
            )

model.cons.add(model.c[10] <= Cmax)

# ─────────────────────────────────────────
# 5. SOLUTION
# ─────────────────────────────────────────
opt = SolverFactory('glpk')
print("\nStarting GLPK solver...")

results = opt.solve(model, tee=True, timelimit=180, options={'mipgap': 0.15}) 

# ─────────────────────────────────────────
# 6. OUTPUT
# ─────────────────────────────────────────

feasible = results.solver.termination_condition in [
    TerminationCondition.optimal,
    TerminationCondition.maxTimeLimit,
    TerminationCondition.feasible,
]

if feasible and value(model.obj) > 0:
    costo_totale   = value(model.c[10])
    costo_ingressi = sum(
        Ticket_M[i]
        for i in model.V
        for j in nodes
        if i != j and (value(model.x[i,j]) or 0) + (value(model.y[i,j]) or 0) > 0.5
    )
    costo_metro_val = costo_totale - costo_ingressi

    print(f"\n{'='*60}")
    print(f"OPTIMIZED TOUR IN PARIS")
    print(f"  Total score : {value(model.obj):.0f} pt")
    print(f"  Metro cost      : {costo_metro_val:.2f} €")
    print(f"  POI cost   : {costo_ingressi:.2f} €")
    print(f"  Total cost     : {costo_totale:.2f} € / {Cmax:.0f} € budget")
    print(f"  Time           : {min_to_time(value(model.u[0]))} → {min_to_time(value(model.u[10]))}")
    print(f"{'='*60}") # to obtain time in hours

    # Reconstruct the path
    percorso = []
    nodo_corrente = 0
    visitati = set()
    while nodo_corrente != 10:
        if nodo_corrente in visitati:
            print(" Loop rilevato nel percorso")
            break
        visitati.add(nodo_corrente)
        trovato = False
        for j in nodes:
            if j == nodo_corrente:
                continue
            xv = value(model.x[nodo_corrente, j]) or 0
            yv = value(model.y[nodo_corrente, j]) or 0
            if xv > 0.5 or yv > 0.5:
                modo  = "BY FOOT" if xv > 0.5 else "METRO"
                tempo = time_walk[nodo_corrente,j] if xv > 0.5 else time_metro[nodo_corrente,j]
                percorso.append((nodo_corrente, j, modo, tempo))
                nodo_corrente = j
                trovato = True
                break
        if not trovato:
            break

    for (i, j, modo, tempo) in percorso:
        ticket_str = f" | Ticket: {Ticket_M[j]:.0f}€" if Ticket_M.get(j, 0) > 0 else ""
        print(
            f"  {labels[i]:<28} → {labels[j]:<28}"
            f" | {modo} ({tempo:.0f} min)"
            f" | Arrival: {min_to_time(value(model.u[j]))}"
            f"{ticket_str}"
        )
else:
    print("\n Nessuna soluzione trovata.")
    print(f"   Termination: {results.solver.termination_condition}")

# ─────────────────────────────────────────
# 7. INTTERACTIVE MAP
# ─────────────────────────────────────────

def generate_paris_interactive_map(model):
    paris_map = folium.Map(location=[48.8606, 2.3376], zoom_start=14,
                           tiles='CartoDB positron')

    for i in nodes:
        if i in [0, 10]:
            color, icon_name = 'green', 'home'
        else:
            visited = any(
                (value(model.x[i,j]) or 0) > 0.5 or (value(model.y[i,j]) or 0) > 0.5
                for j in nodes if j != i
            )
            color, icon_name = ('blue', 'info-sign') if visited else ('lightgray', 'remove-circle')

        popup_html = (
            f"<b>{labels[i]}</b><br>"
            f"Interesse: {p[i]} pt<br>"
            f"Durata: {s[i]} min<br>"
            f"Biglietto: {Ticket_M.get(i,0):.0f} €<br>"
            f"Arrivo: {min_to_time(value(model.u[i]))}"
        )
        folium.Marker(
            location=[lat[i], lon[i]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=labels[i],
            icon=folium.Icon(color=color, icon=icon_name)
        ).add_to(paris_map)

    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            xv = value(model.x[i,j]) or 0
            yv = value(model.y[i,j]) or 0
            if xv > 0.5:
                folium.PolyLine(
                    [[lat[i],lon[i]], [lat[j],lon[j]]],
                    color="red", weight=4, opacity=0.85,
                    tooltip=f"A piedi ({time_walk[i,j]:.0f} min)"
                ).add_to(paris_map)
            elif yv > 0.5:
                folium.PolyLine(
                    [[lat[i],lon[i]], [lat[j],lon[j]]],
                    color="blue", weight=4, opacity=0.75,
                    dash_array='8 6',
                    tooltip=f"Metro ({time_metro[i,j]:.0f} min, {Ticket}€)"
                ).add_to(paris_map)

    paris_map.save("Paris_Map.html")
    print("Map saved: 'Paris_Map.html'")

if feasible and value(model.obj) > 0:
    generate_paris_interactive_map(model)