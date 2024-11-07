# Usa una imagen base de Python
FROM python:3.8

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de dependencias a la imagen
COPY imports.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r imports.txt

# Copia el resto de la aplicación a la imagen
COPY app.py .

# Especifica el comando por defecto para ejecutar la aplicación
CMD ["python", "app.py"]