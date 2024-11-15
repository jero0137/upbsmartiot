# Usa una imagen base de Python
FROM python:3.8

# Actualiza los paquetes e instala cron
RUN apt-get update && apt-get install -y cron

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de dependencias y el resto del código a la imagen
COPY . .

# Instala las dependencias
RUN pip install --no-cache-dir -r imports.txt

# Copia el archivo de crontab al directorio adecuado
COPY crontab /etc/cron.d/crontab

# Da permisos de ejecución al archivo crontab
RUN chmod +x /etc/cron.d/crontab

# Aplica el archivo crontab
RUN crontab /etc/cron.d/crontab

# Crea el archivo de log para cron
RUN touch /var/log/cron.log

# Copia y da permisos de ejecución al script de entrada
COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# Ejecuta el script de entrada
CMD ["./entrypoint.sh"]
