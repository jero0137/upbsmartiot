from flask import Flask, jsonify
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# Configuración del servidor Flask y de Dash
server = Flask(__name__)
app = Dash(__name__, server=server, url_base_pathname='/dashboard/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# Conexión a la base de datos PostgreSQL
def connect_to_postgresql():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        user="jero",
        password="1234",
        dbname="medidas"
    )

# Función para obtener los datos actuales de temperatura y humedad
def get_current_data():
    connection = connect_to_postgresql()
    query = """
        SELECT temperature, humidity, timestamp
        FROM temperature_measurements
        JOIN humidity_measurements USING (timestamp)
        ORDER BY timestamp DESC LIMIT 1
    """
    current_data = pd.read_sql(query, connection)
    connection.close()
    return current_data.iloc[0]

# Función para obtener datos históricos para gráficos en tiempo real
def get_historical_data():
    connection = connect_to_postgresql()
    temp_query = "SELECT temperature, timestamp FROM temperature_measurements ORDER BY timestamp DESC LIMIT 100"
    humidity_query = "SELECT humidity, timestamp FROM humidity_measurements ORDER BY timestamp DESC LIMIT 100"
    temp_data = pd.read_sql(temp_query, connection)
    humidity_data = pd.read_sql(humidity_query, connection)
    connection.close()
    return temp_data, humidity_data

# Función para obtener las predicciones
def get_predictions():
    connection = connect_to_postgresql()
    query = "SELECT temperature_prediction, humidity_prediction, timestamp FROM predictions ORDER BY timestamp"
    predictions = pd.read_sql(query, connection)
    connection.close()
    return predictions

# Layout de Dash con tres pestañas
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Home', children=[
            dbc.Row([
                dbc.Col(html.Img(src="/static/plant_image.jpg", style={'width': '100%'}), width=6),
                dbc.Col(html.Div([
                    html.H3("Información de la Planta"),
                    html.P("Temperatura ideal: 20-25°C"),
                    html.P("Humedad ideal: 40-60%"),
                    html.P("Luz: moderada")
                ]), width=6)
            ])
        ]),
        dcc.Tab(label='Datos Actuales', children=[
            html.H3("Temperatura y Humedad Actuales"),
            html.Div(id="current-temperature", style={"font-size": "24px", "margin-bottom": "10px"}),
            html.Div(id="current-humidity", style={"font-size": "24px", "margin-bottom": "20px"}),
            dcc.Graph(id='temp-actual-graph'),
            dcc.Graph(id='humedad-actual-graph')
        ]),
        dcc.Tab(label='Pronóstico y Recomendaciones', children=[
            html.H3("Pronóstico de Temperatura y Humedad (24 horas)"),
            dcc.Graph(id='temp-prediccion-graph'),
            dcc.Graph(id='humedad-prediccion-graph'),
            html.Div(id='recommendation-text', style={'margin-top': '20px', "font-size": "20px"})
        ])
    ])
])

# Callback para actualizar datos actuales
@app.callback(
    [Output('current-temperature', 'children'),
     Output('current-humidity', 'children')],
    [Input('temp-actual-graph', 'id')]
)
def update_current_values(_):
    data = get_current_data()
    temperature_text = f"Temperatura actual: {data['temperature']} °C"
    humidity_text = f"Humedad actual: {data['humidity']} %"
    return temperature_text, humidity_text

# Callback para actualizar las gráficas de datos actuales
@app.callback(
    [Output('temp-actual-graph', 'figure'),
     Output('humedad-actual-graph', 'figure')],
    [Input('temp-actual-graph', 'id')]
)
def update_current_graphs(_):
    temp_data, humidity_data = get_historical_data()
    temp_fig = go.Figure(data=[go.Scatter(x=temp_data['timestamp'], y=temp_data['temperature'], mode='lines', name='Temperature')])
    humidity_fig = go.Figure(data=[go.Scatter(x=humidity_data['timestamp'], y=humidity_data['humidity'], mode='lines', name='Humidity')])
    return temp_fig, humidity_fig

# Callback para actualizar las gráficas de predicciones y recomendaciones
@app.callback(
    [Output('temp-prediccion-graph', 'figure'),
     Output('humedad-prediccion-graph', 'figure'),
     Output('recommendation-text', 'children')],
    [Input('temp-prediccion-graph', 'id')]
)
def update_prediction_graphs(_):
    predictions = get_predictions()
    temp_fig = go.Figure(data=[go.Scatter(x=predictions['timestamp'], y=predictions['temperature_prediction'], mode='lines', name='Temperature Prediction')])
    humidity_fig = go.Figure(data=[go.Scatter(x=predictions['timestamp'], y=predictions['humidity_prediction'], mode='lines', name='Humidity Prediction')])
    
    recommendation_text = "Recomendaciones: "
    if predictions['temperature_prediction'].max() > 30:
        recommendation_text += "Evite exposición directa al sol. "
    if predictions['humidity_prediction'].min() < 30:
        recommendation_text += "Considere regar la planta. "
    
    return temp_fig, humidity_fig, recommendation_text

if __name__ == "__main__":
    server.run(debug=True, port=8080, host="0.0.0.0")