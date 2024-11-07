import os
from crate import client
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.ensemble import RandomForestRegressor

def convert_epoch_ms_to_timestamp(epoch_ms):
    """Convert milliseconds epoch to datetime"""
    return datetime.fromtimestamp(epoch_ms / 1000.0)

# Conectar a PostgreSQL
def connect_to_postgresql():
    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres_db"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "jero"),
            password=os.getenv("POSTGRES_PASSWORD", "1234"),
            dbname=os.getenv("POSTGRES_DB", "medidas")
        )
        return connection
    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

def create_tables(connection):
    cursor = connection.cursor()
    try:
        # Temperature table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperature_measurements (
            entity_id VARCHAR(50),
            temperature FLOAT,
            timestamp TIMESTAMP,
            lat FLOAT,
            lon FLOAT
        )""")
        
        # Humidity table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS humidity_measurements (
            entity_id VARCHAR(50),
            humidity FLOAT,
            timestamp TIMESTAMP,
            lat FLOAT,
            lon FLOAT
        )""")
        
        # Predictions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            timestamp TIMESTAMP PRIMARY KEY,
            temperature_prediction FLOAT,
            humidity_prediction FLOAT
        )""")
        
        connection.commit()
    finally:
        cursor.close()

def read_from_crate():
    connection = client.connect('http://10.38.32.137:8083', username='crate')
    cursor = connection.cursor()
    try:
        query = """
        SELECT entity_id, temp, humedad, lat, lon, time_index
        FROM "doc"."etvariables"
        WHERE entity_id = 'jeroag'
          AND time_index >= NOW() - INTERVAL '3 DAY'
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

def insert_measurements(data):
    connection = connect_to_postgresql()
    if not connection:
        return
    
    cursor = connection.cursor()
    try:
        create_tables(connection)

        if(len(data) > 0):
            cursor.execute("DELETE FROM temperature_measurements")
            cursor.execute("DELETE FROM humidity_measurements")
        
        # Split and insert data with timestamp conversion
        for entity_id, temp, humidity, lat, lon, timestamp in data:
            # Convert epoch milliseconds to datetime
            timestamp_dt = convert_epoch_ms_to_timestamp(timestamp)
            
            if 0 <= temp <= 100:
                cursor.execute("""
                INSERT INTO temperature_measurements (entity_id, temperature, timestamp, lat, lon)
                VALUES (%s, %s, %s, %s, %s)
                """, (entity_id, temp, timestamp_dt, lat, lon))
                
            if 0 <= humidity <= 100:
                cursor.execute("""
                INSERT INTO humidity_measurements (entity_id, humidity, timestamp, lat, lon)
                VALUES (%s, %s, %s, %s, %s)
                """, (entity_id, humidity, timestamp_dt, lat, lon))
        
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def generate_predictions():
    connection = connect_to_postgresql()
    if not connection:
        return
    
    cursor = connection.cursor()
    try:
        # Get historical data
        cursor.execute("""
        SELECT temperature, timestamp 
        FROM temperature_measurements 
        ORDER BY timestamp DESC 
        LIMIT 1000
        """)
        temp_data = pd.DataFrame(cursor.fetchall(), columns=['temperature', 'timestamp'])
        
        cursor.execute("""
        SELECT humidity, timestamp 
        FROM humidity_measurements 
        ORDER BY timestamp DESC 
        LIMIT 1000
        """)
        humidity_data = pd.DataFrame(cursor.fetchall(), columns=['humidity', 'timestamp'])
        
        if len(temp_data) == 0 or len(humidity_data) == 0:
            print("Not enough data for predictions")
            return
            
        # Create and train models
        temp_forecaster = ForecasterAutoreg(
            regressor=RandomForestRegressor(n_estimators=100, random_state=123),
            lags=24
        )
        
        humidity_forecaster = ForecasterAutoreg(
            regressor=RandomForestRegressor(n_estimators=100, random_state=123),
            lags=24
        )
        
        # Train models
        temp_forecaster.fit(y=temp_data['temperature'])
        humidity_forecaster.fit(y=humidity_data['humidity'])
        
        # Generate predictions and convert to list
        steps = 24
        temp_predictions = temp_forecaster.predict(steps=steps).tolist()
        humidity_predictions = humidity_forecaster.predict(steps=steps).tolist()
        
        # Check if there are existing predictions and delete them
        cursor.execute("SELECT COUNT(*) FROM predictions")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("DELETE FROM predictions")
            
        # Store predictions
        current_time = datetime.now()
        for i in range(steps):
            future_time = current_time + timedelta(hours=i)
            cursor.execute("""
            INSERT INTO predictions (timestamp, temperature_prediction, humidity_prediction)
            VALUES (%s, %s, %s)
            ON CONFLICT (timestamp) DO UPDATE 
            SET temperature_prediction = EXCLUDED.temperature_prediction,
                humidity_prediction = EXCLUDED.humidity_prediction
            """, (future_time, temp_predictions[i], humidity_predictions[i]))
        
        connection.commit()
        
    except Exception as e:
        print(f"Error generating predictions: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    raw_data = read_from_crate()
    if raw_data:
        insert_measurements(raw_data)
        generate_predictions()