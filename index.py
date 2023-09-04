from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import alert_is_present, frame_to_be_available_and_switch_to_it
from selenium.webdriver.support.expected_conditions import new_window_is_opened, number_of_windows_to_be
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.webdriver import ActionChains
from time import sleep
from dotenv import load_dotenv
import os
import pandas as pd
import openpyxl
from bs4 import BeautifulSoup
import requests

load_dotenv()


class Consulting():

    def __init__(self):
        self.usuario = os.getenv('USUARIO')
        self.senha = os.getenv('SENHA')
        self.base_path = os.getenv('BASE_PATH')
        self.options = webdriver.ChromeOptions()
        self.sep = self.sep = '/' if eval(os.getenv('IS_LINUX')) else '\\'
        # self.options.add_argument("--headless")

    def start(self):
        df = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot.xlsx")
        df = pd.DataFrame(df)
        self.lista_cnpj = []
        for index, row in df.iterrows():
            cnpj = row[0]
            cnpj = cnpj.replace('.','').replace('-', '').replace('/', '')
            self.lista_cnpj.append(cnpj)
        self.init_driver()

    def init_driver(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.maximize_window()
        self.acess_tribunal(self.usuario, self.senha)

    def acess_tribunal(self, usuario, senha):
        url = 'https://eproc.jfpr.jus.br/eprocV2/'
        self.driver.get(url)
        sleep(2)
        self.driver.find_element(By.ID, 'txtUsuario').send_keys(usuario)
        self.driver.find_element(By.ID, 'pwdSenha').send_keys(senha)
        self.driver.find_element(By.ID, 'sbmEntrar').click()

        self.verify_captcha()
    
    def verify_captcha(self):
        try:
            locate_elem = self.driver.find_element(By.TAG_NAME, 'h1')     
        except:
            locate_elem = False
        
        if locate_elem is False:
            print(' [ Captcha localizado! ] ')
        else:
            print(' [ Acesso confirmado! Você está no EPROC/PR! ] ')           
        
        self.go_to_consulting(self.lista_cnpj)

    def go_to_consulting(self, lista_cnpj):
        self.driver.find_element(By.CSS_SELECTOR, '#main-menu > li:nth-child(4) > a').click() # --- # Menu lateral (Consulta Processual)
        self.driver.find_element(By.CSS_SELECTOR, '#menu-ul-3 > li:nth-child(1) > a > span.menu-item-text').click() # --- # Dropbox (Consultar Processos)
        sleep(2)

        for self.cnpj in lista_cnpj:
            self.pesquisa_cnpj(self.cnpj)
        
    def pesquisa_cnpj(self, cnpj):
        self.driver.find_element(By.ID, 'selTipoPesquisa').click() # --- # Menu de Consulta (Tipo de Pesquisa)
        for elem in self.driver.find_elements(By.TAG_NAME, 'option'):
            if 'CPF/CNPJ' in elem.text:
                elem.click()
                break
        self.driver.find_element(By.CSS_SELECTOR, '#divStrDocParte > dl > dd > input').send_keys(cnpj)
        self.driver.find_element(By.NAME, 'chkExibirBaixados').click()
        self.driver.find_element(By.CLASS_NAME, 'ms-choice').click()
        self.driver.find_element(By.NAME, 'selectAllselIdClasse').click()
        self.driver.find_element(By.ID, 'sbmConsultar').click() # --- # Botão Azul (Consultar)
        sleep(2)
        self.result_pesquisa()
    
    def result_pesquisa(self):
        url_page = self.driver.page_source
        site = BeautifulSoup(url_page, 'html.parser') 
        process_exists = site.find('div', attrs={'id':'divAreaResultadosAjax'}) # --- # Esse elemento aparece nas condições de 'Não tem processo' e 'Tem vários processos'
        total_process = process_exists.find('caption', attrs={'class': 'infraCaption'})
        print(total_process.text)
        
        print(process_exists.prettify())   

if __name__ == "__main__":

    app = Consulting()
    app.start()
    print('Código finalizado com sucesso!')

# def rascunho():
#     response = requests.get(url)
#     site = BeautifulSoup(response.text, 'html.parser')
#     print(site.prettify())
#     CNPJ = 07781920000133