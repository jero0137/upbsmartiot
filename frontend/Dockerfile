# Use the official Python image from the Docker Hub
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY imports.txt .

# Install the dependencies specified in the imports.txt file
RUN pip install --no-cache-dir -r imports.txt

# Copy the rest of the application code into the container
COPY . .

EXPOSE 8080

# Specify the command to run the application
CMD ["python", "app.py"]