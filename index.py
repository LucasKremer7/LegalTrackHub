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
from PIL import Image
from glob import glob
from reportlab.lib.pagesizes import letter
from reportlab.lib import utils
from reportlab.pdfgen import canvas

load_dotenv()


class Consulting():

    def __init__(self):
        self.usuario = os.getenv('USUARIO')
        self.senha = os.getenv('SENHA')
        self.base_path = os.getenv('BASE_PATH')
        self.options = webdriver.FirefoxOptions()
        self.sep = self.sep = '/' if eval(os.getenv('IS_LINUX')) else '\\'
        # self.options.add_argument("--headless")
        self.extract_capa_do_processo = {'CPF/CNPJ':[],'N do processo': [],'Assunto principal': [],'Classe da acao': [],'Competencia': [],'Data de autuacao': [],
                                        'Situacao': [],'Orgao julgador': [],'Juiz': [],'Processos relacionados': [], 'Nome do Advogado': [],'Advogado Reu': [],
                                        'Autor': [],'Reu': [],'Caminho': [] }
        self.lista_URLs = ['https://eproc.jfpr.jus.br/eprocV2/', 'https://eproc.jfsc.jus.br/eprocV2/', 'https://eproc.jfrs.jus.br/eprocV2/']

    def start(self):
        df = pd.read_excel(f"{self.base_path}{self.sep}testes{self.sep}teste_pre_dot.xlsx") # Primeiro CNPJ 6 processos
        # df = pd.read_excel(f'{self.base_path}{self.sep}testes{self.sep}testes_santa_catarina - Copia.xlsx')
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
        self.driver = webdriver.Firefox(options=self.options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10, poll_frequency=1)
        self.acess_tribunal(self.usuario, self.senha, self.lista_URLs)

    def acess_tribunal(self, usuario, senha, URLs):

        self.driver.get(URLs[0])
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
        self.site = BeautifulSoup(url_page, 'html.parser') 
        process_exists = self.site.find('div', attrs={'id':'divAreaResultadosAjax'}) # --- # Esse elemento aparece nas condições de 'Não tem processo' e 'Tem vários processos'

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

        self.extract_capa_do_processo['CPF/CNPJ'].append(self.cnpj)
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
        self.extract_capa_do_processo['Caminho'].append('Não possui processo')

        self.save_planilha(self.extract_capa_do_processo)

    def one_process(self): # Função que adicionará no dicionário a informação de que este CNPJ possui apenas um processo no TRF4
        print('\n\n\nEstou na função one_process\n\n\n')
        # url_page = self.driver.page_source
        # site = BeautifulSoup(url_page, 'html.parser')
        # # print(site.prettify())
        self.processo = self.site.find('span', attrs={'id': 'txtNumProcesso'}).text
        self.processo = self.processo.replace('.', '').replace('-', '') 
        sleep(1)
        self.extract_capa_process(self.processo, self.cnpj)
        self.driver.find_element(By.ID, 'btnNova').click()
        sleep(2)
    
    def many_process(self): # Função que adicionará no dicionário a informação de que este CNPJ possui varios processos no TRF4
        print('\n\n\n [ Estou na função many_process ] \n\n\n')
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
            self.driver.find_element(By.ID, 'txtNumProcessoPesquisaRapida').click()
            sleep(1)
            self.driver.find_element(By.ID, 'txtNumProcessoPesquisaRapida').send_keys(self.processo, Keys.ENTER)
            self.extract_capa_process(self.processo, self.cnpj)
        
        self.driver.find_element(By.ID, 'btnNova').click()
        sleep(2)

    def extract_capa_process(self, processo, cnpj):
        print(f"\n\n\n [ Estou na função de extrair informações da Capa do Processo! ] \n\n\n")
        sleep(4)

        url_page = self.driver.page_source
        self.site = BeautifulSoup(url_page, 'html.parser')
        
        self.driver.execute_script("arguments[0].style.display = 'block';", self.driver.find_element(By.ID, 'conteudoAssuntos2'))
        assunto_principal = self.driver.find_element(By.CSS_SELECTOR, '#conteudoAssuntos2 > table > tbody > tr.infraTrClara > td:nth-child(2)')
        classe_acao = self.driver.find_element(By.ID, 'txtClasse')
        competencia = self.driver.find_element(By.ID, 'txtCompetencia')
        data_autuacao = self.driver.find_element(By.ID, 'txtAutuacao')
        situacao = self.driver.find_element(By.ID, 'txtSituacao')
        orgao_julgador = self.driver.find_element(By.ID, 'txtOrgaoJulgador')
        juiz = self.driver.find_element(By.ID, 'txtMagistrado')   
        partes = self.extract_partes_representantes(self.site) # Função que coleta o nome das partes e seus respectivos advogados.
        processos_relacionados = self.find_process_related(self.site)
        self.extract_capa_do_processo['CPF/CNPJ'].append(cnpj)
        self.extract_capa_do_processo['N do processo'].append(processo)
        self.extract_capa_do_processo['Assunto principal'].append(assunto_principal.text)
        self.extract_capa_do_processo['Classe da acao'].append(classe_acao.text)
        self.extract_capa_do_processo['Competencia'].append(competencia.text)
        self.extract_capa_do_processo['Data de autuacao'].append(data_autuacao.text)
        self.extract_capa_do_processo['Situacao'].append(situacao.text)
        self.extract_capa_do_processo['Orgao julgador'].append(orgao_julgador.text)
        self.extract_capa_do_processo['Juiz'].append(juiz.text)
        self.extract_capa_do_processo['Processos relacionados'].append(processos_relacionados)
        self.extract_capa_do_processo['Autor'].append(partes[0])
        self.extract_capa_do_processo['Nome do Advogado'].append(partes[1])
        self.extract_capa_do_processo['Reu'].append(partes[2])
        self.extract_capa_do_processo['Advogado Reu'].append(partes[3])
        # self.extract_capa_do_processo['Caminho'].append(f"{self.base_path}a00_downloads{self.sep}{self.cnpj}{self.sep}_{processo}_inicial_.pdf")

        self.verify_second_captcha()
        self.save_planilha(self.extract_capa_do_processo) # FIM DA COLETA DE DADOS DO PROCESSO. DADOS SENDO SALVO NA PLANILHA.
        

    def verify_second_captcha(self):
        print(' [ Estou no segundo Captcha! ]')
        
        # CHAMA A FUNÇÃO QUE QUEBRA CAPTCHAS
        # Caso ele consiga quebrar o captcha e o link ficar apto para ser clicado, chame a função de screenshot
        self._screenshot(self.driver, self.wait)
        caminho_do_arquivo = self.merge_pdf()
        self.extract_capa_do_processo['Caminho'].append(caminho_do_arquivo)
        print(caminho_do_arquivo)
        
        # Caso contrário ele 
    
    def extract_partes_representantes(self, site):

        """
        Está função irá realizar o tratamento e a coletado dos dados referente as partes do processo.
        Bem como o autor(es), o(s) advogado(s) do autor, reu(s) e o(s) advogado(s).

        """
        
        partes = []
        lista = []

        partes_representantes = site.find('table', attrs={'id': 'tblPartesERepresentantes'}).findAll('td') # Localiza a div com o autor e seu advogado, reu e seu advogado
        ponteiro = 0
        for elem in partes_representantes:
            elem = elem.text
            lista_autor = elem.split('\n')
            for item in lista_autor:
                lista_autor = item.split(10*'\xa0')
                for objeto in lista_autor:
                    objeto = objeto.replace('\xa0', '&')
                    objeto = objeto.replace('&&&', ' ').replace('&&&&', ' ')
                    objeto = objeto.replace('&', '')
                    if len(lista_autor) == 1:
                        partes.append(objeto)
                        partes.append('Não localizado advogado!')
                    elif len(lista_autor) == 2:
                        partes.append(objeto)
                    elif len(lista_autor) >= 3:
                        lista.append(objeto)
                        ponteiro += 1
                        if ponteiro >= 3:
                            partes.append(lista[0])
                            partes.append(lista[1])

        return partes
    
    def find_process_related(self, site):
        print('\n\n\n [ Estou na função de processos relacionados! ] \n\n\n')

        processos_relacionados = []

        try:
            loc_process = site.find('table', attrs={'id': 'tableRelacionado'}).findAll('a')        
        except:
            loc_process = False
        
        if loc_process:
            for elem in loc_process:
                processos_relacionados.append(elem.text)
        else:
            processos_relacionados.append('Não possui processos relacionados!')
        
        if len(processos_relacionados) > 1:
            processos_relacionados = ','.join(processos_relacionados)
            return processos_relacionados
        else:
            return processos_relacionados[0]
    
    def _screenshot(self, driver, wait):
        # Fazer uma condicional que verifica a UF para quebrar o captcha
        table_moviments = driver.find_element(By.XPATH, '//*[@id="divTblEventos"]').find_elements(By.TAG_NAME, 'tr')
        for i in table_moviments:
            elementos = i.find_elements(By.TAG_NAME, 'td')
            if len(elementos) != 0 and 'INIC1' in elementos[4].text:
                evento = int(elementos[0].text)
                inicial = elementos[4]
        
        if evento == 1:
            inicial = inicial.find_elements(By.TAG_NAME, 'a')
            inicial = inicial[0]
            inicial.click()
        else:
            ...
            # Chamar aqui uma função de escape
        
        self.abas = self.driver.window_handles
        sleep(0.5)
        if len(self.abas) > 1:
            self.original_window = self.driver.current_window_handle
            for window_handle in self.driver.window_handles:
                if window_handle != self.original_window:
                    self.driver.switch_to.window(self.abas[-1])
                    wait.until(frame_to_be_available_and_switch_to_it(('id', 'conteudoIframe')))
                    print(window_handle)
                    break
        
        self.driver.find_element(By.ID, 'scaleSelect').click()
        sleep(0.5)
        self.driver.find_element(By.ID, 'pageFitOption').click()
        sleep(0.5)
        container_pdfs = self.driver.find_element(By.ID,'viewer')
        sleep(0.5)
        pdfs_inic = container_pdfs.find_elements(By.CLASS_NAME, 'page')
        sleep(0.5)
        contador = 1
        for pdf in pdfs_inic:
            sleep(0.5)
            contador_str = str(contador).zfill(2)
            # pdf.screenshot(f'{self.base_path}{self.sep}arquivos{self.sep}_{self.processo}_page_{contador_str}_INIC1.png')
            pdf.screenshot(f'{self.base_path}{self.sep}a07_temps{self.sep}a02_temp_files{self.sep}_{self.processo}_page_{contador_str}_INIC1.png')
            sleep(0.5)
            contador += 1

        self.driver.close()
        sleep(0.5)
        self.driver.switch_to.window(self.original_window)
        sleep(0.5)
        self.driver.switch_to.default_content()
        sleep(0.5)
    
    def merge_pdf(self):

        try:
            input_folder = f"{self.base_path}{self.sep}a07_temps{self.sep}a02_temp_files"
            
            output_pdf = f"{self.base_path}{self.sep}arquivos{self.sep}_{self.processo}_inicial_.pdf"
            # output_pdf = f"{self.base_path}{self.sep}a00_downloads{self.sep}{self.cnpj}{self.sep}_{self.processo}_inicial_.pdf"

            png_files = [file for file in os.listdir(input_folder) if file.endswith(".png")]
            png_files.sort()
            c = canvas.Canvas(output_pdf, pagesize=letter)
            for png_file in png_files:
                
                img = Image.open(f"{self.base_path}{self.sep}a07_temps{self.sep}a02_temp_files{self.sep}{png_file}")
                img_width, img_height = img.size            
                c.drawImage(os.path.join(input_folder, png_file), 0, 0, width=img_width, height=img_height)            
                if png_file != png_files[-1]:
                    c.showPage()

            c.save()
            img.close()

            for elem in glob(f"{self.base_path}{self.sep}a07_temps{self.sep}a02_temp_files{self.sep}*.png"):
                os.remove(elem)
            sleep(1)
            caminho_do_arquivo = (f'{self.base_path}a00_downloads{self.sep}{self.cnpj}{self.sep}_{self.processo}_inicial_.pdf')
        except:
            caminho_do_arquivo = (f'Falha no download do processo {self.processo}. Necessário verificar manualmente.')

        return caminho_do_arquivo
    
    def save_planilha(self, dados_processuais):
        print(f'\n\n\n [ Estou na função de salvar na planilha as informações extraídas da capa do processo. ] \n\n\n')

        dados = pd.DataFrame(dados_processuais, columns=['CPF/CNPJ', 'N do processo', 'Assunto principal', 'Classe da acao', 'Competencia', 'Data de autuacao', 'Situacao', 'Orgao julgador', 'Juiz', 'Processos relacionados', 'Autor', 'Nome do Advogado', 'Reu', 'Advogado Reu', 'Caminho'])

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