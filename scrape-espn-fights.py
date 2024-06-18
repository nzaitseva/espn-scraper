# -*- coding: utf-8 -*-
import sys
import csv
import time
import argparse
import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

""" Usage example:
	$ python scrape-espn-fights.py --driver ../chromedriver --out_csv out.csv --logfile out.log --url https://www.espn.com/mma/fightcenter/_/league/ufc/id/401221629 
"""

csv_headers = ["event url", "event id", "event_name", 
							"event_date","event_date_month", "event_date_day", "event_date_year",
							"event_location", "event_location_arena", "event_location_geo","fight_priority",
							"fight_class1", "fight_class2", "fight_class3",
							"fight_end_method1", "fight_end_method2", "fight_end_time1", "fight_end_time2", 
							"f1_name", "f1_url", "f1_id", "KD",
							"TOT STRIKES", "TOT STRIKES",
							"SIG STRIKES", "SIG STRIKES", 
							"HEAD", "HEAD",
							"BODY", "BODY", 
							"LEGS", "LEGS",
							"CONTROL", "TAKE DOWNS", "TAKE DOWNS","SUB ATT",
							"f2_name", "f2_url", "f2_id",  "KD",
							"TOT STRIKES", "TOT STRIKES",
							"SIG STRIKES", "SIG STRIKES", 
							"HEAD", "HEAD",
							"BODY", "BODY", 
							"LEGS", "LEGS",
							"CONTROL", "TAKE DOWNS", "TAKE DOWNS","SUB ATT",
							"fight_winner"]


def write_to_csv(rows, out_csv):
	with open(out_csv, "a", newline='') as csvfile:
		writer = csv.writer(csvfile)
		for row in rows:
			writer.writerow(row)

# A wrapper to avoid "Not enough values to unpack" error.
def get_splitted_values(values):
	if len(values) > 1:
		return values
	else:
		return ["",""]

def get_driver(driver_path):
	options = Options()
	options.add_argument('--headless')
	options.add_argument('--disable-gpu')	# only for Windows
	options.add_argument('--start-maximized')
	service = Service(executable_path=driver_path)
	driver = webdriver.Chrome(service=service,options=options)
	driver.set_window_size("1980","1080")
	driver.set_page_load_timeout(60)
	driver.implicitly_wait(15)
	return driver
				
