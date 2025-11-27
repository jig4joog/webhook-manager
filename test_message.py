import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta, datetime, timezone
from discord_webhook import DiscordWebhook, DiscordEmbed
# import random
import time
# import timeit
import json
import re
# import cook_groups_test as c
# import pytz
# import mysql.connector
# from urllib.parse import urljoin
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests_html2 import HTMLSession
from curl_cffi import requests

from db import SessionLocal
from models import Group, Service, GroupService

def send_message_db():
    session = SessionLocal()
    message_test = "test message"

    enabled_links = session.query(GroupService).filter_by(enabled=True).all()
    for link in enabled_links:
        group = link.group
        service = link.service

        # Prefer per-service webhook; fall back to group webhook if None
        webhook_url = link.webhook_url or group.webhook_url
        if not webhook_url:
            continue  # nothing to send to

        webhook = DiscordWebhook(url=webhook_url, username=group.name)
        embed = DiscordEmbed(
            title=f"Test for {service.name} and {group.name}",
            description=message_test,
            color=group.color,
        )
        embed.set_footer(text=group.webhook_footer, icon_url=group.webhook_footer_img)
        webhook.add_embed(embed)
        response = webhook.execute(remove_embeds=True)

    session.close()

send_message_db()

def discord_unix_timestamp(timestamp):
    # Convert the string to a datetime object
    # date_object = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    # date_object = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    formats = ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ']
    for format_string in formats:
        try:
            date_object = datetime.strptime(timestamp, format_string)
            # print("Date:", date_object)
            break  # Break out of loop if parsing succeeds
        except ValueError:
            pass  # Continue to next format if parsing fails

    # Convert the datetime object to a Unix timestamp (seconds since 1970-01-01)
    unix_timestamp = int(date_object.replace(tzinfo=timezone.utc).timestamp())

    # Format the Discord timestamp string
    discord_timestamp = f"<t:{unix_timestamp}:f>"
    return discord_timestamp

def dsm(url, retailer):
    payload = {}
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    soup = BeautifulSoup(response.content, 'html.parser')
    food_dict = []

    headers_text = soup.find_all('h3')
    for input_string in headers_text:
        # Split the string using 'RAFFLE CLOSES:' as the keyword
        parts = input_string.text.split('RAFFLE CLOSES:')

        # Extract the two parts
        launch_info = parts[0].strip()
        raffle_closes_info = 'RAFFLE CLOSES: ' + parts[1].strip()
        # print(raffle_closes_info, launch_info)

    img_tags = soup.find_all('img')
    img_srcs = [img['src'] for img in img_tags if 'src' in img.attrs]

    # Print the image sources
    for src in img_srcs:
        final_img = 'https:' + src
        # print('https:' + src)

    # Find all <strong> tags
    strong_tags = soup.find_all('strong')

    # Extract the text content from each <strong> tag and print it
    strong_texts = [tag.get_text() for tag in strong_tags]

    # Print the strong texts
    for text in strong_texts:
        if 'raffle' in text.lower():
            final_text = text.replace('below:','').strip()
            # print(final_text)

    if final_img not in url_list:
        food_list = {
            'title': '',
            'url_link': url,
            'img_link': final_img,
            'retailer': retailer,
            'desc': final_text + '\n\n' + launch_info + '\n\n' + raffle_closes_info,
        }
        food_dict.append(food_list)
        # sql_insert = "INSERT INTO eql (title_name, retailer, url) VALUES (%s, %s, %s)"
        # sql_values = (food_list['title'], food_list['retailer'], food_list['img_link'] )
        # mycursor.execute(sql_insert, sql_values)

    food_df = pd.DataFrame(food_dict)
    if len(food_df) == 0:
        # pass
        return 0
    else:
        for i in range(0, len(food_df)):
            for z in c.groups.values():
                name = z['name']
                webhook_footer = z['webhook_footer']
                color = z['color']
                whop_url = z['whop_url']
                webhook_footer_img = z['webhook_footer_img']
                webhook = z['webhook']

                webhook_name = DiscordWebhook(url=webhook, username=name)
                embed = DiscordEmbed(title="{}{}".format(retailer, ' New Raffle'),description='{}'.format(food_df['desc'][i]), color=color)
                embed.add_embed_field(name="Retailer", value=food_df['retailer'][i], inline=True)
                embed.add_embed_field(name="Link", value="[{}]({})".format("Click here for raffle link",food_df['url_link'][i]), inline=True)

                embed.set_footer(text=webhook_footer, icon_url=webhook_footer_img)
                embed.set_image(url=food_df['img_link'][i])

                webhook_name.add_embed(embed)
                response = webhook_name.execute(remove_embeds=True)

