from dotenv import load_dotenv, find_dotenv
import os
import mysql.connector
from mysql.connector import Error

def get_connection_mysql():
    try:
        connection = mysql.connector.connect(
            host = os.getenv("DB_HOST"),
            port = os.get("DB_PORT"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD"),
            database = os.getenv("DB_NAME")
        )

        if connection.is_connected():
            print("Connection Successfully")
            cursor =  connection.cursor()
    except Error as e:
        print(f"Error while connecting:{e}")
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed")
        