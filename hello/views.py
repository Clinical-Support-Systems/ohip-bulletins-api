from django.shortcuts import render
from django.core.cache import cache

from .models import Greeting

# Create your views here.

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from asyncio.windows_events import NULL
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import urljoin

recursion_limit = 1
column_width = 50
url_visited = []
response_text = ""

# urls = ["https://www.ontario.ca/document/ohip-infobulletins-2024",
#             "https://www.ontario.ca/document/ohip-infobulletins-2023",
#             "https://www.ontario.ca/document/ohip-infobulletins-2022/",
#             "https://www.ontario.ca/document/ohip-infobulletins-2021/",
#             "https://www.ontario.ca/document/ohip-infobulletins-2020/"]
urls = ["https://www.ontario.ca/document/ohip-infobulletins-2024"] #Just 2024 to test

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
        return NULL
    elif state == 2:
        if href.startswith(base_url):
            return requests.get(href)
        else: 
            return NULL
    else:
        full_url = urljoin(base_url, href)
        if is_full_url(full_url):
            return requests.get(full_url)
        else:
            return NULL


def recursive_read_bulletin(href, base_url, current_depth = 0):
    global recursion_limit
    global column_width
    excluded_titles = ["Contact information", "Contact Information", "Contact\xa0information", "Keywords/Tags", "Keywords/tags", "Keywords\x2fTags"]
    if current_depth >= recursion_limit:
        return
    url_visited.append(href)
    response_text = ""
    
    bulletinInfo = read_url(href, base_url)
    if bulletinInfo != NULL and bulletinInfo.status_code == 200:     # If we get a valid request for this link to a bulletin let's read it
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
                                    if href not in url_visited and href not in urls and not href.startswith('mailto:') and not href.startswith('tel:'):
                                            res = recursive_read_bulletin(href, base_url, current_depth + 1)
                                            if res is not None:
                                                response_text += res
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
    if response.status_code == 200:
        # HANDLE MAIN URL CONTAINING ALL BULLETINS FO THE YEAR (Example: Bulletins 2024)
        soup = BeautifulSoup(response.text, 'html.parser')
        bulletins = soup.find_all('div', class_='main-content');    # Get all the div element on the main content at bulletins 2024
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
                                response_text += recursive_read_bulletin(href, base_url)  
                response_text += '\n\n'
        return response_text


class OhipBulletinAPIView(APIView):
    def get(self, request, search=None):
        if search is None:
            return Response({"error": "search is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # cached_data = cache.get(search)

        # if cached_data:
        #     return Response(cached_data, status=status.HTTP_200_OK)
            
        # If not in cache, scrape the website
        url_visited = []
        response_text = ""
        for url in urls:
            response_text = scrape_bulletin(url)
        bulletin_info = {
            "bulletinInfo": response_text,
        }
        if bulletin_info:
            # here save cache
            # cache.set(search, bulletin_info, timeout=600) # 10 min cache ~ 600 seconds
            return Response(bulletin_info, status=status.HTTP_200_OK)
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
