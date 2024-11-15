# frontend_app.py

from flask import Flask
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import psycopg2
import pandas as pd
from datetime import datetime
import os

# Configuración del servidor Flask y de Dash
server = Flask(__name__)
app = Dash(__name__, server=server, url_base_pathname='/dashboard/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# Conexión a la base de datos PostgreSQL
def connect_to_postgresql():
    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres_db"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "jero"),
            password=os.getenv("POSTGRES_PASSWORD", "1234"),
            dbname=os.getenv("POSTGRES_DB", "medidas")
        )
        print("Conexión a PostgreSQL exitosa")
        return connection
    except psycopg2.OperationalError as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

# Función para determinar el color del gauge de temperatura
def get_temp_color(value):
    if value < 20:
        return "lightblue"
    elif 20 <= value < 25:
        return "blue"
    else:
        return "lightcoral"

# Función para determinar el color del gauge de humedad
def get_humidity_color(value):
    if value < 30:
        return "lightcoral"
    elif 30 <= value < 60:
        return "lightgreen"
    else:
        return "lightblue"

# Layout de Dash con tres pestañas
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Home', children=[
            dbc.Row([
                dbc.Col(html.Img(src="./assets/suculenta.jpg", style={'width': '100%'}), width=6),
                dbc.Col(html.Div([
                    html.H3("Suculenta", style={'textAlign': 'center'}),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id='temp-gauge', config={'displayModeBar': False}), width=6),
                        dbc.Col(dcc.Graph(id='humidity-gauge', config={'displayModeBar': False}), width=6),
                    ], justify='center'),
                    html.Div([
                        html.P("Las suculentas son plantas que almacenan agua en sus hojas, tallos o raíces, lo que les permite sobrevivir en ambientes áridos. Aquí tienes un resumen:", style={'textAlign': 'center'}),
                        html.P("Nombre científico: No tienen un único nombre, ya que 'suculentas' agrupa diversas familias botánicas, como Crassulaceae, Cactaceae y Euphorbiaceae. Ejemplo: Echeveria elegans.", style={'textAlign': 'center'}),
                        html.P("Lugar de origen: Muchas especies provienen de regiones áridas o semiáridas de América, África y Asia.", style={'textAlign': 'center'}),
                        html.P("Dónde se encuentran: Se encuentran en todo el mundo, tanto en hábitats naturales como en jardines y hogares.", style={'textAlign': 'center'}),
                        html.P("Importancia para el humano:", style={'textAlign': 'center'}),
                        html.Ul([
                            html.Li("Ornamentación: Son populares en la decoración por su estética y bajo mantenimiento.", style={'textAlign': 'center'}),
                            html.Li("Uso medicinal: Algunas, como el aloe vera, se usan en tratamientos tópicos y cosmética.", style={'textAlign': 'center'}),
                            html.Li("Conservación: Ayudan en la restauración de suelos áridos y en jardines sostenibles.", style={'textAlign': 'center'}),
                        ], style={'textAlign': 'center'}),
                    ], style={'marginTop': '20px'})
                ]), width=6)
            ])
        ]),
        dcc.Tab(label='Datos temperatura y humedad', children=[
            html.H3("Temperatura y Humedad por Fechas"),
            dcc.DatePickerSingle(
                id='date-picker',
                date=pd.to_datetime("today").date(),
                display_format='YYYY-MM-DD'
            ),
            dcc.Tabs([
                dcc.Tab(label='Temperatura', children=[
                    dcc.Graph(id='temp-date-graph')
                ]),
                dcc.Tab(label='Humedad', children=[
                    dcc.Graph(id='humidity-date-graph')
                ]),
            ])
        ]),
        dcc.Tab(label='Pronóstico y Recomendaciones', children=[
            html.H3("Pronóstico de Temperatura y Humedad (24 horas)"),
            dbc.Card([
                dcc.Graph(id='temp-prediccion-graph'),
                dcc.Graph(id='humedad-prediccion-graph')
            ]),
            html.Div(id='recommendation-text', style={'margin-top': '20px', "font-size": "20px"})
        ])
    ]),
    dcc.Interval(id='interval-component', interval=5*60*1000, n_intervals=0)  # Actualización cada 5 minutos
])

