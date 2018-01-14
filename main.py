# coding=utf-8
import requests
import threading
from html.parser import HTMLParser
import glob
from itertools import zip_longest
import platform
import datetime
import os


# Oma toteutus HTMLParser luokasta
class CoinMarketCapParser(HTMLParser):
    def __init__(self, name):
        HTMLParser.__init__(self)
        self.coin_name = name
        self.current_tag = None
        self.market_data = []      # Kaikkia päiviä koskeva data
        self.current_data = []     # Yhtä päivää koskeva data
        self.open_source = "0"       # 0 = False, 1 = True
        self.token_or_coin = "-"  # Arvon pitäisi olla token tai coin

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == "span" and ('title', 'Source Code') in attrs:
            self.open_source = "1"

    def handle_endtag(self, tag):
        # Tässä kohtaa loppuu yhtä päivää koskeva data,
        # jolloin sitä koskevat lista alustetaan
        if tag == "tr":
            if self.current_data:
                self.market_data.append(self.current_data)
            self.current_data = []
        # Tässä kohtaa koko taulukko loppuu, jolloin tiedot kirjoitetaan tiedostoon
        if tag == "tbody":
            with open("coins/"+self.coin_name+".csv", "w") as f:
                for date_data in self.market_data:
                    date_string = date_data[0]
                    date = datetime.datetime.strptime(date_string, "%b %d, %Y")
                    f.write(str(date.date().strftime("%d.%m.%Y"))+";")
                    for value in date_data[1:]:
                        f.write(value+";")
                    #print(self.token_or_coin + " " + self.open_source)
                    f.write(self.token_or_coin + ";")
                    f.write(self.open_source + ";")
                    f.write("\n")
            # Tässä kohtaa voisi kutsua close() funktiota, jolloin lopputiedostoa ei luettaisi, mutta
            # en saanut sitä toimimaan
        self.current_tag = None

    # Käsittelee tagin sisällä olevan datan
    def handle_data(self, data):
        # td tägien sisällä on kaikki hintadata mitä tarvitaan
        if self.current_tag == "td":
            self.current_data.append(data)
        elif self.current_tag == "span":
            if data == "Coin":
                self.token_or_coin = "coin"
            elif data == "Token":
                self.token_or_coin = "token"



def process_coin(coin_name):
    date_string = datetime.date.today().strftime("%Y%m%d")
    url = "https://coinmarketcap.com/currencies/"+coin_name+"/historical-data/?start=20130428&end="+date_string
    print(url)
    #try:
    response = requests.get(url)
    data_text = response.text
    if "No data was found for the selected time period." in data_text:
        print(coin_name + ": Ei löytynyt dataa")
        return
    elif response.status_code == 200:
        parser = CoinMarketCapParser(coin_name)
        parser.feed(data_text)
    #print(coin_name + " - OK")
    #except urllib.error.HTTPError:
    #    # Tätä kolikkoa ei löytynyt
    #    pass

def get_coin_name_from_file_name(file_name):
    if platform.system() == "Windows":
        return file_name.split(".")[0].split("\\")[1]
    else:
        return file_name.split(".")[0].split("/")[1]

# Ohjelman suoritus alkaa tästä
if __name__ == '__main__':

    # Luetaan etsittävien coinien nimet
    name_file = "name_list.txt"
    with open(name_file) as f:
        name_list = [line.strip() for line in f]

    # Rinnakkainen toteutus
    threads = [threading.Thread(target=process_coin, args=(name,)) for name in name_list]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


    # Toteutus ilman rinnakkaisuutta
    #for name in name_list:
    #    process_coin(name)


    ''' HUOM: Tätä voi käyttää kirjoittamaan tiedoston kuten aluksi oli, että coinit ovat päällekkäin
    count = 0
    with open("all_coins.csv", encoding='utf-8', mode="w") as file_all:
        for file_name in glob.glob("coins/*.csv"):
            count += 1
            name = file_name.split(".")[0].split("\\")[1]
            file_all.write(name+"\n")
            with open(file_name, encoding='utf-8') as f:
                file_all.write(str(f.read()))
            #file_all.write("\n")
    '''

    count = 0
    not_modified_count = 0
    # Listataan löydetyt coinien nimet coins-kansion CSV-tiedostojen perusteella
    found_names = [get_coin_name_from_file_name(file_name) for file_name in glob.glob("coins/*.csv")]
    with open("all_coins.csv", encoding='utf-8', mode="w") as file_all:
        # Kaikki pvm rivit muodossa:
        # [pvm1, pvm2, pvm3][pvm1, pvm2, pvm3][pvm1, pvm2, pvm3] ...
        all_row_lists = []

        # Aluksi kirjoitetaan ylimmälle riville pelkästään kaikki nimet
        for name in found_names:
            file_all.write(name+"; Date; Open; High; Low; Close; Volume; Market Cap; Type; Open source;")
        file_all.write("\n")


        for file_name in glob.glob("coins/*.csv"):
            count += 1
            file_stats = os.stat(file_name)
            modified_time = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            now = datetime.datetime.now()
            ago = now-datetime.timedelta(minutes=5)
            if modified_time < ago:
                not_modified_count += 1
            name = get_coin_name_from_file_name(file_name)
            with open(file_name, encoding='utf-8') as f:
                row_list = [line.strip() for line in f.readlines()]
                all_row_lists.append(row_list)
                #file_all.write("\n")

        empty_value = "-;-;-;-;-;-;-;-;-;"  # Tyhjät arvot korvataan tällä
        # [pvm1, pvm1, pvm1][pvm2, pvm2, pvm2]...
        zipped = zip_longest(*all_row_lists, fillvalue=empty_value)
        for row in zipped:
            for coin_data in row:
                file_all.write(str(" ;"+coin_data))
            file_all.write("-;" * (9-len(coin_data)))
            file_all.write("\n")

    print("Coins in all_coins file: "+str(count) + "/" + str(len(name_list)))
    print(str(not_modified_count) + " coins have not been modified within 5 minutes")
    not_found_file = open("not_found_list.txt", "w")
    for name in set(name_list) - set(found_names):
        not_found_file.write(name + "\n")
    print("Coins that were not found are written in not_found_list.txt")