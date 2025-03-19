# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 13:53:32 2025

@author: above
"""

import streamlit as st
from fusion_solar_py.client import FusionSolarClient
import matplotlib.pyplot as plt
import pickle
import requests
import datetime
import pandas as pd
import numpy as np
import time
from streamlit_autorefresh import st_autorefresh

ss = st.session_state

# Configuració de la pàgina de Streamlit
st.set_page_config(page_title="Dashboard Fotovoltaic", layout="wide")
count = st_autorefresh(interval=20 * 1000, key="dataframerefresh")
print(count)


st.title("📊 Dashboard Fotovoltaic - Consell Comarcal")

def clean_data(data):
    df = pd.DataFrame(data, columns=["values"])
    df["values"] = pd.to_numeric(df["values"], errors='coerce')
    return df


def actualitza_df_energia():
    # Inicialitzem la variable si no existeix
    if 'df_power' not in ss:
        ss.df_power = pd.DataFrame()
    if 'df_energy' not in ss:
        ss.df_energy = pd.DataFrame()
    
    dies = dates_cerca()
    
    for dia in dies:
        print(1)
        # get the data for the first plant
        segons = round(time.mktime(dia) * 1000)
        plant_data = client.get_plant_stats(plant_ids[0],segons)
        
        # Creem un df amb les corbes de consum i generació
        p_generacio = clean_data(plant_data['productPower'])
        p_consum = clean_data(plant_data['usePower'])
        dates = pd.DataFrame(plant_data['xAxis'], columns=["values"])
        
        df_power = pd.concat([dates, p_generacio, p_consum], axis=1)
        df_power.columns = ["dates", "p_generacio", "p_consum"]
        # Convertir la columna "dates" a tipus datetime
        df_power["dates"] = pd.to_datetime(df_power["dates"])
        
        
        # obtenim els consums i generació pel dia en concret
        df_energy = pd.DataFrame({ 
            'dates': [datetime.datetime.fromtimestamp(time.mktime(dia))],
            'generacio_dia' : [plant_data['totalProductPower']],
            'consum_dia' : [plant_data['totalUsePower']],
            'autoconsum_dia' : [plant_data['totalSelfUsePower']],
            'excedents_dia' : [plant_data['totalOnGridPower']],
            'consum_xarxa_dia' : [plant_data['totalBuyPower']]
        })
        
        # Afegim la nova informació a la variable del session_state
        ss.df_power = pd.concat([ss.df_power, df_power], ignore_index=True)
        ss.df_energy = pd.concat([ss.df_energy, df_energy], ignore_index=True)
    
    ss.df_energy.replace("--", np.nan, inplace=True)
    cols_a_convertir = ["generacio_dia", "consum_dia", "autoconsum_dia", "excedents_dia", "consum_xarxa_dia"]
    ss.df_energy[cols_a_convertir] = ss.df_energy[cols_a_convertir].apply(pd.to_numeric, errors="coerce")

    
    return 

def dates_cerca():
    #obtenim un llistat de tots els dies de l'any
    # Obtenir l'any actual
    ara = datetime.datetime.utcnow()
    any_actual = ara.year

    # Generar una llista de dates des de l'1 de gener fins avui
    dies_necessaris = [datetime.datetime(any_actual, 1, 1) + datetime.timedelta(days=i) for i in range((ara - datetime.datetime(any_actual, 1, 1)).days + 1)]

    # Convertir cada data a struct_time
    dies_necessaris_struct_time = [dia.timetuple() for dia in dies_necessaris]
    
    try:
        # Obtenim un llistat de tots els dies de que ja en tenim dades
        dies_tenim = ss.df_power["dates"].dt.date.drop_duplicates().tolist()
        
        # Convertir cada data a struct_time
        dies_tenim_struct_time = [dia.timetuple() for dia in dies_tenim]
    except:
        dies_tenim_struct_time = []
    
    # Convertir les llistes a conjunts per fer l'operació de diferència
    dies_filtrats = list(set(dies_necessaris_struct_time) - set(dies_tenim_struct_time))
    dies_filtrats.sort()
    
    return dies_filtrats



if "sessio" not in ss:
    ss.sessio = requests.Session()
    
# log into the API - with proper credentials...
client = FusionSolarClient(
  st.secrets["huawei_user" ],
  st.secrets["huawei_password"],
  huawei_subdomain="uni002eu5",
  session=ss.sessio
)

print(client.keep_alive())
print(client.is_session_active())


# if you only need an overview of the current status of
# your plant(s) you can use the get_plant_list function
plant_overview1 = client.get_station_list()

# get the current power of your first plant
print(f"Current power production: { plant_overview1[0]['currentPower'] }")

# alternatively, you can get time resolved data for each plant:

# get the plant ids
plant_ids = client.get_plant_ids()

print(f"Found {len(plant_ids)} plants")

# get the basic (current) overview data for the plant
plant_overview = client.get_current_plant_data(plant_ids[0])

print(str(plant_overview))


# get the data for the first plant
plant_data = client.get_plant_stats(plant_ids[0])

#Històric de dades
#omplim el df
actualitza_df_energia()

# Filtrar les files del mes actual i dia
df_energy_mes = ss.df_energy[(ss.df_energy["dates"].dt.month == pd.Timestamp.today().month)]
df_energy_dia = ss.df_energy[(ss.df_energy["dates"].dt.month == pd.Timestamp.today().month)&((ss.df_energy["dates"].dt.day == pd.Timestamp.today().day))]


# plant_data is a dict that contains the complete
# usage statistics of the current day. There is
# a helper function available to extract some
# most recent measurements
last_values = client.get_last_plant_data(plant_data)




stats = client.get_power_status()


# Mostrar KPIs principals
#st.header("📈 KPIs Principals")
col1, col2, col3 = st.columns([1,1,2])

# Potència actual
current_power = stats.current_power_kw
col1.metric("Generació actual (kW)", f"{current_power:.2f}", border=True)

# Generació d'energia avui
today_energy = last_values['totalProductPower']
col1.metric("Energia Avui (kWh)", f"{today_energy:.2f}", border=True)

# Generació mensual d'energia
month_energy = df_energy_mes['generacio_dia'].sum()
col1.metric("Energia mensual (kWh)", f"{month_energy:.2f}", border=True)

# Generació total d'energia
total_energy = ss.df_energy['generacio_dia'].sum()
col1.metric("Energia Total anual (kWh)", f"{total_energy:.2f}", border=True)

# Consum actual
current_consumption = last_values['usePower']['value']
col2.metric("Consum actual (kW)", f"{current_consumption:.2f}", border=True)

# Consum d'energia avui
today_consumption = last_values['totalUsePower']
col2.metric("Consum Avui (kWh)", f"{today_consumption:.2f}", border=True)

# Consum mensual d'energia
month_consumption = df_energy_mes['consum_dia'].sum()
col2.metric("Consum mensual (kWh)", f"{month_consumption:.2f}", border=True)

# Consum total d'energia
anual_consumption = ss.df_energy['consum_dia'].sum()
col2.metric("Consum Total anual (kWh)", f"{anual_consumption:.2f}", border=True)

col1.write(f"Última actualització: {last_values['usePower']['time']}")

col1.write(f"**Nom de l'Estació:** {plant_overview1[0]['name']}")
col1.write(f"**Capacitat Instal·lada:** 54,45 kWp")
# Footer
col1.write("---")
col1.markdown("© 2023 Consell Comarcal - Dades proporcionades per Huawei FusionSolar.")
col1.markdown("© 2022 Johannes Griss - FusionSolarPy")

with col3:
    # Gràfic de generació d'energia diària
    #st.header("📅 Generació Diària d'Energia")
    generacio = clean_data(plant_data['productPower'])
    consum = clean_data(plant_data['usePower'])
    
    
    # Crear el gràfic
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(consum, label="Energia Consumida (kWh)", color="blue")
    ax.plot(generacio, label="Energia Produïda (kWh)", color="green")
    
    # Afegir títols i etiquetes
    ax.set_title("Energia Consumida vs Energia Produïda (Intervals de 5 minuts)")
    ax.set_xlabel("Intervals de 5 minuts")
    ax.set_ylabel("Energia (kWh)")
    ax.legend()
    ax.grid(True)
    
    # Mostrar el gràfic amb Streamlit
    st.pyplot(fig)
    st.image("logo.png", use_container_width=True)
    
col1, col2, col3 = st.columns([1,1,2])

# Informació addicional de l'estació
    #st.header("🏭 Informació de l'Estació")
    


