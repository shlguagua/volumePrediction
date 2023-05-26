import os
import click
import pandas as pd
import datetime
import traceback
from jqdatasdk import *
import cn_stock_holidays.data as shsz

class JQDataLoader():
    
    def __init__(self, date, data_dir):
        
        self.date = date
        self.date_str = self.date.strftime('%Y%m%d')
        self.data_dir = data_dir
    
    @staticmethod
    def authentication():
        username = '18140562236'
        password = 'Sinoalgo123'
        auth(username, password)
    
    def load_market_data(self, ukeys):
        
        data_list = []
        date_folder_str = self.date.strftime('%Y/%m/%d')
        for ukey in ukeys:
            marketType = ukey.rsplit('.')[-1]
            dir_name = f'{os.path.expanduser("~")}/security/JQMarketData/STOCK/{marketType}/{date_folder_str}'
            if not os.path.exists(dir_name):
               os.makedirs(dir_name)

            
            print(f'loading tick data for {ukey}')
            try:
                df = get_ticks(ukey, start_dt = self.date, end_dt = (self.date + datetime.timedelta(days = 1)))
                df = self.format_ticket_data(df)
                print(f"Downloading data for {security} on {date}")
                df.to_csv(os.path.join(dir_name, ukey) + '.gz', index = False, compression = 'gzip')
            except:
                print(f'failed to load tick data for {ukey}')
    
    @staticmethod
    def format_ticket_data(data):
        
        data['time'] = data['time'].apply(lambda x: str(x).replace("-", "").replace(":", "").replace(" ", "") + "000")
        priceCols = ['current', 'high', 'low'] + [ x for x in data.columns if x[-1] == 'p']
        for col in priceCols:
            data[col] = data[col].apply( lambda x: int(round(x*10000)) )
        
        volCols = ['volume'] + [x for x in data.columns if x[-1] == 'v']
        for col in volCols:
            data[col] = data[col].apply( lambda x: int(x) )
        
        return data
    
    def run(self):
        
        if not os.path.exists(f'{os.path.expanduser("~")}/security_file/'):
           os.mkdir(f'{os.path.expanduser("~")}/security_file/')

        
        security_df = get_all_securities(types = ['stock'], date = self.date).reset_index()
        security_df.rename({'index' : 'code'}, axis = 1, inplace = True)
        
        ukeys = security_df['code'].tolist()
        close_df = get_price(ukeys, start_date = self.date, end_date = self.date, fields = ['open', 'close', 'high', 'low', 'volume', 'money', 'high_limit', 'low_limit', 'factor'])
        
        # add check_is_st information
        extras = get_extras('is_st', ukeys, start_date = self.date, end_date = self.date)
        
        def check_is_st(code, time):
            return 1 if extras.loc[time, code] else 0
        
        close_df['is_st'] = close_df.apply(lambda x: check_is_st(x['code'], x['time']), axis = 1)
        close_df = close_df.drop_duplicates(['code'])
        
        security_df = security_df.merge(close_df[['code', 'close', 'high_limit', 'low_limit', 'is_st', 'factor']], on = ['code'], how = 'left')
        security_df.to_csv(f'{os.path.expanduser("~")}/security_file/{self.date_str}_stocks.csv.gz', index = False, compression = 'gzip')

        
        self.load_market_data(ukeys)
        date_folder_str = self.date.strftime('%Y/%m/%d')

        os.system(f'chmod 777 -R {self.data_dir}/security_file/')
        os.system(f'chmod 777 -R {self.data_dir}/JQMarketData/STOCK/XSHE/{date_folder_str}')
        os.system(f'chmod 777 -R {self.data_dir}/JQMarketData/STOCK/XSHG/{date_folder_str}')


@click.command()
@click.option("--start_date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date in format 'YYYY-MM-DD'")
@click.option("--end_date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]), help="End date in format 'YYYY-MM-DD'")
@click.option("--today", is_flag=True, help="If specified, downloads data for today's date")
def main(start_date, end_date, today):
    if today:

        today_date = datetime.date.today()
        while not shsz.is_trading_day(today_date) or datetime.datetime.now() < datetime.datetime(year=today_date.year, month=today_date.month, day=today_date.day, hour=15):
            today_date -= datetime.timedelta(days=1)
        prev_date = today_date - datetime.timedelta(days=1)
        while not shsz.is_trading_day(prev_date):# or datetime.datetime.now() < datetime.datetime(year=today_date.year, month=today_date.month, day=today_date.day, hour=15):
            prev_date -= datetime.timedelta(days=1)
        dates = [today_date, prev_date]
    else:
        dates = [i.date() for i in pd.date_range(start_date, end_date, freq = 'D')]
        dates = [date for date in dates if shsz.is_trading_day(date)]

# create the directory if it doesn't exist
data_dir = '/volume/sinoalgo'
security_dir =  "~/security"
if not os.path.exists(security_dir):
    os.makedirs(security_dir)
    JQDataLoader.authentication()
    for date in dates:
        print(f'Running {date}')
        try:
            loader = JQDataLoader(date, '/volume/sinoalgo')
            loader.run()
        except Exception as e:
            print(f'failed to load data for {date}')
            print(traceback.format_exc())

if __name__ == '__main__':
    main()
