
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import itertools
import warnings
import yaml
import streamlit as st
warnings.filterwarnings('ignore')

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)


# Read Tables

pokemon_database = pd.read_csv('C:/Users/adria/Downloads/pokemon_data/pokemon_database.csv')

types_chart = pd.read_csv('C:/Users/adria/Downloads/pokemon_data/chart.csv')

df_melted = types_chart.melt(id_vars=["Attacking"], var_name="Defense Type", value_name="Multiplier")

df_melted["Key"] = range(1, len(df_melted) + 1)

types_chart_final = df_melted[["Key", "Attacking", "Defense Type", "Multiplier"]]

with open('C:/Users/adria/Downloads/pokemon_data/moves.yaml', 'r') as file:
    dados_yaml = yaml.safe_load(file)

dados_moves = []

for move, info in dados_yaml.items():
    move_data = {
        'name': info.get('name', ''),
        'type': info.get('type', ''),
        'category': info.get('category', ''),
        'power': info.get('power', ''),
        'accuracy': info.get('accuracy', ''),
        'pp': info.get('pp', ''),
        'priority': info.get('priority', '')
    }
    dados_moves.append(move_data)

df_moves = pd.DataFrame(dados_moves)

# Data Manipulation

pokemon_database = pokemon_database.applymap(lambda x: x.replace('"', '') if isinstance(x, str) else x)

generation_map = {
    'Red': 1, 'Blue': 1, 'Green': 1, 'Yellow': 1,
    'Gold': 2, 'Silver': 2, 'Crystal': 2, 
    'Ruby': 3, 'Sapphire': 3, 'Emerald': 3, 'Fire Red': 3, 'Leaf Green': 3,
    'Diamond': 4, 'Pearl': 4, 'Platinum': 4, 'HeartGold' : 4,  'SoulSilver': 4, 
    'Black': 5, 'White': 5, 'Black 2': 5, 'White 2': 5,
    'X': 6, 'Y': 6, 'Omega Ruby': 6, 'Alpha Sapphire': 6,
    'Sun': 7, 'Moon': 7, 'Ultra Sun': 7, 'Ultra Moon': 7, "Let's Go Pikachu": 7, "Let's Go Eevee": 7, 
    'Sword': 8, 'Shield': 8, 'Brilliant Diamond': 8, 'Shining Pearl': 8, 'Legends Arceus': 8,
    'Scarlet': 9, 'Violet': 9
}

pokemon_database['generation'] = pokemon_database['Game(s) of Origin'].map(generation_map)

df_moves['move_name'] = df_moves['name'].str.replace(' ', '-', regex=False).str.lower()

# Functions

def pegar_move(poke):
    
    dados_moves = []
    
    for i in poke['moves']:
        
        move_name = i['move']['name']
        
        for version_group_detail in i['version_group_details']:
            
            dados_moves.append({
            'move_name': move_name,
            'level_learned_at': version_group_detail['level_learned_at'],
            'move_learn_method': version_group_detail['move_learn_method']['name'],
            'origin': version_group_detail['version_group']['name']
        })
            
        
        df_moves = pd.DataFrame(dados_moves)
        
    return df_moves
        

def moves_pokemon(poke):
    
    pokemon_lower = poke.lower()
    
    api = f'https://pokeapi.co/api/v2/pokemon/{pokemon_lower}'
    
    res = requests.get(api)
    
    if res.status_code == 200:
        poke = res.json()
        
        return pegar_move(poke)
    
    else:
        print("Error fetching Pokémon data.")
        return None
    
## Visualizations

### Pokemon Weakness

def pokemon_types(df, pokemon_name, pokemon_alternate_form=None):
    
    if pokemon_alternate_form:
        
        pokemon_types = df[(df['Pokemon Name']==pokemon_name) & (pokemon_database['Alternate Form Name']==pokemon_alternate_form)][['Primary Type', 'Secondary Type']]
        
        primary_type = pokemon_types.iloc[0]['Primary Type']
        
        secondary_type = pokemon_types.iloc[0]['Secondary Type']
    
    else:
        
        pokemon_types = df[(df['Pokemon Name']==pokemon_name) & (pokemon_database['Alternate Form Name'].isnull())][['Primary Type', 'Secondary Type']]
        
        primary_type = pokemon_types.iloc[0]['Primary Type']
        
        secondary_type = pokemon_types.iloc[0]['Secondary Type']
        
    if pd.isnull(secondary_type):
        
        return [primary_type]
    
    else:
        return [primary_type, secondary_type]
        
        
    return [primary_type, secondary_type]


