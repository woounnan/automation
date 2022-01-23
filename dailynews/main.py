from msvcrt import getch
import requests
from bs4 import BeautifulSoup
import os
import webbrowser
import re
import datetime
import os

MAX_LEVEL = 1
srcs = {
    'src': ['알약 블로그 보안동향', '데일리시큐', '보안뉴스'],
    'query': {
        'getList': ['#content_search > div > div > ul li', 'div.list-block', 'div.news_list'],
        'getTitle': ['div.cont_thumb p.txt_thumb', 'div.list-titles', 'span.news_txt'],
        'getDate': ['div.cont_thumb p.thumb_info span.date', 'div.list-dated', 'span.news_writer'],
        'getLink': ['a.link_thumb', 'div.list-titles a', 'a']
    },
    'meta': {
        'title': [[], [], []],
        'writer': [[], [], []],
        'date': [[], [], []],
        'link': [[], [], []]
    },
    'main': '',
    'summary': [[], [], []],
    'url': [
        'http://blog.alyac.co.kr/category/%EA%B5%AD%EB%82%B4%EC%99%B8%20%EB%B3%B4%EC%95%88%EB%8F%99%ED%96%A5' + '?',
        'https://www.dailysecu.com/news/articleList.html?sc_section_code=S1N2&view_type=sm' + '&',
        'https://www.boannews.com/media/t_list.asp' + '?'
    ]
}
idx_article = 0
mi = -1
articles = []
level = 0
c = 0
sel = -1
flag_movP = 0
msg_state = ''
msg_cur = ''


def getDateWriter(n, idx, url):
    div = srcs['src'][idx]
    date = ''
    writer = ''
    if div == '알약 블로그 보안동향':
        res = requests.get(url, verify=False)
        bs = BeautifulSoup(res.text, 'html.parser')
        date = bs.select_one('span.date').get_text()
        y, m, d, h = list(re.findall('(\d\d\d\d)\. (\d{1,2})\. (\d{1,2})\. (\d\d:\d\d)', date)[0])

        date = y + '-' + '0' * (2 - len(m)) + m + '-' + '0' * (2 - len(d)) + d + ' ' + h
    elif div == '데일리시큐':
        tp = n.select_one(srcs['query']['getDate'][idx]).get_text().split(' | ')
        date = tp[2]
        writer = tp[1]
    elif div == '보안뉴스':
        tp = n.select_one(srcs['query']['getDate'][idx]).get_text().split(' | ')
        date = tp[1]
        writer = tp[0]
        y, m, d, h = list(re.findall('(\d\d\d\d)년 (\d{1,2})월 (\d{1,2})일 (\d\d:\d\d)', date)[0])
        date = y + '-' + m + '-' + d + ' ' + h

    return date, writer


def deleteArticle(idx_article):
    global articles, mi
    if len(articles) == 0:
        return 0
    if mi == idx_article:
        mi = -1
    del articles[idx_article]
    if idx_article >= len(articles):
        return -1
    return 0


def parseNews():
    for idx in range(len(srcs['url'])):
        url = srcs['url'][idx]
        for i in range(2):
            # input(url + 'page={}'.format(i+1))
            res = requests.get(url + 'page={}'.format(i + 1), verify=False)
            soup = BeautifulSoup(res.text, 'html.parser')
            news = soup.select(srcs['query']['getList'][idx])
            domain = re.findall('https*.*\.(?:kr|com)', url)[0]
            for n in news:
                tp = n.select_one(srcs['query']['getTitle'][idx])
                title = tp.get_text()
                tp = n.select_one(srcs['query']['getLink'][idx])
                link = domain + tp['href']
                date, writer = getDateWriter(n, idx, link)
                srcs['meta']['title'][idx].append(title)
                srcs['meta']['link'][idx].append(link)
                srcs['meta']['date'][idx].append(date)
                writer = srcs['src'][idx] + ' ' + writer
                srcs['meta']['writer'][idx].append(writer)
                srcs['summary'][idx].append('[' + date + '] ' + title)


def printMenu(y, o):
    os.system('cls')
    global flag_movP
    print("===============================================================")
    for i in range(len(o)):
        t = '   '
        if y == i and flag_movP == 0:
            t = '▶ '
        print(t + '| ' + o[i])
    print("===============================================================")
    print("[선택된 뉴스]")
    j = 0
    for a in articles:
        t = '   '
        if idx_article == j and flag_movP == 1:
            t = '▶ '
        content = "[" + srcs['meta']['date'][a[0]][a[1] + a[2]] + "] "
        content += srcs['meta']['title'][a[0]][a[1] + a[2]]
        if j == mi:
            content += ' *메인뉴스'
        print(t + '| ' + content)
        print("")
        j += 1
    print("===============================================================")
    print(msg_state)