# Callback para actualizar los gauges de temperatura y humedad actuales
@app.callback(
    [Output('temp-gauge', 'figure'),
     Output('humidity-gauge', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_gauges(n):
    connection = connect_to_postgresql()
    if connection is None:
        # Retornar gauges vacíos con mensaje de error
        temp_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            title={'text': "Temperatura Actual (°C)"},
            gauge={'axis': {'range': [0, 50]}}
        ))
        humidity_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            title={'text': "Humedad Actual (%)"},
            gauge={'axis': {'range': [0, 100]}}
        ))
        temp_fig.update_layout(height=250)
        humidity_fig.update_layout(height=250)
        return temp_fig, humidity_fig
    
    try:
        cursor = connection.cursor()
        
        # Obtener la última temperatura
        temp_query = """
            SELECT temperature
            FROM temperature_measurements
            WHERE entity_id = 'jeroag'
            ORDER BY timestamp DESC
            LIMIT 1
        """
        cursor.execute(temp_query)
        temp_result = cursor.fetchone()
        current_temp = temp_result[0] if temp_result else 0
        
        # Obtener la última humedad
        humidity_query = """
            SELECT humidity
            FROM humidity_measurements
            WHERE entity_id = 'jeroag'
            ORDER BY timestamp DESC
            LIMIT 1
        """
        cursor.execute(humidity_query)
        humidity_result = cursor.fetchone()
        current_humidity = humidity_result[0] if humidity_result else 0
        
        cursor.close()
        connection.close()
        
        # Determinar el color del gauge de temperatura
        temp_color = get_temp_color(current_temp)
        
        # Crear gráfico de gauge para temperatura
        temp_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_temp,
            title={'text': "Temperatura Actual (°C)"},
            gauge={
                'axis': {'range': [0, 50]},
                'bar': {'color': temp_color},
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': 30
                }
            }
        ))
        temp_fig.update_layout(height=250)
        
        # Determinar el color del gauge de humedad
        humidity_color = get_humidity_color(current_humidity)
        
        # Crear gráfico de gauge para humedad
        humidity_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_humidity,
            title={'text': "Humedad Actual (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': humidity_color},
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': 40
                }
            }
        ))
        humidity_fig.update_layout(height=250)
        
        return temp_fig, humidity_fig
    except Exception as e:
        print(f"Error al actualizar los gauges: {e}")
        # Retornar gauges vacíos con mensaje de error
        temp_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            title={'text': "Temperatura Actual (°C)"},
            gauge={'axis': {'range': [0, 50]}}
        ))
        humidity_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            title={'text': "Humedad Actual (%)"},
            gauge={'axis': {'range': [0, 100]}}
        ))
        temp_fig.update_layout(height=250)
        humidity_fig.update_layout(height=250)
        return temp_fig, humidity_fig

# Callback para actualizar los gráficos de temperatura y humedad basados en la fecha seleccionada
@app.callback(
    [Output('temp-date-graph', 'figure'),
     Output('humidity-date-graph', 'figure')],
    [Input('date-picker', 'date')]
)
def update_temp_humidity_graphs(selected_date):
    if selected_date is None:
        return {}, {}
    connection = connect_to_postgresql()
    if connection is None:
        return {}, {}
    date = pd.to_datetime(selected_date).date()

    # Consultar datos de temperatura para la fecha seleccionada
    temp_query = """
        SELECT temperature, timestamp
        FROM temperature_measurements
        WHERE DATE(timestamp) = %s
        ORDER BY timestamp ASC
    """
    temp_data = pd.read_sql(temp_query, connection, params=[date])

    # Consultar datos de humedad para la fecha seleccionada
    humidity_query = """
        SELECT humidity, timestamp
        FROM humidity_measurements
        WHERE DATE(timestamp) = %s
        ORDER BY timestamp ASC
    """
    humidity_data = pd.read_sql(humidity_query, connection, params=[date])
    connection.close()

    # Crear gráfico de temperatura
    temp_fig = go.Figure(data=[
        go.Scatter(x=temp_data['timestamp'], y=temp_data['temperature'], mode='lines+markers', name='Temperatura')
    ])
    temp_fig.update_layout(
        title=f"Temperatura el {selected_date}",
        xaxis_title="Hora",
        yaxis_title="Temperatura (°C)"
    )

    # Crear gráfico de humedad
    humidity_fig = go.Figure(data=[
        go.Scatter(x=humidity_data['timestamp'], y=humidity_data['humidity'], mode='lines+markers', name='Humedad')
    ])
    humidity_fig.update_layout(
        title=f"Humedad el {selected_date}",
        xaxis_title="Hora",
        yaxis_title="Humedad (%)"
    )

    return temp_fig, humidity_fig