def weakeness_pokemon(df_type_charts, df_pokemon_database, pokemon_name, pokemon_alternate_form=None):
    
    types = pokemon_types(df_pokemon_database, pokemon_name, pokemon_alternate_form) 

    merged_results = None

    for i, pokemon_type in enumerate(types):

        filtered_data = df_type_charts[df_type_charts['Defense Type'] == pokemon_type].drop(columns=['Key'])

        if i == 0:
            filtered_data = filtered_data.rename(columns={'Defense Type': 'Defense Type (Primary)', 
                                                          'Multiplier': 'Multiplier (Primary)'})

        else:
            filtered_data = filtered_data.rename(columns={'Defense Type': 'Defense Type (Secondary)', 
                                                          'Multiplier': 'Multiplier (Secondary)'})


        if merged_results is None:

            merged_results = filtered_data
            
            merged_results['Weakness'] = merged_results['Multiplier (Primary)']

        else:

            merged_results = pd.merge(merged_results, filtered_data, on='Attacking', how='left')
            
            merged_results['Weakness'] = merged_results['Multiplier (Primary)'] * merged_results['Multiplier (Secondary)']
        
        cols = [col for col in merged_results.columns if col != 'Weakness']
        
        merged_results = merged_results[cols + ['Weakness']]
        
    conditions = [
        (merged_results['Weakness'] == 0),
        (merged_results['Weakness'] == 0.25),
        (merged_results['Weakness'] == 0.5),  
        (merged_results['Weakness'] == 1),
        (merged_results['Weakness'] == 2),
        (merged_results['Weakness'] == 4)
    ]

    categories = ['No Effect', 'Resistant (0.25)', 'Resistant (0.5)', 'Neutral', 'Super Effective (2)', 'Super Effective (4)']

    merged_results['Weakness Category'] = np.select(conditions, categories, default='Unknown')

    df_weakness_category_final = merged_results.groupby('Weakness Category').agg(
            count=('Weakness Category', 'size'),
            Attacking=('Attacking', lambda x: list(x))
        ).reset_index()
    
    return df_weakness_category_final


def bar_plot_weakness_category (df_weakeness_pokemon):
    
    order_list = ['Neutral', 'No Effect', 'Resistant (0.25)', 'Resistant (0.5)', 'Super Effective (2)', 'Super Effective (4)']

    custom_palette = ['#1f77b4', '#d3d3d3', '#2ca02c', '#006400', '#ff6347', '#b22222']

    fig = px.bar(
        df_weakeness_pokemon,
        x='Weakness Category',
        y='count',
        color='Weakness Category',
        title="Weakness Categories",
        labels={'count': 'Count'},
        hover_data={'Attacking'},
        category_orders={'Weakness Category': order_list},
        color_discrete_map={'Neutral': custom_palette[0], 'No Effect': custom_palette[1],
                           'Resistant (0.25)': custom_palette[2], 'Resistant (0.5)': custom_palette[3],
                           'Super Effective (2)': custom_palette[4], 'Super Effective (4)': custom_palette[5]}
    )

    fig.update_layout(
        title={'x': 0.5, 'xanchor': 'center', 'y': 0.95},  
        font=dict(family="Arial", size=14),  
        yaxis=dict(tickformat=".0f", showgrid=True, gridcolor='gray', gridwidth=0.2, title=None), 
        xaxis=dict(title=None),
        plot_bgcolor='white',  
        height=600,  
        width=900,  
    )

    return fig
    
    
### Pokemon Stats

