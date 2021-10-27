import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
import time
import json
import glob
import unicodedata


BASE_URL = 'https://www.akc.org/dog-breeds/'


def init_browser() -> WebDriver:  # sourcery skip: inline-immediately-returned-variable
  service = Service('/Users/michaellong/Projects/geckodriver 2')
  opts = Options()
  # running headless causes a memory error for some reason
  # opts.headless = True
  browser = webdriver.Firefox(options=opts, service=service)
  return browser


def get_breeds() -> list:
  page = requests.get(BASE_URL)

  soup = BeautifulSoup(page.content, 'html.parser')
  breeds = [str(breed.text) for breed in soup.find_all('option')]
  del breeds[0]
  yorkshire = breeds.index('Yorkshire Terrier')
  return breeds[:yorkshire+1]


def restart_browser(browser: WebDriver) -> WebDriver:
  browser.quit()
  time.sleep(5)
  browser = init_browser()
  return browser


def dump_current_data(breed_info: dict, browser: WebDriver, count: int) -> WebDriver:
  with open(f'./public/dog_breeds_{count}.json', 'w') as json_file:
    json.dump(breed_info, json_file, indent=2, ensure_ascii=False)
  breed_info = {}
  return restart_browser(browser)


def set_breed_traits(trait_div, breed_info: dict, breed: str) -> dict:
  trait_name = trait_div.find_element(By.TAG_NAME, 'h4')
  trait_name = trait_name.get_attribute('textContent')
  level = len(trait_div.find_elements(By.CLASS_NAME, 'breed-trait-score__score-unit--filled'))
  breed_info[breed][trait_name] = level
  if level == 0:
    traits = trait_div.find_elements(By.CLASS_NAME, 'breed-trait-score__choice--selected')
    traits = [trait.find_element(By.TAG_NAME, 'span').get_attribute('textContent') for trait in traits]
    breed_info[breed][trait_name] = traits
  return breed_info


def open_breed_web_page(breed_name: str, browser: WebDriver) -> int:
  url_compatible_breed = '-'.join(breed_name.split(' '))
  breed_url = f'{BASE_URL}{url_compatible_breed}/'

  if requests.get(breed_url).status_code == 404:
    return 404

  browser.get(breed_url)
  time.sleep(2)
  return 200


def set_breed_info(breed_info: dict, breed: str, overview_subtitles: list) -> dict:
  try:
    if len(overview_subtitles) == 7:
      breed_info[breed]['Height'] = [overview_subtitles[0], overview_subtitles[1], overview_subtitles[2]]
      breed_info[breed]['Weight'] = [overview_subtitles[3], overview_subtitles[4], overview_subtitles[5]]
      breed_info[breed]['Life Expectancy'] = overview_subtitles[6]
    elif len(overview_subtitles) == 5:
      breed_info[breed]['Height'] = [overview_subtitles[0], overview_subtitles[1]]
      breed_info[breed]['Weight'] = [overview_subtitles[2], overview_subtitles[3]]
      breed_info[breed]['Life Expectancy'] = overview_subtitles[4]
    elif len(overview_subtitles) == 4:
      breed_info[breed]['Height'] = [overview_subtitles[0], overview_subtitles[1]]
      breed_info[breed]['Weight'] = overview_subtitles[2]
      breed_info[breed]['Life Expectancy'] = overview_subtitles[3]
    else:
      breed_info[breed]['Height'] = overview_subtitles[0]
      breed_info[breed]['Weight'] = overview_subtitles[1]
      breed_info[breed]['Life Expectancy'] = overview_subtitles[2]
  except IndexError:
    print(f"{breed} probably didn't scrape properly. Fix it manually.")
    breed_info[breed]['Height'] = ''
    breed_info[breed]['Weight'] = ''
    breed_info[breed]['Life Expectancy'] = ''

  return breed_info


