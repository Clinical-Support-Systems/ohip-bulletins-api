from urllib import response
from django.shortcuts import render
from django.core.cache import cache

from .models import Greeting

# Create your views here.

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import urljoin
from datetime import datetime, timedelta

# urls = ["https://www.ontario.ca/document/ohip-infobulletins-2024",
#             "https://www.ontario.ca/document/ohip-infobulletins-2023",
#             "https://www.ontario.ca/document/ohip-infobulletins-2022/",
#             "https://www.ontario.ca/document/ohip-infobulletins-2021/",
#             "https://www.ontario.ca/document/ohip-infobulletins-2020/"]
urls = ["https://www.ontario.ca/document/ohip-infobulletins-2024"] #Just 2024 to test
last_year_bulletins = "https://www.ontario.ca/document/ohip-infobulletins-2024"

# Helper function to scrape
def is_full_url(href):
    parsed_url = urlparse(href)
    path = parsed_url.path
    if path.endswith('.pdf'): 
        return 1
    elif bool(parsed_url.scheme and parsed_url.netloc):
        return 2
    else:
        return 3

def read_url(href, base_url):
    state = is_full_url(href)
    if  state == 1:
        # Are we going to handle PDF?
        return None
    elif state == 2:
        if href.startswith(base_url):
            return requests.get(href)
        else: 
            return None
    else:
        full_url = urljoin(base_url, href)
        if is_full_url(full_url):
            return requests.get(full_url)
        else:
            return None


# We are not reading any URL inside each bulletin because we have limited text size to return to GPT
def read_bulletin(href, base_url):
    column_width = 50
    excluded_titles = ["Contact information", "Contact Information", "Contact\xa0information", "Keywords/Tags", "Keywords/tags", "Keywords\x2fTags"]
    response_text = ""
    
    bulletinInfo = read_url(href, base_url)
    if bulletinInfo != None and bulletinInfo.status_code == 200:     # If we get a valid request for this link to a bulletin let's read it
        soup = BeautifulSoup(bulletinInfo.text, 'html.parser')
        response_text += soup.title.get_text() + '\n'
        div_info = soup.find_all('div', class_='body-field')
        for div in div_info:           
            titles2 = div.find_all(['h2', 'div'], recursive=False)
            for title2 in titles2:
                title_content = title2.text.strip() 
                accordions = title2.find_all('div', class_='accordion')
                if len(accordions) > 0: 
                    for accordion in accordions:
                        tables = accordion.find_all('table')
                        if len(tables) > 0:
                            response_text += accordion.find('h3').text.strip()
                            for table in tables:
                                rows = table.find_all('tr')
                                for row in rows:
                                    columns = row.find_all(['th', 'td'])
                                    row_text = "\t".join([col.get_text(strip=True).ljust(column_width) for col in columns])
                                    response_text += row_text      
                        else:
                            response_text += title_content                                       
                else:
                    if(title_content not in excluded_titles):
                        response_text += title_content                  
                        
                if(title_content not in excluded_titles):
                    for sibling in title2.find_next_siblings():
                        if sibling.name == 'h2':
                            break
                        elif sibling.name in ['ol', 'ul']:
                            # HANDLE FILES INSIDE EACH BULLETING
                            a_tags = sibling.find_all('a')              # Get links
                            if len(a_tags) > 0:
                                for a in a_tags:
                                    href = a.get('href')
                                    response_text += a.get_text() + '\n'
                            else:
                                for elem in sibling.children:
                                    response_text += elem.get_text()
                        elif sibling.name in ['p']:
                            result = []
                            for elem in sibling.children:
                                if elem.name == 'br':
                                    result.append('\n')
                                else:
                                    result.append(elem.get_text() if hasattr(elem, 'get_text') else str(elem))
                            response_text += ''.join(result)
                        elif sibling.name in ['dl', 'dt', 'h3']:
                            for elem in sibling.children:
                                text = elem.get_text(separator=" ", strip=True)
                                response_text += text
                    response_text += '\n'
    return response_text + '\n'    

def scrape_bulletin(url):
    response = requests.get(url)
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    response_text = ""
    url_visited = []
    if response.status_code == 200:
        # HANDLE MAIN URL CONTAINING ALL BULLETINS FO THE YEAR (Example: Bulletins 2024)
        soup = BeautifulSoup(response.text, 'html.parser')
        bulletins = soup.find_all('div', class_='main-content')    # Get all the div element on the main content at bulletins 2024
        for bulletin in bulletins:
            titles = bulletin.find_all('h2')                        # Find all H2 elements
            for title in titles:
                response_text += title.text.strip() + '\n'          # Print the title
                for sibling in title.find_next_siblings():
                    if sibling.name == 'h2':
                        break
                    if sibling.name == 'ul':                        # If there is a ul bellow the h2 let's check if are links to bulletins
                        a_tags = sibling.find_all('a')              # Get links
                        for a in a_tags:
                            href = a.get('href')
                            if href not in url_visited:
                                # HANDLE EACH BULLETIN ON THE PAGE
                                response_text += read_bulletin(href, base_url) 
                                url_visited.append(href)
                response_text += '\n\n'
        return response_text, url_visited

def get_updated_urls(url):
    response = requests.get(url)
    url_visited = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        bulletins = soup.find_all('div', class_='main-content');
        for bulletin in bulletins:
            uls = bulletin.find_all('ul')
            for ul in uls: 
                a_tags = ul.find_all('a')
                for a in a_tags:
                    href = a.get('href')
                    if href not in url_visited:
                        url_visited.append(href)
    return url_visited

class OhipBulletinAPIView(APIView):
    def get(self, request, search=None):        
        cached_data = cache.get("bulletin")

        if cached_data:
            current_time = datetime.now()
            time_diff = current_time - cached_data["timestamp"]
            if time_diff < timedelta(hours = 24):
                return Response(cached_data["bulletinInfo"], status=status.HTTP_200_OK)
            else:
                updated_urls = get_updated_urls(last_year_bulletins) # read current bullentins link
                updated_status = True
                for updated_url in updated_urls:
                    if updated_url not in cached_data["urls"]:
                        updated_status = False
                if updated_status:
                    return Response(cached_data["bulletinInfo"], status=status.HTTP_200_OK) 
                
            
        # If not in cache, or if it is in cache but is not updated scrape the website
        url_visited = []
        response_text = ""
        for url in urls:
            r_text, r_url = scrape_bulletin(url)
            response_text += r_text
            url_visited += r_url
            
        bulletin_cache = {
            "bulletinInfo": response_text[:50000],
            "urls": url_visited,
            "timestamp" : datetime.now()
        }

        if bulletin_cache:
            # here save cache
            cache.set("bulletin", bulletin_cache, timeout=600) # 10 min cache ~ 600 seconds
            return Response(response_text[:50000], status=status.HTTP_200_OK)
        else:
            return Response({"error": "Could not fetch OHIP Bulletin data"}, status=status.HTTP_400_BAD_REQUEST)



def index(request):
    return render(request, "index.html")

def db(request):
    # If you encounter errors visiting the `/db/` page on the example app, check that:
    #
    # When running the app on Heroku:
    #   1. You have added the Postgres database to your app.
    #   2. You have uncommented the `psycopg` dependency in `requirements.txt`, and the `release`
    #      process entry in `Procfile`, git committed your changes and re-deployed the app.
    #
    # When running the app locally:
    #   1. You have run `./manage.py migrate` to create the `hello_greeting` database table.

    greeting = Greeting()
    greeting.save()

    greetings = Greeting.objects.all()

    return render(request, "db.html", {"greetings": greetings})
