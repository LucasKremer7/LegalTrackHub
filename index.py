from selenium import webdriver
from time import sleep
from dotenv import load_dotenv
import os
import pandas as pd
import openpyxl

load_dotenv()


class Consulting():

    def __init__(self):
        self.usuario = os.getenv('USUARIO')
        self.senha = os.getenv('SENHA')
        self.base_path = os.getenv('BASE_PATH')
        self.options = webdriver.ChromeOptions()
        self.driver = webdriver.Chrome(options=self.options)
        self.sep = self.sep = '/' if eval(os.getenv('IS_LINUX')) else '\\'
        self.options.add_argument("--headless")

    def start(self):
        lista_cnpj = []
        planilha = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot.xlsx")
        df = pd.DataFrame(planilha)
        sleep(0.1)
        
        for index, valor in df:
            print(index)
            print(valor)
            lista_cnpj.append(valor)

    def scraping(self):
        url = self.driver.get('https://www.selenium.dev/documentation/webdriver/getting_started/first_script/')
        self.driver.maximize_window()
        sleep(5)

if __name__ == "__main__":

    app = Consulting()
    app.start()
    print('Código finalizado com sucesso!')