def setMain(idx_article):
    global mi
    mi = idx_article


def addArticle(sel, y, c):
    if len(articles) > 4:
        return
    articles.append([sel, y, c])


def saveArticles():
    if mi == -1:
        input('메인 기사를 설정해주세요.')
        return
    global articles, msg_state
    content = ''
    i = 0
    j = 0
    for a in articles:
        if i != mi:
            sel = a[0]
            y = a[1]
            c = a[2]
            tp = '{}. {}'.format(j + 2, srcs['meta']['title'][sel][y + c])
            tp += '\n- {}'.format(srcs['meta']['date'][sel][y + c])
            tp += '\n- {}'.format(srcs['meta']['writer'][sel][y + c])
            tp += '\n- {}'.format(srcs['meta']['link'][sel][y + c])
            tp += '\n\n'
            content += tp
            j += 1
        i += 1
    sel, y, c = articles[mi]
    main = '{}. {}'.format(1, srcs['meta']['title'][sel][y + c])
    main += '\n- {}'.format(srcs['meta']['date'][sel][y + c])
    main += '\n- {}'.format(srcs['meta']['writer'][sel][y + c])
    main += '\n- {}'.format(srcs['meta']['link'][sel][y + c])
    main += '\n\n'
    content = main + content
    year, month, day = datetime.date.today().strftime('%Y-%m-%d').split('-')
    month = '0' * (2 - len(month)) + month
    day = '0' * (2 - len(day)) + day
    content = '<{}년 {}월 {}일 정보보안·개인정보보호 뉴스>\n\n'.format(year, month, day) + content
    fName = '정보보호 뉴스_{}.txt'.format(year + month + day)
    with open(fName, 'w') as f:
        f.write(content)
    msg_state = "파일 저장이 완료되었습니다. {" + os.getcwd() + '\\' + fName + "}"
    # 특정 배열이나 텍스트파일로 저장


def browseURL(sel, y, c):
    url = srcs['meta']['link'][sel][y + c]
    chrome_path = r'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'
    webbrowser.get(chrome_path).open(url)
    return 0


def parseFunc(key, y):
    global sel, flag_movP, idx_article, c, msg_state, msg_cur
    if flag_movP:
        msg_state = 'q: 전체 목록으로   m: 메인뉴스로 설정   d: 뉴스 삭제   s: 파일로 저장   엔터: 크롬으로 뉴스 열기(크롬을 미리 실행해두세요.)'
        if key == b'\r':
            return browseURL(articles[idx_article][0], articles[idx_article][1], articles[idx_article][2])
        elif key == b'm':
            setMain(idx_article)
        elif key == b'd':
            idx_article += deleteArticle(idx_article)
        elif key == b's':
            saveArticles()
        elif key == b'q':
            flag_movP = 0
            msg_state = 'e: 선택된 뉴스목록으로   a: 선택된 뉴스목록에 추가   엔터: 크롬으로 뉴스 열기(크롬을 미리 실행해두세요.)'
            msg_cur = msg_state
    else:
        if level == 0:
            if key == b'\r':
                sel = y
                y = 0
                msg_state = 'e: 선택된 뉴스목록으로   a: 선택된 뉴스목록에 추가   엔터: 크롬으로 뉴스 열기(크롬을 미리 실행해두세요.)'
                msg_cur = msg_state
                return 1
        elif level >= 1:
            if y == 0 and key == b'\r':
                sel = -1
                return -1
            if level == 1:
                if key and key == b'\r':
                    return browseURL(sel, y, c)
                else:
                    if key == b'a':
                        addArticle(sel, y, c)
                    elif key == b'e':
                        if len(articles) > 0:
                            flag_movP = 1
                            msg_state = 'q: 전체 목록으로   m: 메인뉴스로 설정   d: 뉴스 삭제   s: 파일로 저장   엔터: 크롬으로 뉴스 열기(크롬을 미리 실행해두세요.)'
                            msg_cur = msg_state
    return 0


def validation(menus, code, y):
    if 0 > (code + y) or len(menus) - 1 < (code + y):
        return 0
    return code


select = 0
y = 0
keyCode = {'H': -1, 'P': 1, 'K': 0, 'M': 0}
stage = ['src', 'summary']
parseNews()
past = 0
while level >= 0:
    if sel != -1:
        output = srcs[stage[level]][sel][:]
    else:
        output = srcs[stage[level]][:]
    if level >= 1:
        output.insert(0, '[back]')
        c = -1
    printMenu(y, output)
    key = getch()
    if key == b'\xe0':
        key = getch()
        msg_state = msg_cur
        if flag_movP == 0:
            y += validation(output, keyCode[key.decode()], y)
        else:
            idx_article += validation(articles, keyCode[key.decode()], idx_article)
        continue
    else:
        level += parseFunc(key, y)