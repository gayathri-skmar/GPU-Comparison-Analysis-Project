import time
from selenium import webdriver
from bs4 import BeautifulSoup
import requests
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns

gpu_market_data = []

#This function is used specifically for webscraping from Canada Computers.
#Canada Computers webpage loads in as you scroll. We use Selenium to keep scrolling until the height of the page no longer changes.
def obtain_data_canadacomputers(url, data_record):
    driver = webdriver.Chrome()
    try:
        driver.get(url)
        time.sleep(5)

        last_height = driver.execute_script("return document.body.scrollHeight")
        
        #Scroll to the bottom of the page
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                print("Reached the bottom of the webpage: No more items loading.")
                break

            print("Page is still loading. Continuing.")
            last_height = new_height

        #Obtain all data for the graphic cards
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.find_all('div', class_ = 'product-description')

        #print(f"Scrape Complete! Total items found: {len(cards)}")

        #Extracting name, price and stock information for each graphic card found and then importing it into a list.
        for card in cards:
            name_tag = card.find('h2', class_ = 'h3 product-title mb-0_5')
            name = name_tag.text.strip() if name_tag else "N/A"

            price_tag = card.find('span', class_ = 'price no-sale-price')
            price_raw = price_tag.text.strip() if price_tag else "0"
            price = float(price_raw.replace('$', '').replace(',', '').strip())

            stock_divs = card.find_all('div', class_ = 'line-height mr-0')
            online_stock_raw = stock_divs[0].text.strip() if len(stock_divs) > 0 else "Unknown"
            online_stock = online_stock_raw.replace('Online - ', '').strip()
            instore_stock_raw = stock_divs[1].text.strip()if len(stock_divs) > 1 else "Unknown"
            instore_stock = instore_stock_raw.replace('In Store - ','').strip()

            data_record.append({"Source": "Canada Computers", 
                                "Product Name": name, 
                                "Price": price, 
                                "Online Stock": online_stock, 
                                "In Store Stock": instore_stock})
    finally:
        driver.quit()

#This function is specifically used for webscraping from Newegg. 
def obtain_data_newegg(base_url, data_record):
    page_num = 1

    
    while True:
        #Keep going to the next page until we get a error.
        url = f"{base_url}&page={page_num}"
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        if soup.find('span', class_ = 'result-message-error'):
            print("End of listings.")
            break
        
        #Extract graphic card information from each page and import into list.
        cards = soup.find_all('div', 'item-container position-relative')
        for card in cards:
            name_tag = card.find('a', class_ = 'item-title')
            name = name_tag.text.strip() if name_tag else 'N/A'

            price_tag = card.find('li', class_ = 'price-current')
            if price_tag and price_tag.find('strong'):
                dollars = price_tag.find('strong').text.replace(',', '').strip()
                cents = price_tag.find('sup').text.strip()
                price = float(f"{dollars}{cents}")
            else:
                price = 0

            stock = 'Available to Ship' if card.find('button', class_ = 'btn btn-primary btn-mini') else 'Out of Stock'

            data_record.append({"Source": "Newegg", 
                                "Product Name": name, 
                                "Price": price, 
                                "Online Stock": stock, 
                                "In Store Stock": 'N/A'})
        
        #Move onto next page
        page_num += 1
        time.sleep(1)

#This function is used to classify each graphics card without its manufacturer.
def categorize_gpu(name):
    name_upper = name.upper()
    for m in model_names: 
        if m in name_upper:
            return m
    return "Other"

#Obtain all graphics card purchasing info from Canada Computers
obtain_data_canadacomputers('https://www.canadacomputers.com/en/search?s=nvidia+rtx+5070+ti', gpu_market_data)
obtain_data_canadacomputers('https://www.canadacomputers.com/en/search?s=amd+rx+9070+xt&category=Graphics%2520Cards%257C914', gpu_market_data)
obtain_data_canadacomputers('https://www.canadacomputers.com/en/search?s=NVIDIA+RTX+5060+TI&t=1', gpu_market_data)
obtain_data_canadacomputers('https://www.canadacomputers.com/en/search?s=amd+rx+9060+xt&category=Graphics%2520Cards%257C914', gpu_market_data)
obtain_data_canadacomputers('https://www.canadacomputers.com/en/search?s=NVIDIA+RTX+5050&t=1', gpu_market_data)