def triage_webhook(response_code, service):
    if response_code == 200:
        for z in c.groups_triage.values():
            name = z['name']
            webhook_footer = z['webhook_footer']
            color = z['color']
            whop_url = z['whop_url']
            webhook_footer_img = z['webhook_footer_img']
            webhook = z['webhook']

            webhook_name = DiscordWebhook(url=webhook, username=name)

            embed = DiscordEmbed(title="Triage - Check Webhook", description='{}'.format(service), color=color)
            webhook_name.add_embed(embed)
            response = webhook_name.execute(remove_embeds=True)

def convert_to_unix_timestamp(date_str):
    if date_str.lower() == "varies":
        return "Varies"
    else:
        try:
            # Parse the date string to a datetime object
            date_obj = datetime.strptime(date_str, "%m/%d/%y")

            # Get the current date and time
            current_date = datetime.now()

            # Convert the datetime object to a Unix timestamp
            unix_timestamp = int(date_obj.timestamp())

            # Compare the date with the current date
            if date_obj >= current_date:
                return '<t:{}:D>'.format(unix_timestamp)
            else:
                return 0
        except ValueError:
            return "Invalid date format"

def convert_json_url(original_url):
    # Split the URL to get the base URL and the path
    base_url = "https://soleplay.runfair.com"
    path = original_url.replace(base_url, "")

    # Construct the new URL
    new_url = f"{base_url}/page-data{path}/page-data.json"
    return new_url

url = 'https://visitstore.bio/capitalonecafe'

def main_selenium():
    options = uc.ChromeOptions()
    # options.headless = True  # Enable headless mode
    # options.add_argument("--window-size=1920,1080")  # Recommended for headless to set window size

    driver = uc.Chrome(options=options)
    driver.get('https://www.hyatt.com/explore-hotels/service/avail/days?spiritCode=itmph&startDate=2026-01-01&endDate=2026-11-01&roomCategory=STANDARD_ROOM&numAdults=1&numChildren=0&roomQuantity=1&los=3&isMock=false')
    time.sleep(5)
    # headers = {
    #     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    #     }
    # proxy = {
    #     'http': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
    #     'https': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
    # }
    # response = requests.get(url, proxies=proxy)
    # Option 1: Find an element containing JSON text (example selector)
    json_element = driver.find_element("css selector", "pre")  # or correct selector
    json_text = json_element.text

    data = json.loads(json_text)
    print(data)
    # time.sleep(10)
    # print(soup)
    time.sleep(10)

    # Current date
    current_date = datetime.now()  # Use datetime.today() if you want only the date part
    chrome_options = Options()

    # chrome_options.add_argument("--headless")  # Enable headless mode
    # chrome_options.add_argument("--no-sandbox")  # Required for some Linux environments
    # chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    # set up Chrome
    driver = webdriver.Chrome(options=chrome_options)

    # ...
    # open the target website
    # driver.get("https://playbycourt.com/book/ipicklewhittiernarrows")
    # driver.get('https://www.hyatt.com')
    # driver.get('https://www.hyatt.com/explore-hotels/service/avail/days?spiritCode=itmph&startDate=2026-01-01&endDate=2026-11-01&roomCategory=STANDARD_ROOM&numAdults=1&numChildren=0&roomQuantity=1&los=3&isMock=false')

    user_email = 'seanlinh6@gmail.com'
    user_pass = 'Box12345'
    time.sleep(10)
    # print(driver.page_source)

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        }
    proxy = {
        'http': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
        'https': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
    }
    response = requests.get(url, proxies=proxy)
    soup = BeautifulSoup(response.content, 'html.parser')
    # soup = BeautifulSoup(driver.page_source, 'html.parser')
    print(soup)
    # table = soup.find('div', class_='productsContainer__2w_QF')
    # href_links = [link.get('href') for link in soup.find_all('a') if link.get('href')]

    # print(href_links)

# main_selenium()

# url = 'https://gdx-api.costco.com/catalog/product/product-api/v2/display-price-lite?whsNumber=847&clientId=4900eb1f-0c10-4bd9-99c3-c59e6c1ecebf&item=1592075&locale=en-us'
# headers = {
#     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
#     }
# proxy = {
#     'http': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
#     'https': 'http://ARbWpQ54wGeq5UVB:p8Q730XxBHr0Fh8D_country-us@geo.iproyal.com:12321',
# }
# response = requests.get(url)
# print(response)
# resp = curl_cffi.requests.get(url, http_version="1.1")
# soup = BeautifulSoup(response.content, 'html.parser')
# table = soup.find('div', class_='productsContainer__2w_QF')

# date_text = soup.find('span', class_='LeaderBoardWithButtons_lbwbDate__gsMEu').text
# date_object = datetime.strptime(date_text, "%m/%d/%Y").date()
# print(date_object)

# print(soup)
# for data in table:
#     player_record = data.find_all('tr', class_='LeaderBoardPlayerCard_lbpcTableRow___Lod5')
#     for player_data in player_record:
#         # print(player_data.text)
#
#
#         player_score = int(player_data.text[-2:])
#         player_name = player_data.text.split()[1]
#
#         if player_score >= 50:
#             print('works')
#             break
#         else:
#             print('fail')




