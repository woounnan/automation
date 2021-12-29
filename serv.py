# -*- coding: utf-8 -*-

from flask import Flask,request
from collections import Counter
from functools import reduce
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests.packages.urllib3, requests, json, time, datetime, re, os, csv
import pene

requests.packages.urllib3.disable_warnings()

botEmail = "hyeok.jang_soc@webex.bot"
accessToken = "OWYxZWE4MTEtOTZiNy00YTcyLTk4NWItZmEwNTUzMTM4OTQyMTFiNGM1MTMtZmZm_PF84_22cb7792-d880-4ec5-b6a6-649d9411bb5e"
headers = {"Authorization": "Bearer %s" % accessToken, "Content-Type": "application/json"}

TIME_WAIT = 0.5



class CSVTypeError(Exception):
    pass
    
def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)

        
def sendFile(fullPath, roomId, text=""):
    with open(fullPath, 'rb') as f:
        cmd = """curl --request POST \
    --header "Authorization: Bearer {}" \
    --form "files=@{};type=text/html" \
    --form "roomId={}" \
    --form "text=[*] {}" \
    https://webexapis.com/v1/messages""".format(accessToken, fullPath, roomId, text)
        os.system(cmd)
        os.system('rm -f ' + fullPath)
        
        

app = Flask(__name__)
@app.route('/', methods=['POST'])
def get_tasks():
    data = request.json.get('data')
    email, roomId, messageId = data['personEmail'], data['roomId'], data['id']
    payload = {"roomId": roomId}
    fPath = './storage/{}'.format(email)
    createFolder(fPath)
    
    
    if email == botEmail:
        return("")
    
    
    response = json.loads(requests.request("GET", "https://api.ciscospark.com/v1/messages/{}".format(messageId), headers=headers).text)
    if 'files' in response:
        print('파일을 받음')
        payload["text"] = '[*] 파일 업로드 완료...'
        requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload), headers=headers)
        
        try:
            files = response['files'][0]
            fullPath = fPath + '/' + response['created']
            response = requests.request("GET", files, headers=headers)
            stats = []
            idx_payload, idx_host = -1, -1
            
            
            with open(fullPath, 'wb') as f:
                f.write(response.text.encode())
                
            
            payload["text"] = '[*] 파일에서 페이로드를 찾는 중...'
            response = requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload), headers=headers)
            while True:
                try:
                    with open(fullPath, 'r') as f:
                        #lines = list(csv.reader(f))
                        reader = csv.reader(f)
                        rows = list(reader)
                        #['signature', 'host', 'uri', 'payload']
                        #if not('signature' in rows[0][0] and 'host' in rows[0][1] and 'uri' in rows[0][2] and 'payload' in rows[0][3]):
                        for i, s in enumerate(rows[0]):
                            if 'payload' in s:
                                idx_payload = i
                            elif 'host' in s:
                                idx_host = i
                            elif idx_host != -1 and idx_payload != -1:
                                break
                        break
                #If null byte exists
                except:
                    with open(fullPath, 'rb') as fi:
                        data = fi.read()
                    with open(fullPath, 'wb') as fo:
                        fo.write(data.replace(b'\x00', b''))
                    continue
            print('idx_payload : ', idx_payload)
            
            payload["text"] = '[*] 페이로드 확인...'
            response = requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload), headers=headers)
            if idx_payload < 0:
                raise CSVTypeError
            
            os.system('rm -f ' + fullPath)
            
            c = 1
            totalLen = len(rows) - 1
            extend = 3
            payload["text"] = '[*] 진행률 : 0% [ 0 / {} ] \n'.format(totalLen)  + '▷ '*10*extend
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
            response = json.loads(response.text)
            messageId_state = response['id']
            
            rows[0].append('응답 코드')
            for idx, row in enumerate(rows[1:], start = 1):
                rawdata = row[idx_payload]
                #row[1] = host = 'https*://xxx.xxx.xxx'
                try:
                    if re.match('https*://(\w+\.*)+/*', row[idx_host]) != None:
                        result = pene.main(rawdata, 'file', row[idx_host])
                    else:
                        result = pene.main(rawdata, 'file')
                except requests.exceptions.ConnectionError:
                    print('Reached the limit.... Wait 30 seconds')
                    time.sleep(30)
                    continue
                if result['Error'] != 0:
                    rows[idx].append(result['Message'])
                else:
                    responseCode = result['Response'].status_code
                    rows[idx].append(responseCode)
                    stats.append(responseCode)
                time.sleep(TIME_WAIT)
                
                progress = int((idx/totalLen)*100)
                if progress > c*int(totalLen/10) and c < 10:
                    payload["text"] = '[*] 진행률 : {0}% [ {1} / {2} ] \n'.format(progress, idx, totalLen) + '▶'*(c*extend) + '▷ '*(10*extend - (c*extend))
                    response = requests.request("PUT", "https://webexapis.com/v1/messages/{}".format(messageId_state), data=json.dumps(payload), headers=headers)
                    c += 1
            payload["text"] = '[*] 진행률 : {}% [{}/{}]\n'.format(100, idx, totalLen) + '▶'*10*extend
            response = requests.request("PUT", "https://webexapis.com/v1/messages/{}".format(messageId_state), data=json.dumps(payload), headers=headers)
            
                
            stats = sorted(dict(Counter(stats)).items(), key= lambda x : x[0])
            stats = [[str(cells[0]), str(cells[1])] for cells in stats]
            csv_content = [['응답 코드 통계']]
            csv_content += [['응답 코드', '반환 수']]
            csv_content += stats
            csv_content += rows
            fullPath += '.csv'
            with open(fullPath, 'w', newline='') as f_write:
                writer = csv.writer(f_write)
                for row in csv_content:
                    writer.writerow(row)
        except CSVTypeError:
            print('CSV Upload Error')
            payload["text"] = '[*] 파일 처리 실패 [타입 오류]'
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
            return("")
        except pene.HTTPConnectionPool:
            print('Request Error')
            payload["text"] = '[*] HTTP 연결 실패 [최대 연결 수 초과]'
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
            return("")
        sendFile(fullPath, roomId)
        
        
    else:
        print('메시지를 받음')
        
        msg = response['text']
        
        result = pene.main(msg, 'string')
        if result['Error'] == -1:
            payload["text"] = result['Message']
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
            return ("It failed")

        payload["text"] = '[*] 요청값\n' + json.dumps(result['Format'], indent=2)
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)

        if result['Error'] == -2:
            payload["text"] = result['Message']
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
            return ("It failed")
        payload["text"] = '[*] 응답 코드 \n<' + str(result['Response'].status_code) + '>'
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
        payload["text"] = '[*] 응답 헤더 \n' + json.dumps(dict(result['Response'].headers), indent=2)
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)

        fName = re.search('/+([^/\s]+)(?:\.\w+)*$',result['Format']['Path'])
        if fName != None:
            fName = fName.group() + '.html'
        else:
            fName = 'response.html'

        payload["text"] = '[*] 응답 페이지(html)'
        with open(fPath + '/' + fName, 'wb') as f:
            #Convert relative path to absolute path
            host = 'https://' + result['Format']['Host']
            source = re.sub('(<.+=")(/\S+")',r'\1{}\2'.format(host), result['Response'].text)
            f.write(source.encode())

        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
        fullPath = fPath + '/' + fName
        sendFile(fullPath, roomId, '외부망에서 실행하세요()')

        #response = requests.request("POST", "https://webexapis.com/v1/messages", headers=headers, data={'files' : f,  'roomId' : roomId, 'text': 'test'})
        #response = requests.request("POST", "https://webexapis.com/v1/messages", headers=headers, data=f)
            
            
            
    print ('[',datetime.datetime.now(),'] from (', email,') in {', roomId, '}')
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    
    return ("It works")

app.run(host="0.0.0.0", port=8899)
