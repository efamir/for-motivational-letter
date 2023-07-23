from bs4 import BeautifulSoup
import requests
from fake_http_header import FakeHttpHeader

from selenium import webdriver
from selenium.webdriver.firefox.service import Service

import time
import re


dic_of_lessons = {
    "Англ.мова": "",
    "Алгебра": "",
    "Геометрія": "",
    "Історія": "",
    "Укр.мова": "",
}

list_of_ordinary_numbers = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]

list_of_ignoring = ["", "Фіз-ра", "", "МСП", "Психологічна хвилинка", "Історія курс"]


def get_lessons_urls():
    url = ""
    main_page = BeautifulSoup(requests.get(url, headers=FakeHttpHeader().as_header_dict()).text, "lxml")
    date = time.ctime().split()[1:3]
    p_list = main_page.find("main").find_all("p")
    flag = False
    dic_of_links = dict()
    for p in p_list:
        if date[1] in p.text:
            flag = True
            continue
        if flag:
            is_ignore = False
            link = p.find("a")
            if link:
                link_soup = BeautifulSoup(str(link), "lxml")
                final_link_soup = BeautifulSoup(requests.get(link_soup.find("a").get("href")).text, "lxml")
                title = p.text
                for ignore in list_of_ignoring:
                    if ignore in title:
                        is_ignore = True
                if not is_ignore:
                    dic_of_links[title] = final_link_soup.find("a").get("href")
            else:
                break
    return dic_of_links


def open_links_with_sel(list_of_links: list):
    service = Service(".../driver_folder/geckodriver")
    driver = webdriver.Firefox(service=service)
    try:
        driver.get(list_of_links[0])
        for index in range(1, len(list_of_links)):
            driver.execute_script(f"window.open('about:blank', '{list_of_ordinary_numbers[index]}tab');")
            driver.switch_to.window(f"{list_of_ordinary_numbers[index]}tab")
            driver.get(list_of_links[index])
        while True:
            try:
                _ = driver.window_handles
                time.sleep(1)
            except Exception:
                exit()
    finally:
        driver.quit()


def get_lessons_data(dic_of_links=None, action=None):
    print()
    bad_urls = list()
    for lesson, url in dic_of_links.items():
        src = requests.get(url, headers=FakeHttpHeader().as_header_dict()).text
        soup = BeautifulSoup(src, "lxml")
        zoom = False
        try:
            content_for_zoom_time = "".join([element.get("content") for element in soup.find_all("meta")])
            if re.search(r"[zZ][Oo]{2}[mM]\W|[Зз][Уу][Мм][Іі]?\W", src):
                zoom = True
                zoom_time = re.findall(r"\d{1,2}:\d{2}", content_for_zoom_time)
                if len(zoom_time) > 1:
                    if re.search(r"10\s?[-–]\s?Б.*?(\d{1,2}:\d{2})", content_for_zoom_time):
                        zoom_time = re.search(r"10\s?[-–]\s?А.*?(\d{1,2}:\d{2})", content_for_zoom_time)
                        print(f"{lesson}\nZoom at {zoom_time.group(1)}")
                        string1 = True
                        for key, item in dic_of_lessons.items():
                            if key in lesson:
                                print(item, url, '#'*20, sep="\n")
                                string1 = False
                                break
                        if string1:
                            print(url, "#" * 20, sep="\n")
                        continue
                    else:
                        if action == "3":
                            bad_urls.append(url)
                            continue
                        print(lesson, "Zoom at unknown time", sep="\n")
                        string4 = True
                        for key, item in dic_of_lessons.items():
                            if key in lesson:
                                print(item, url, '#' * 20, sep="\n")
                                string4 = False
                                break
                        if string4:
                            print(url, "#" * 20, sep="\n")
                        continue
                print(f"{lesson}\nZoom at {zoom_time[0]}")
                string2 = True
                for key, item in dic_of_lessons.items():
                    if key in lesson:
                        print(item, url, '#'*20, sep="\n")
                        string2 = False
                        break
                if string2:
                    print(url, "#"*20, sep="\n")
            else:
                if "docs.google.com/document/" not in url:
                    if action == "3":
                        bad_urls.append(url)
                        continue
                    print(f"{lesson}\nPROGRAM CAN'T WORK WITH THIS URL\n{url}\n{'#'*20}")
                    continue
                print(f"{lesson}\nProgram couldn't find zoom\n{url}\n{'#'*20}")
        except Exception as ex:
            if zoom:
                if action == "3":
                    bad_urls.append(url)
                    continue
                print(lesson, "Zoom at unknown time", sep="\n")
                string3 = True
                for key, item in dic_of_lessons.items():
                    if key in lesson:
                        print(item, url, '#'*20, sep="\n")
                        string3 = False
                        break
                if string3:
                    print(url, "#"*20, sep="\n")
            else:
                print(ex)
    if action == "3":
        return bad_urls


def main():
    action = input("Choose parse mode by entering it's number and pressing Enter key:\n"
                   "[1] Without selenium\n[2] Open all links with selenium\n[3] Open bad links with selenium\nMode: ")
    if action == "1":
        get_lessons_data(dic_of_links=get_lessons_urls())
    elif action == "2":
        list_of_urls = list()
        for lesson, url in get_lessons_urls().items():
            for ignore in list_of_ignoring:
                if ignore in lesson:
                    continue
            list_of_urls.append(url)
        open_links_with_sel(list_of_urls)
    elif action == "3":
        open_links_with_sel(get_lessons_data(dic_of_links=get_lessons_urls(), action="3"))


if __name__ == '__main__':
    main()
