import os
import requests
import pandas as pd
from datetime import datetime, timedelta

class ExtracaoDataANP:
    def __init__(self):
        self.url_anp = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc"
        self.df_final = pd.DataFrame()
        self.data_path = '../Data'
        self.bronze_dir = os.path.join(self.data_path, 'Data-bronze')
        self.silver_dir = os.path.join(self.data_path, 'Data-silver')
        
        # Criar diretórios se não existirem
        os.makedirs(self.bronze_dir, exist_ok=True)
        os.makedirs(self.silver_dir, exist_ok=True)


    def obtem_range_datas(self, date):
        """Calcula o intervalo da semana (domingo a sábado) para uma data"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
            
        start_date = date - timedelta(days=date.weekday() + 1)
        end_date = start_date + timedelta(days=6)
        return start_date.date(), end_date.date()
    
    def cria_url(self, start_date, end_date):
        """Gera a URL com base nas datas de início e fim da semana"""
        year = start_date.year
        return f"{self.url_anp}/{year}/resumo_semanal_lpc_{start_date}_{end_date}.xlsx"
    
    def download_data(self, dates):
        """
        Baixa os dados da ANP para datas específicas
        Args:
            dates (list/str/datetime): Data única ou lista de datas
        """
        if not isinstance(dates, list):
            dates = [dates]

        downloaded_files = []
        for date in dates:
            start_date, end_date = self.obtem_range_datas(date)
            url = self.cria_url(start_date, end_date)
            
            filename = f"resumo_semanal_lpc_{start_date}_{end_date}.xlsx"
            bronze_path = os.path.join(self.bronze_dir, filename)
            
            if os.path.exists(bronze_path):
                print(f'Arquivo {filename} já existe. Pulando download.')
                downloaded_files.append(bronze_path)
                continue

            response = requests.get(url)
            if response.status_code == 200:
                with open(bronze_path, 'wb') as f:
                    f.write(response.content)
                downloaded_files.append(bronze_path)
                print(f'Dados de {start_date} baixados com sucesso')
            else:
                print(f'Falha ao baixar dados para {start_date}')
        
        return downloaded_files

    def process_data(self, bronze_file, concatenate=True):
        """Processa um arquivo baixado e opcionalmente concatena com dados existentes"""
        # Ler e tratar os dados
        df = pd.read_excel(bronze_file, header=None)
        df.columns = df.iloc[9]
        df = df[10:].reset_index(drop=True)
        
        # Adicionar coluna com período de referência
        file_name = os.path.basename(bronze_file)
        date_range = file_name.split('_')[-2:]
        df['periodo_referencia'] = f"{date_range[0]} a {date_range[1].replace('.xlsx','')}"
        
        # Salvar na camada silver
        filename = file_name.replace('.xlsx', '.csv')
        silver_path = os.path.join(self.silver_dir, filename)
        
        # Concatenar os dados     
        self.df_final = pd.concat([self.df_final, df], ignore_index=True)
        
        print(f'Dados processados salvos em: {silver_path}')
        return df

    def salva_dados_silver(self, file_name='dados_combustiveis_anp.csv'):
        """Salva os dados concatenados na camada silver"""
        if not self.df_final.empty:
            combined_path = os.path.join(self.silver_dir, file_name)
            self.df_final.to_csv(combined_path, index=False)
            print(f'Dados combinados salvos em: {combined_path}')
            return combined_path
        else:
            print('Nenhum dado para concatenar.')
            return None

    def download_and_process_range(self, start_date, end_date):
        """Baixa e processa dados para um intervalo de datas"""
        current_date = start_date
        while current_date <= end_date:
            self.download_data(current_date)
            current_date += timedelta(weeks=1)
        
        # Processar e concatenar todos os arquivos baixados
        for file in os.listdir(self.bronze_dir):
            if file.endswith('.xlsx'):
                self.process_data(os.path.join(self.bronze_dir, file))
        
        # Salvar dados combinados
        self.salva_dados_silver()

