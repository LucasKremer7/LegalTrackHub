from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import alert_is_present, frame_to_be_available_and_switch_to_it
from selenium.webdriver.support.expected_conditions import new_window_is_opened, number_of_windows_to_be
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
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
        self.extract_capa_do_processo = {'cpf/cnpj':[],'N do processo': [],'Assunto principal': [],'Classe da acao': [],'Competencia': [],'Data de autuacao': [],
                                        'Situacao': [],'Orgao julgador': [],'Juiz': [],'Processos relacionados': [], 'Nome do Advogado': [],'Advogado Reu': [],
                                        'Autor': [],'Reu': [],'Caminho_Planilha_Movimentos': [] }

    def start(self):
        df = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot.xlsx") # Primeiro CNPJ 6 processos
        # df = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot - Copia.xlsx") # Primeiro CNPJ nenhum processo
        # df = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot - Copia (2).xlsx") # Primeiro CNPJ somente 1 processo
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
        sleep(2)
        self.driver.find_element(By.CSS_SELECTOR, '#main-menu > li:nth-child(4) > a').click() # --- # Menu lateral (Consulta Processual)
        self.driver.find_element(By.CSS_SELECTOR, '#menu-ul-3 > li:nth-child(1) > a > span.menu-item-text').click() # --- # Dropbox (Consultar Processos)
        sleep(2)

        self.contador = 0
        for self.cnpj in lista_cnpj: # Loop que irá iterar sobre toda lista de CNPJs e consultará todos.
            self.pesquisa_cnpj(self.cnpj)
            self.contador += 1
        
        print(f'Foram consultados {self.contador} CNPJs')
        
    def pesquisa_cnpj(self, cnpj):

        self.driver.refresh()
        sleep(1)
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
    
    def result_pesquisa(self): # Função que verifica o resultado inicial da consulta, se o CNPJ possui ou não processo.

        url_page = self.driver.page_source
        site = BeautifulSoup(url_page, 'html.parser') 
        process_exists = site.find('div', attrs={'id':'divAreaResultadosAjax'}) # --- # Esse elemento aparece nas condições de 'Não tem processo' e 'Tem vários processos'

        if process_exists == None:
            print(f' [ O CNPJ "{self.cnpj}" possui apenas 1 processo.\nChamando a função que faz a coleta dos dados processuais. ] ')
            self.one_process()
        elif 'Lista de Processos' in process_exists.text:
            process_exists = len(process_exists)
            print(f'O CNPJ "{self.cnpj}" possui mais de um processo.\nChamando a função de coleta dos dados processuais. ] ')
            self.many_process()
        elif 'Nenhum Resultado Encontrado' in process_exists.text:
            print('Chamando a função que adicionará no dicionário a informação que este CNPJ não possui processo.')
            self.zero_process()
    
    def zero_process(self): # Função que adicionará no dicionário a informação de que este CNPJ não possui processo no TRF4
        print('\n\n\nEstou na função zero_process\n\n\n')

        self.extract_capa_do_processo['cpf/cnpj'].append(self.cnpj)
        self.extract_capa_do_processo['N do processo'].append('Não possui processo')
        self.extract_capa_do_processo['Assunto principal'].append('Não possui processo')
        self.extract_capa_do_processo['Classe da acao'].append('Não possui processo')
        self.extract_capa_do_processo['Competencia'].append('Não possui processo')
        self.extract_capa_do_processo['Data de autuacao'].append('Não possui processo')
        self.extract_capa_do_processo['Situacao'].append('Não possui processo')
        self.extract_capa_do_processo['Orgao julgador'].append('Não possui processo')
        self.extract_capa_do_processo['Juiz'].append('Não possui processo')
        self.extract_capa_do_processo['Nome do Advogado'].append('Não possui processo')
        self.extract_capa_do_processo['Advogado Reu'].append('Não possui processo')
        self.extract_capa_do_processo['Autor'].append('Não possui processo')
        self.extract_capa_do_processo['Reu'].append('Não possui processo')
        self.extract_capa_do_processo['Processos relacionados'].append('Não possui processo')
        self.extract_capa_do_processo['Caminho_Planilha_Movimentos'].append('Não possui processo')

        self.save_planilha(self.extract_capa_do_processo)

    def one_process(self): # Função que adicionará no dicionário a informação de que este CNPJ possui apenas um processo no TRF4
        print('\n\n\nEstou na função one_process\n\n\n')
        url_page = self.driver.page_source
        site = BeautifulSoup(url_page, 'html.parser')
        print(site.prettify())
        self.processo = site.find('div', attrs={'style': 'XXX'}) 
        sleep(1)
        self.extract_capa_process(self.processo, self.cnpj)
    
    def many_process(self): # Função que adicionará no dicionário a informação de que este CNPJ possui varios processos no TRF4
        print('\n\n\nEstou na função many_process\n\n\n')
        # sleep(4)
        lista_processos = []
        tabela_processos = self.driver.find_element(By.CSS_SELECTOR, 'div > table > tbody').find_elements(By.TAG_NAME, 'tr') # Retorna uma lista com todos os elementos 'td' dentro da tag 'tr'

        for value_row in tabela_processos:
            value_row = value_row.find_elements(By.TAG_NAME, 'td')
            for value_collum in value_row:
                lista_processos.append(value_collum.text) # Aqui value_collum, será adicionado a uma nova lista, como processo para ser consultado.
                break

        sleep(1)
        print(lista_processos)
    
        for self.processo in lista_processos:
            self.processo = self.processo.replace('.', '').replace('-', '')
            print(self.processo)
            sleep(4)
            self.driver.find_element(By.CSS_SELECTOR, 'div > form > input').send_keys(self.processo, Keys.ENTER)
            self.extract_capa_process(self.processo, self.cnpj)

    def extract_capa_process(self, processo, cnpj):
        print(f" [ Estou na função de extrair informações da Capa do Processo! ] ")
        sleep(4)

        url_page = self.driver.page_source
        site = BeautifulSoup(url_page, 'html.parser')
        
        # btn_assunto = self.driver.find_element(By.ID, 'conteudoAssuntos2')
        self.driver.execute_script("arguments[0].style.display = 'block';", self.driver.find_element(By.ID, 'conteudoAssuntos2'))
        assunto_principal = self.driver.find_element(By.CSS_SELECTOR, '#conteudoAssuntos2 > table > tbody > tr.infraTrClara > td:nth-child(2)')
        classe_acao = self.driver.find_element(By.ID, 'txtClasse') # --------------------------------------------------------------------------------- # Localiza o elemento da Classe da acao
        competencia = self.driver.find_element(By.ID, 'txtCompetencia') # ---------------------------------------------------------------------------- # Localiza o elemento da Competencia
        data_autuacao = self.driver.find_element(By.ID, 'txtAutuacao') # ----------------------------------------------------------------------------- # Localiza o elemento da Data de autuacao do processo
        situacao = self.driver.find_element(By.ID, 'txtSituacao') # ---------------------------------------------------------------------------------- # Localiza o elemento da Situacao do processo
        orgao_julgador = self.driver.find_element(By.ID, 'txtOrgaoJulgador') # ----------------------------------------------------------------------- # Localiza o elemento que informa qual é o Orgao julgador
        juiz = self.driver.find_element(By.ID, 'txtMagistrado') # ------------------------------------------------------------------------------------ # Localiza o elemento que informa o nome do Juiz responsável
        partes_representantes = self.driver.find_element(By.CSS_SELECTOR,'#tblPartesERepresentantes > tbody > tr:nth-child(2)').text
        partes_representantes = partes_representantes.split('\n')

        nome_autor = partes_representantes[0].strip()
        print(nome_autor)
        nome_advogado = partes_representantes[2].strip()
        print(nome_advogado)
        nome_reu = partes_representantes[5].strip()
        print(nome_reu)
        reu_advogado = partes_representantes[7].strip()
        print(reu_advogado)
        

        self.extract_capa_do_processo['cpf/cnpj'].append(cnpj)
        self.extract_capa_do_processo['N do processo'].append(processo)
        self.extract_capa_do_processo['Assunto principal'].append(assunto_principal.text)
        self.extract_capa_do_processo['Classe da acao'].append(classe_acao.text)
        self.extract_capa_do_processo['Competencia'].append(competencia.text)
        self.extract_capa_do_processo['Data de autuacao'].append(data_autuacao.text)
        self.extract_capa_do_processo['Situacao'].append(situacao.text)
        self.extract_capa_do_processo['Orgao julgador'].append(orgao_julgador.text)
        self.extract_capa_do_processo['Juiz'].append(juiz.text)
        self.extract_capa_do_processo['Nome do Advogado'].append(nome_advogado)
        self.extract_capa_do_processo['Advogado Reu'].append(reu_advogado)
        self.extract_capa_do_processo['Autor'].append(nome_autor)
        self.extract_capa_do_processo['Reu'].append(nome_reu)
        self.extract_capa_do_processo['Caminho_Planilha_Movimentos'].append(f"{self.base_path}a00_downloads{self.sep}{self.cnpj}{self.sep}_{self.proc}_inicial_.pdf")

        self.save_planilha(self.extract_capa_do_processo)
    
    def find_process_related(self):
        print(' [ Estou na função de processos relacionados! ]')
        processo_relacionado = self.driver.find_element(By.CSS_SELECTOR, '#tableRelacionado > tbody').find_elements(By.TAG_NAME, 'a')
        for elem in processo_relacionado:
            print(elem.text)
    
    def save_planilha(self, dados_processuais):
        print(f' [ Estou na função de salvar na planilha as informações extraídas da capa do processo. ] ')

        dados = pd.DataFrame(dados_processuais, columns=['cpf/cnpj', 'N do processo', 'Assunto principal', 'Classe da acao', 'Competencia', 'Data de autuacao', 'Subsecao de origem', 'Situacao', 'Orgao julgador', 'Juiz', 'Processos relacionados', 'Nome do Advogado', 'OAB do Advogado', 'Autor', 'Reu', 'Caminho_Planilha_Movimentos'])

        dados.to_excel(f'{self.base_path}{self.sep}arquivos{self.sep}_Planilha_com_Resultados_.xlsx', index=False)

if __name__ == "__main__":

    app = Consulting()
    app.start()
    # app.init_driver()
    print('Código finalizado com sucesso!')

# def rascunho():
#     response = requests.get(url)
#     site = BeautifulSoup(response.text, 'html.parser')
#     print(site.prettify())
#     CNPJ = 07781920000133 (6 processos)
#     CNPJ = 21578639000129 (Nenhum processo)