def pokemon_stats(df_pokemon_database, pokemon_name, pokemon_alternate_form=None):
    
    if pokemon_alternate_form:
    
        df = df_pokemon_database[(df_pokemon_database['Pokemon Name']==pokemon_name) & (df_pokemon_database['Alternate Form Name']==pokemon_alternate_form)][['Health Stat', 'Attack Stat', 'Defense Stat', 'Special Attack Stat', 'Special Defense Stat', 'Speed Stat', 'Base Stat Total']]

        df_melted = df.melt(var_name='Stat', value_name='Value')

        df_melted['Stat'] = df_melted['Stat'].str.replace(' Stat$', '', regex=True)
    
    else:
        
        df = df_pokemon_database[(df_pokemon_database['Pokemon Name']==pokemon_name) & (df_pokemon_database['Alternate Form Name'].isnull())][['Health Stat', 'Attack Stat', 'Defense Stat', 'Special Attack Stat', 'Special Defense Stat', 'Speed Stat', 'Base Stat Total']]
        
        df_melted = df.melt(var_name='Stat', value_name='Value')

        df_melted['Stat'] = df_melted['Stat'].str.replace(' Stat$', '', regex=True)
        
    return df_melted


def bar_plot_pokemon_stat (df_pokemon_database, pokemon_name, pokemon_alternate_form=None):
    
    df_pokemon_stat = pokemon_stats(pokemon_database, pokemon_name, pokemon_alternate_form)

    order_list = ['Health', 'Attack', 'Defense', 'Special Attack', 'Special Defense', 'Speed']

    custom_palette = {
        'Health': '#15f50e',           
        'Attack': '#ffeb3b',           
        'Defense': '#f5890e',          
        'Special Attack': '#3c91dc',   
        'Special Defense': '#6d0ef5',  
        'Speed': '#f06292'
    }

    fig = px.bar(
            df_pokemon_stat[df_pokemon_stat['Stat']!='Base Stat Total'],
            x='Value',
            y='Stat',
            title="Stats",
            labels={'count': 'Count'},
            color='Stat',
            category_orders={'Stat': order_list},
            color_discrete_map=custom_palette,
            text='Value'
        )

    fig.update_layout(
            title={'x': 0.5, 'xanchor': 'center', 'y': 0.95},  
            font=dict(family="Arial", size=14),  
            yaxis=dict(title=None, showgrid=False), 
            xaxis=dict(title=None, showticklabels=False),
            plot_bgcolor='white',  
            height=600,  
            width=900,  
        )

    fig.update_traces(textposition='outside')

    fig.show()
    
### Pokemon Moves

def pokemon_all_moves (pokemon_name, origin_game, df_moves_dataset):
    
    df_pokemon_moves = moves_pokemon(pokemon_name) 

    df_pokemon_moves_origin = df_pokemon_moves[df_pokemon_moves['origin']==origin_game]

    df_pokemon_moves_final = df_pokemon_moves_origin.merge(df_moves_dataset[['move_name', 'type', 'category', 'power', 'accuracy', 'pp', 'priority']], on='move_name', how='left')
    
    return df_pokemon_moves_final


def calculate_damage(df):
    
    attack = np.where(df['category'] == 'physical', df['Attack Stat'],
                      np.where(df['category'] == 'special', df['Special Attack Stat'], np.nan))

    stab = np.where((df['type'] == df['Primary Type']) | (df['type'] == df['Secondary Type']), 1.5, 1)

    base_damage = np.where(df['power'].notna(), (df['power'] * attack) * stab, np.nan)

    return base_damage

