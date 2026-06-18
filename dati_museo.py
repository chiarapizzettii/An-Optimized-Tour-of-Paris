# [out:json][timeout:60];
# (
#   nwr["name"="Musée du Louvre"](48.75,2.2,48.95,2.5);
#   nwr["name"="Musée d'Orsay"](48.75,2.2,48.95,2.5);
#   nwr["name"="Musée de l'Orangerie"](48.75,2.2,48.95,2.5);
#   nwr["name"="Tour Eiffel"](48.75,2.2,48.95,2.5);
#   nwr["name"="Arc de Triomphe"](48.75,2.2,48.95,2.5);
#   nwr["name"="Sacré-Cœur"](48.75,2.2,48.95,2.5);
#   nwr["name"="Opéra Garnier"](48.75,2.2,48.95,2.5);
#   nwr["name"="Notre-Dame de Paris"](48.75,2.2,48.95,2.5);
#   nwr["name"="Musée Rodin"](48.75,2.2,48.95,2.5);
# );
# out center;

import pandas as pd

data = {
    'ID': [1,2,3,4,5,6,7,8,9],
    'Name': [
        "Musée du Louvre", "Musée d'Orsay", "Musée de l'Orangerie", "Tour Eiffel",
        "Arc de Triomphe", "Sacré-Cœur", "Opéra Garnier", "Notre-Dame de Paris",
        "Musée Rodin"
    ],
    'Score': [8, 4, 5, 2, 4, 2, 3, 6, 1],
    'Visiting_Time': [180, 120, 60, 120, 45, 60, 60, 45, 60],
    'Opening': ["09:00", "09:30", "09:00", "09:30", "11:00", "09:00", "10:00", "08:00", "10:00"],
    'Closing': ["18:00", "18:00", "18:00", "23:45", "23:00", "17:00", "17:00", "19:00", "18:30"],
    'Ticket_M': [22, 16, 11, 28, 16, 8, 15, 16, 15]
}

df = pd.DataFrame(data)

df.to_excel("dati_parigi.xlsx", index=False)