def main(logger,driver_path,out_csv,urls):
	driver = get_driver(driver_path)
	try:
		for url in urls: 
			rows = [] # Write to CSV after processing a web page.
			time.sleep(random.uniform(0.5,2))
			driver.get(url)
			# Accept cookies, if popup
			try:
				popup_cookies = driver.find_element(By.ID, value="onetrust-accept-btn-handler")
				popup_cookies.click()
				time.sleep(random.uniform(1.5, 3))
			except: #no popup
				pass
			event_url = url
			event_id = event_url.split("/")[-1]
			try:
				# 502 error
				headline = driver.find_element(by=By.XPATH, value="//h1[contains(@class,'headline')]")
			except:
				if "502 bad gateway" in driver.page_source.lower():
					logger.error("502 HTTP Error. Will retry later...")
					urls.append(url)
					time.sleep(5)
					continue
				else:
					raise
			event_name = headline.text
			event_date = headline.find_element(by=By.XPATH, value="./following-sibling::div[1]").text
			event_date_month = event_date.split()[0]
			event_date_day = event_date.split()[1].replace(",","")
			event_date_year = event_date.split()[-1]
			try:
				event_location = headline.find_element(by=By.XPATH, value="./following-sibling::div[2]").text
				location_parts = event_location.split(",")
				event_location_arena = location_parts[0]
				event_location_geo = location_parts[-1] if len(location_parts) > 1 else ""
			except:
				event_location, event_location_arena, event_location_geo = "","",""
			skip_this_page = False			
			# Rows are grouped by fight priority.
			groups = driver.find_elements(by=By.XPATH, value="//div[@class='PageLayout__Main']/div[@data-wrapping='MMAFightCard']")
			for group in groups:
				if skip_this_page:
					break
				fight_priority = group.find_element(by=By.XPATH, value=".//header/div/h3").text.split('-')[0].strip()
				fights = group.find_elements(by=By.XPATH,value=".//div[@class='Accordion']/div[contains(@class,'AccordionPanel')]")
				for fight in fights:
					accordion_header = fight.find_element(by=By.XPATH, value="./div[contains(@class,'AccordionPanel__header')]")
					if not accordion_header.find_elements(by=By.XPATH,value=".//div[contains(@class,'MMAFightCard__Gamestrip--open')]"):
						accordion_header.click()
					time.sleep(0.5)
					overview_header = accordion_header.find_element(by=By.XPATH, value=".//div[contains(@class,'Gamestrip__Overview')]")
					if "Canceled" in overview_header.text:
						logger.info("Canceled: {}\nSkipping...".format(driver.current_url))
						continue
					try:					
						fight_classes = accordion_header.find_element(by=By.XPATH, value=".//div[@class='Collapse__Child']/h2").text.split("-")
						fight_class1 = fight_classes[0]	
						fight_class2 = fight_classes[1] if len(fight_classes)>1 else ""
						fight_class3 = fight_classes[2] if len(fight_classes)>2 else ""
					except:
						fight_class1,fight_class2,fight_class3 = "","",""
					try:
						info_divs = overview_header.find_elements(by=By.XPATH,value=".//div[contains(@class,'ScoreCell__Time')]/div/div")
						fight_end_method1 = info_divs[0].text
						fight_end_time1,fight_end_time2 = info_divs[-1].text.split(",")
					except IndexError:	
						skip_this_page = True
						# Save screenshot of the current page.
						error_png = driver.get_screenshot_as_png()	
						with open("Error-{}.png".format(event_id), "wb") as f:
							f.write(error_png)
						break	
					div_text = info_divs[1].text
					if len(info_divs) > 2:
						fight_end_method2 = div_text
					else:
						if div_text.find("("):
							fight_end_method2 = div_text
							fight_end_time1,fight_end_time2 = "",""
						else:
							fight_end_method2 = ""
					f1_header = accordion_header.find_element(by=By.XPATH, value=".//div[contains(@class,'MMACompetitor')][1]")
					f1_name = f1_header.find_element(by=By.XPATH, value=".//h2/span").text
					f2_header = accordion_header.find_element(by=By.XPATH, value=".//div[contains(@class,'MMACompetitor')][2]")
					f2_name = f2_header.find_element(by=By.XPATH, value=".//h2/span").text
					try:
						f1_header.find_element(by=By.CLASS_NAME, value='MMACompetitor__arrow')
					except:
						fight_winner = f2_name
					else:
						fight_winner = f1_name
					accordion_body = fight.find_element(by=By.XPATH, value="./div[contains(@class,'AccordionPanel__body')]")
					accordion_body_divs = accordion_body.find_elements(by=By.XPATH,value=".//div[@class='ResponsiveWrapper']/div/div[contains(@class, 'flex')]/div")
					f1_url = accordion_body_divs[0].find_element(by=By.XPATH, value=".//a[contains(@class,'AnchorLink')]").get_attribute("href")
					f1_id = f1_url.split("/")[-2]
					f2_url = accordion_body_divs[2].find_element(by=By.XPATH, value=".//a[contains(@class,'AnchorLink')]").get_attribute("href")
					f2_id = f2_url.split("/")[-2]
					logger.debug("Fighter 1 URL: {}, ID: {}\nFighter 2 URL: {}, ID: {}".format(f1_url,f1_id,f2_url,f2_id))
					# All stats
					matchup_list = accordion_body_divs[1].find_elements(by=By.XPATH,value=".//ul[@class='MMAMatchup list']/li")
					fstats = {"KD":[],"TOT STRIKES":[],"SIG STRIKES":[],
									"HEAD":[],"BODY":[],"LEGS":[],
									"CONTROL":[],"TAKE DOWNS":[],"SUB ATT":[]}	
					for li in matchup_list:
						key = li.find_element(by=By.XPATH, value="./div[2]").text.strip().upper()
						vals = li.find_elements(by=By.XPATH, value=".//div[contains(@class,'MMAMatchup__Stat')]")
						if "/" in vals[0].text:
							res=[]
							for v in vals:
								res.extend(get_splitted_values(v.text.split('/')))
							logger.debug("{}: {}".format(key, ', '.join([r for r in res])))
						else:
							res = [v.text.replace("--","") for v in vals]
							logger.debug("{}: {}".format(key, ', '.join([r for r in res])))
						fstats[key] = res
					row = [event_url, event_id, event_name, 
							event_date,event_date_month, event_date_day, event_date_year,
							event_location, event_location_arena, event_location_geo,fight_priority,
							fight_class1, fight_class2, fight_class3,
							fight_end_method1, fight_end_method2, fight_end_time1, fight_end_time2, 
							f1_name, f1_url, f1_id, fstats["KD"][0],
							fstats["TOT STRIKES"][0], fstats["TOT STRIKES"][1],
							fstats["SIG STRIKES"][0], fstats["SIG STRIKES"][1], 
							fstats["HEAD"][0], fstats["HEAD"][1], 
							fstats["BODY"][0], fstats["BODY"][1], 
							fstats["LEGS"][0], fstats["LEGS"][1],
							fstats["CONTROL"][0], fstats["TAKE DOWNS"][0], fstats["TAKE DOWNS"][1],fstats["SUB ATT"][0],
							f2_name, f2_url, f2_id,  fstats["KD"][1],
							fstats["TOT STRIKES"][2], fstats["TOT STRIKES"][3],
							fstats["SIG STRIKES"][2], fstats["SIG STRIKES"][3], 
							fstats["HEAD"][2], fstats["HEAD"][3], 
							fstats["BODY"][2], fstats["BODY"][3], 
							fstats["LEGS"][2], fstats["LEGS"][3],
							fstats["CONTROL"][1], fstats["TAKE DOWNS"][0], fstats["TAKE DOWNS"][1],fstats["SUB ATT"][1],
							fight_winner]
					rows.append(row)
					logger.info(row)				
			if not skip_this_page:
				# If some error on a page it won't be saved into CSV.
				write_to_csv(rows, out_csv)					
	except Exception as ex:
		logger.error("Error: URL {}".format(driver.current_url))
		logger.error(ex)
		# Save screenshot of the current page.
		error_png = driver.get_screenshot_as_png()
		with open("Error-{}.png".format(event_id), "wb") as f:
			f.write(error_png)			
	finally:
		driver.quit()
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Scrape a URL or a list of URLs from a text file into CSV.')
	parser.add_argument('--url', help='A url to scrape.')
	parser.add_argument('--links', help='A text file with URLs.')
	parser.add_argument('--out_csv', help='A CSV file for results.')
	parser.add_argument('--append', default=False, action='store_true', help='Append scraped results to existing CSV.')
	parser.add_argument('--driver', help='Path to Selenium Chromedriver.')
	parser.add_argument('--logfile', help='Name for a log file (optional).')
	args = parser.parse_args()
	logger = logging.getLogger('scrape-espn-fights')
	logger.setLevel(logging.INFO)
	logfile = args.logfile or 'out.log'
	fh = logging.FileHandler(logfile)
	fh.setLevel(logging.ERROR)
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	logger.addHandler(fh)
	logger.addHandler(ch)	
	out_csv = args.out_csv or 'results.csv'
	mode = "a" if args.append else "w"
	# Write CSV headers for a new file (if no --append flag is set), otherwise skip this step.
	if not args.append:
		with open(out_csv,"w") as csvfile: # In the beginning re-writes a file.
			writer = csv.writer(csvfile)
			writer.writerow(csv_headers)		
	driver_path = args.driver
	if not driver_path:
		logger.info("Please specify path of the Chromedriver")
		sys.exit()
	# Either a url or a file with links should be specified.
	url = args.url
	links_file = args.links
	if url:
		urls=[url]
	elif links_file:
		with open(links_file) as f:
			urls = f.read().splitlines()
	else:
		logger.error("Please specify --url or --seed-list")		
		sys.exit()
	main(logger,driver_path,out_csv,urls)
		