def best_moves_pokemon (df_pokemon_database, df_moves, pokemon_name, origin, pokemon_alternate_form=None, level_learned_at=None,
                        move_learn_method=None, move_type=None, move_category=None, accuracy=None, move_pp=None):
    
    df_pokemon_all_moves = pokemon_all_moves (pokemon_name, origin, df_moves)
    
    if pokemon_alternate_form:
    
        pokemon_name_database = df_pokemon_database[(df_pokemon_database['Pokemon Name']==pokemon_name)\
                                                  & (df_pokemon_database['Alternate Form Name']==pokemon_alternate_form)]\
                                                    [['Primary Type', 'Secondary Type', 'Health Stat', 'Attack Stat',\
                                                      'Defense Stat', 'Special Attack Stat', 'Special Defense Stat',\
                                                      'Speed Stat', 'Base Stat Total']]
    
    else:
        
        pokemon_name_database = df_pokemon_database[(df_pokemon_database['Pokemon Name']==pokemon_name)\
                                                  & (df_pokemon_database['Alternate Form Name'].isnull())]\
                                                    [['Primary Type', 'Secondary Type', 'Health Stat', 'Attack Stat',\
                                                      'Defense Stat', 'Special Attack Stat', 'Special Defense Stat',\
                                                      'Speed Stat', 'Base Stat Total']]
        
    df_pokemon_all_moves['key'] = 1
    pokemon_name_database['key'] = 1

    df_final = pd.merge(df_pokemon_all_moves, pokemon_name_database, on='key').drop('key', axis=1)                          
    
    df_final['move_damage'] = calcular_dano_vetorizado(df_final)
    
    filtros = []
    
    if level_learned_at is not None:
        filtros.append(df_final['level_learned_at'] >= level_learned_at)
        
    if move_learn_method is not None:
        filtros.append(df_final['move_learn_method'] == move_learn_method)
        
    if move_type is not None:
        filtros.append(df_final['type'] == move_type)
        
    if move_category is not None:
        filtros.append(df_final['category'] == move_category)
        
    if accuracy is not None:
        filtros.append(df_final['accuracy'] >= accuracy)
        
    if move_pp is not None:
        filtros.append(df_final['pp'] >= move_pp)
    
    if filtros:
        df_final = df_final[np.logical_and.reduce(filtros)]
        
    
    df_final = df_final[['move_name', 'move_damage', 'level_learned_at', 'move_learn_method', 'origin', 'type',
                         'category', 'power', 'accuracy', 'pp', 'priority']]
    
    df_final = df_final.sort_values(by='move_damage', ascending=False).reset_index(drop=True)
    
    return df_final


######################################################################

# Title of the app
st.title("Pokemón Database")

# Escolher o Pokémon
pokemon_names = pokemon_database['Pokemon Name'].unique()

# Filtro para selecionar o Pokémon
pokemon_chosen = st.selectbox("Choose a pokemon:", pokemon_names)

# Filtrar os dados com base no Pokémon escolhido
df_pokemon = pokemon_database[pokemon_database['Pokemon Name'] == pokemon_chosen]

# Obter as opções de "Alternate Form Name" com base no Pokémon escolhido
alternate_form_names = df_pokemon['Alternate Form Name'].dropna().unique()

# Adicionar uma opção para "None" (nenhum formulário alternativo)
alternate_form_names = ['None'] + list(alternate_form_names)

# Filtro para escolher o formulário alternativo
pokemon_alternate_form = st.selectbox("Choose the alternate form name:", alternate_form_names)

# Exibir as escolhas
st.write(f"Você escolheu o Pokémon: {pokemon_chosen}")
st.write(f"Formulário alternativo selecionado: {pokemon_alternate_form}")

if pokemon_alternate_form == 'None':

    st.dataframe(weakeness_pokemon(types_chart_final, pokemon_database, pokemon_chosen, None))
    
else:
    
    st.dataframe(weakeness_pokemon(types_chart_final, pokemon_database, pokemon_chosen, pokemon_alternate_form))
    

if pokemon_alternate_form == 'None':  
    
    st.plotly_chart(bar_plot_weakness_category (weakeness_pokemon(types_chart_final, pokemon_database, pokemon_chosen, None)))

else:
    
    st.plotly_chart(bar_plot_weakness_category (weakeness_pokemon(types_chart_final, pokemon_database, pokemon_chosen, pokemon_alternate_form)))

#st.dataframe(df_pokemon)

# Text input
#name = st.text_input("Enter your team name:")

# Button
#if st.button("Submit"):
#    st.write(f"Hello, {name}!")

# Slider
#number = st.slider("Select a number:", 0, 100)
#st.write(f"You selected: {number}")

#weakeness_pokemon(types_chart_final, pokemon_database, 'Charizard', 'Mega Y')

# Create a select box
#selected_league_option = st.selectbox("Choose an option:", league_names)

# Get the teams 'ids'

#id_league_choice = leagues_dictionary[selected_league_option]

#id_team_season = chamada_api(f'/teams?league={id_league_choice}&season=2021')

#teams_ids = transform_dic_column(pd.DataFrame(id_team_season['response']), ['team'])['team_id'].tolist()
#teams_names = transform_dic_column(pd.DataFrame(id_team_season['response']), ['team'])['team_name'].tolist()

#teams_dictionary = dict(zip(teams_names, teams_ids))

# Create a select box
#selected_team_option = st.selectbox("Choose an option:", teams_names)
