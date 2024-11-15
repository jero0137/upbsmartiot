import os
from crate import client
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.ensemble import RandomForestRegressor
import numpy as np
from scipy.interpolate import interp1d

def convert_epoch_ms_to_timestamp(epoch_ms):
    """Convert milliseconds epoch to datetime"""
    return datetime.fromtimestamp(epoch_ms / 1000.0)

# Conectar a PostgreSQL
def connect_to_postgresql():
    try:
        connection = psycopg2.connect(
            host='postgres_db',
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "jero"),
            password=os.getenv("POSTGRES_PASSWORD", "1234"),
            dbname=os.getenv("POSTGRES_DB", "medidas")
        )
        return connection
    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

def connect_to_crate():
    try:
        connection = client.connect('http://10.38.32.137:8083', username='crate')
        return connection
    except Exception as e:
        print(f"Error al conectar a CrateDB: {e}")
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
        print("Tablas creadas")
        connection.commit()
    finally:
        cursor.close()

def read_from_crate():
    connection = connect_to_crate()
    if connection is None:
        print("Error: No se pudo establecer la conexión a CrateDB")
        return None
    try:
        cursor = connection.cursor()
        query = """
        SELECT entity_id, temp, humedad, lat, lon, time_index
        FROM "doc"."etvariables"
        WHERE entity_id = 'jeroag'
        AND time_index >= NOW() - INTERVAL '10 DAY'
        ORDER BY time_index DESC 
        LIMIT 1000;
        """
        cursor.execute(query)
        raw_data = cursor.fetchall()
        cursor.close()
        connection.close()
        print("Datos leídos de CrateDB")
        return raw_data
    except Exception as e:
        print(f"Error al leer datos de CrateDB: {e}")
        return None

def insert_measurements(data):
    connection = connect_to_postgresql()
    if not connection:
        return
    
    cursor = connection.cursor()
    try:
        create_tables(connection)

        if len(data) > 0:
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
        print("Datos insertados")
    except Exception as e:
        print(f"Error insertando datos: {e}")
        connection.rollback()
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
        
        # Interpolate temperature data
        temp_data['timestamp'] = pd.to_datetime(temp_data['timestamp'])
        temp_data = temp_data.sort_values('timestamp')
        temp_data = temp_data.reset_index(drop=True)
        temp_data['minutes'] = (temp_data['timestamp'] - temp_data['timestamp'][0]).dt.total_seconds() / 60
        f_temp = interp1d(temp_data['minutes'], temp_data['temperature'], fill_value="extrapolate")
        t_new = np.linspace(temp_data['minutes'].min(), temp_data['minutes'].max(), num=1000)
        temp_interpolated = f_temp(t_new)
        
        # Interpolate humidity data
        humidity_data['timestamp'] = pd.to_datetime(humidity_data['timestamp'])
        humidity_data = humidity_data.sort_values('timestamp')
        humidity_data = humidity_data.reset_index(drop=True)
        humidity_data['minutes'] = (humidity_data['timestamp'] - humidity_data['timestamp'][0]).dt.total_seconds() / 60
        f_humidity = interp1d(humidity_data['minutes'], humidity_data['humidity'], fill_value="extrapolate")
        h_new = np.linspace(humidity_data['minutes'].min(), humidity_data['minutes'].max(), num=1000)
        humidity_interpolated = f_humidity(h_new)
        
        # Convert interpolated data to pandas Series
        temp_interpolated_series = pd.Series(temp_interpolated)
        humidity_interpolated_series = pd.Series(humidity_interpolated)
        
        # Create and train models
        temp_forecaster = ForecasterAutoreg(
            regressor=RandomForestRegressor(n_estimators=50, random_state=123),
            lags=100
        )
        
        humidity_forecaster = ForecasterAutoreg(
            regressor=RandomForestRegressor(n_estimators=50, random_state=123),
            lags=100
        )
        
        # Train models
        temp_forecaster.fit(y=temp_interpolated_series)
        humidity_forecaster.fit(y=humidity_interpolated_series)
        
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