# Callback para actualizar los gráficos de predicciones y recomendaciones
@app.callback(
    [Output('temp-prediccion-graph', 'figure'),
     Output('humedad-prediccion-graph', 'figure'),
     Output('recommendation-text', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_prediction_graphs(n):
    connection = connect_to_postgresql()
    if connection is None:
        return {}, {}, "Error al conectar a PostgreSQL para obtener predicciones"
    
    try:
        query = """
        SELECT temperature_prediction, humidity_prediction, timestamp
        FROM predictions
        ORDER BY timestamp ASC
        """
        predictions = pd.read_sql(query, connection)
        connection.close()
        
        if predictions.empty:
            return {}, {}, "No hay predicciones disponibles"
        
        # Crear gráfico de predicciones de temperatura
        temp_fig = go.Figure(data=[
            go.Scatter(
                x=predictions['timestamp'],
                y=predictions['temperature_prediction'],
                mode='lines+markers',
                name='Predicción de Temperatura'
            )
        ])
        temp_fig.update_layout(
            title="Predicción de Temperatura para las Próximas 24 Horas",
            xaxis_title="Hora",
            yaxis_title="Temperatura Predicha (°C)"
        )

        # Crear gráfico de predicciones de humedad
        humidity_fig = go.Figure(data=[
            go.Scatter(
                x=predictions['timestamp'],
                y=predictions['humidity_prediction'],
                mode='lines+markers',
                name='Predicción de Humedad'
            )
        ])
        humidity_fig.update_layout(
            title="Predicción de Humedad para las Próximas 24 Horas",
            xaxis_title="Hora",
            yaxis_title="Humedad Predicha (%)"
        )

        # Generar recomendaciones basadas en las predicciones
        recommendation_text = "Recomendaciones: "
        max_temp = predictions['temperature_prediction'].max()
        min_humidity = predictions['humidity_prediction'].min()
        max_humidity = predictions['humidity_prediction'].max()

        if max_temp > 28:
            if min_humidity < 50:
                recommendation_text += "Aumente la humedad al rango de 50% al 70% para evitar estrés por falta de agua. "
            elif max_humidity > 70:
                recommendation_text += "Reduzca la humedad al rango de 50% al 70% para evitar riesgo de hongos. "
        elif max_temp < 10:
            if min_humidity < 10:
                recommendation_text += "Aumente la humedad al rango de 10% al 50% para evitar destrucción de tejidos celulares. "
            elif max_humidity > 50:
                recommendation_text += "Reduzca la humedad al rango de 10% al 50% para evitar quemadura por frío. "
            recommendation_text += "Considere poner una fuente de calor o mover la planta a un lugar más cálido para reducir su estrés. "

        if recommendation_text.strip() == "Recomendaciones:":
            recommendation_text = "No se requieren recomendaciones adicionales."

        return temp_fig, humidity_fig, recommendation_text
    except Exception as e:
        print(f"Error al obtener predicciones: {e}")
        connection.close()
        return {}, {}, "Error al obtener predicciones"

if __name__ == "__main__":
    app.run_server(debug=True, port=8080, host="0.0.0.0")