def set_breed_stats(browser: WebDriver, breeds: dict, breed_name: str) -> dict:
  # overview_titles = [
  #   overview.get_attribute('textContent')
  #   for overview in browser.find_elements(
  #     By.CLASS_NAME, 'breed-page__hero__overview__title')
  # ]
  overview_subtitles = [
    overview.get_attribute('textContent')
    for overview in browser.find_elements(
      By.CLASS_NAME, 'breed-page__hero__overview__subtitle')
  ]

  breeds = set_breed_info(breeds, breed_name, overview_subtitles)

  trait_divs = browser.find_elements(By.CLASS_NAME, 'breed-trait-group__trait-all')
  for trait_div in trait_divs:
    breeds = set_breed_traits(trait_div, breeds, breed_name)

  return breeds


def scrape_for_dog_info():
  browser = init_browser()
  breeds = get_breeds()

  breed_info = {}

  for index, breed in enumerate(breeds):
    count = index // 15

    if index != 0 and index % 15 == 0:
      browser = dump_current_data(breed_info, browser)

    breed_info.setdefault(breed, {})
    status_code = open_breed_web_page(breed, browser)
    if status_code == 404:
      continue

    breed_info = set_breed_stats(browser, breed_info, breed)

    # overview_titles = [
    #   overview.get_attribute('textContent')
    #   for overview in browser.find_elements(
    #     By.CLASS_NAME, 'breed-page__hero__overview__title')
    # ]
    # overview_subtitles = [
    #   overview.get_attribute('textContent')
    #   for overview in browser.find_elements(
    #     By.CLASS_NAME, 'breed-page__hero__overview__subtitle')
    # ]

    # for overview_pair in zip(overview_titles, overview_subtitles):
    #   breed_info[breed][overview_pair[0]] = overview_pair[1]

    # breed_info = set_breed_info(breed_info, breed, overview_subtitles)

    # trait_divs = browser.find_elements(By.CLASS_NAME, 'breed-trait-group__trait-all')
    # for trait_div in trait_divs:
    #   breed_info = set_breed_traits(trait_div, breed_info, breed)
    if breed == 'Yorkshire Terrier':
      break

  browser.quit()

  with open(f'./public/dog_breeds_{count}.json', 'w') as json_file:
    json.dump(breed_info, json_file, indent=2, ensure_ascii=False)


def get_missing_keys(keys: list, breed_info: dict) -> list:
  return list(set(keys).difference(list(breed_info.keys())))


def fix_missing() -> None:
  KEYS = [
    'Height',
    'Weight',
    'Life Expectancy',
    'Affectionate With Family',
    'Good With Young Children',
    'Good With Other Dogs',
    'Shedding Level',
    'Coat Grooming Frequency',
    'Drooling Level',
    'Coat Type',
    'Coat Length',
    'Openness To Strangers',
    'Playfulness Level',
    'Watchdog/Protective Nature',
    'Adaptability Level',
    'Trainability Level',
    'Barking Level',
    'Mental Stimulation Needs'
  ]
  for breed_file in glob.glob('public/dog_breeds_*.json'):
    with open(breed_file, 'r+') as bf:
      breeds = json.load(bf)
      for breed_name, breed_info in breeds.items():
        normalized_name = unicodedata.normalize('NFKD', breed_name).encode('ascii', 'ignore').decode('ascii')
        missing_keys = get_missing_keys(KEYS, breed_info)
        if len(missing_keys) > 0 or breed_info['Height'] == "":
          browser = init_browser()
          status_code = open_breed_web_page(normalized_name, browser)
          if status_code == 404:
            continue
          breeds = set_breed_stats(browser, breeds, breed_name)
          browser.quit()
          if breed_name == 'Yorkshire Terrier':
            break
          time.sleep(5)
      bf.seek(0)
      json.dump(breeds, bf, indent=2, ensure_ascii=False)
      bf.truncate()


def stitch_files():
  combined_breed_reference = {}
  for breed_file in glob.glob('public/dog_breeds_*.json'):
    with open(breed_file) as bf:
      breeds = json.load(bf)
      for breed_name, breed_info in breeds.items():
        combined_breed_reference[breed_name] = breed_info
  combined_breed_reference = {k:combined_breed_reference[k] for k in sorted(combined_breed_reference)}
  with open('public/dog_breeds.json', 'w') as json_file:
    json.dump(combined_breed_reference, json_file, indent=2, ensure_ascii=False)

  
stitch_files()
