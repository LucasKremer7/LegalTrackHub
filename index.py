from selenium import webdriver
from time import sleep
from dotenv import load_dotenv
import os

load_dotenv()

usuario = os.getenv('USUARIO')
print(usuario)
senha = os.getenv('SENHA')
print(senha)

options = webdriver.ChromeOptions()

driver = webdriver.Chrome(options=options)

url = driver.get('https://www.selenium.dev/documentation/webdriver/getting_started/first_script/')
sleep(5)