#Obtain all graphics card purchasing info from Newegg
obtain_data_newegg('https://www.newegg.ca/p/pl?d=geforce+rtx+5070+ti', gpu_market_data)
obtain_data_newegg('https://www.newegg.ca/p/pl?d=AMD+RX+9070+XT', gpu_market_data)
obtain_data_newegg('https://www.newegg.ca/p/pl?d=NVIDIA+RTX+5060+TI', gpu_market_data)
obtain_data_newegg('https://www.newegg.ca/p/pl?d=AMD+RX+9060+XT', gpu_market_data)
obtain_data_newegg('https://www.newegg.ca/p/pl?d=NVIDIA+RTX+5050', gpu_market_data)

#Convert all webscraping results into a dataframe and then into a csv file so that we won't have to webscrape again.
df = pd.DataFrame(gpu_market_data)
df.to_csv('gpu_search_results.csv', index=False)

#Performance scores found from https://www.videocardbenchmark.net/high_end_gpus.html
gpu_performance_score = {"RTX 5050": 17160, 
                         "RTX 5060 TI": 22263, 
                         "RTX 5070 TI": 32428,
                         "RX 9060 XT": 20125,
                         "RX 9070 XT": 26910}


gpu_search_results = pd.read_csv('gpu_search_results.csv')

#Remove all store items which are not strictly classified as a graphics card
noise_keywords = ['PC', 'DESKTOP', 'SYSTEM', 'COMPUTER']
#Just in case we try to clean the df again
clean_df = gpu_search_results[~gpu_search_results['Product Name'].str.upper().str.contains('|'.join(noise_keywords))].copy()

model_names = ['RTX 5050', 'RTX 5060 TI', 'RTX 5070 TI', 'RX 9060 XT', 'RX 9070 XT']

#Go through all results and categorize the GPUs
clean_df["General Model"] = clean_df["Product Name"].apply(categorize_gpu)

#Calculate average price among all results across all websites for each graphics card
avg_prices = clean_df.groupby("General Model")["Price"].mean()

#Obtain Average Price, STD Price, Performance Score, and Price per Performance for each graphics card type
tier_stats = clean_df.groupby("General Model")["Price"].agg(["mean", "std"]).reset_index()
tier_stats.columns = ["General Model", "Average Price", "STD Price"]
tier_stats["Performance Score"] = tier_stats["General Model"].map(gpu_performance_score)
tier_stats["Price per Performance"] = tier_stats['Average Price'] / tier_stats["Performance Score"]

#Merge these stats with original dataframe
clean_df = clean_df.merge(tier_stats, on = "General Model")

#Find overpriced graphics cards
overpriced_mask = clean_df["Price"] > (clean_df["Average Price"] + clean_df["STD Price"])
overpriced_cards =  clean_df.loc[overpriced_mask, ["Product Name", "Price", "Average Price"]]

#Setting up the graph to show prices and performance for each model as well as identifying the 'value kings'
sns.set_style("whitegrid")
plt.figure(figsize=(12,8))

sns.scatterplot(data=clean_df, x = "Performance Score", y = "Price", hue = "General Model", alpha = 0.6, s = 100)
trend_data = tier_stats.sort_values('Performance Score')
plt.plot(trend_data["Performance Score"], trend_data["Average Price"], color = "red", linestyle = "--", label = "Market Average Trend")

value_kings = clean_df.nsmallest(3, "Price per Performance")
for i, row in value_kings.iterrows():
    plt.annotate(row["Product Name"][:20] + "...",
                 xy = (row['Performance Score'], row["Price"]), 
                 xytext = (15,15), textcoords = "offset points",
                 arrowprops = dict(arrowstyle="->", color="black"),
                 fontsize = 9, fontweight = "bold")

plt.title("GPU Comparison Analysis: Price Vs. Performance", fontsize = 16)
plt.xlabel("Performance Score", fontsize = 12)
plt.ylabel("Price ($)", fontsize = 12)
plt.legend(title="GPU Tier")
plt.tight_layout()

plt.show()