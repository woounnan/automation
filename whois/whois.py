
#!/usr/bin/python3

from ipwhois import IPWhois
from sys import argv
from flask import Flask, request
from requests.packages.urllib3.util.retry import Retry
import requests.packages.urllib3, requests, json, time, datetime, re, os, csv
from binascii import hexlify
import pycountry

test = '1'
whitelist_ip = ''
whitelist_description = ''
whitelist_country = ''
botEmail = "bob8gook_whois@webex.bot"
accessToken = "MGY3ZWI0N2ItZjI0ZC00MzQ2LWFlNjYtNDc0MWM3NDNlNGQ2ODI1MzQ4MzAtZmMz_PF84_22cb7792-d880-4ec5-b6a6-649d9411bb5e"
#accessToken = "N2MyNzY5OTAtODA4ZS00ZTA3LWI4YmYtYWE5MmJiODg2NmQ3YmY5MjBkNTAtMWFl_PF84_22cb7792-d880-4ec5-b6a6-649d9411bb5e"
headers = {"Authorization": "Bearer %s" % accessToken, "Content-Type": "application/json", 'Accept' : 'application/json'}

def GetInfo(ip):
    try:
        w = IPWhois(ip).lookup_rdap()
        print('lookup succeeded')
    except:
        print('lookup failed')
        return {'state' : False}
    _net = w["network"]
    _obj = w["objects"]
    red = "\x1b[0;31m"
    cyan = "\x1b[0;36m"
    end = "\x1b[0m"

    # ASN
    _asn = {
        "asn": "ASN",
        "asn_cidr": "CIDR",
        "asn_country_code": "Country code",
        "asn_date": "Date",
        "asn_description": "Description",
        "asn_registry": "Registry"
    }

    dic_ret = {}
    for k, v in _asn.items():
        dic_ret[f'{v}'] = f'{w[k]}'
    return {'state' : True, 'whois' : dic_ret}
    
def SendMessage(payload, msg):
    payload["text"] = str(msg)
    response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                    headers=headers)
    response = json.loads(response.text)
    return {'messageId' : response['id']}

def ModifyMessage(payload, msg, messageId):
    payload["text"] = str(msg)
    requests.request("PUT", "https://webexapis.com/v1/messages/{}".format(messageId),
                                                data=json.dumps(payload), headers=headers)
    
def SendFile(fullPath, roomId, text=""):
    print('send the file')
    with open(fullPath, 'rb') as f:
        cmd = f"""curl --request POST\
         --header "Authorization: Bearer {accessToken}"\
         --form "files=@{fullPath};type=image/png"\
         --form "roomId={roomId}"\
         --form "text={text}"\
         https://webexapis.com/v1/messages"""
        os.system(cmd)

def LoadWhitelist(padding = '@'):
    global whitelist_ip, whitelist_description, whitelist_country
    os.system(f'cp cdns.txt cdns{padding}.txt')
    os.system(f'cp descriptions.txt descriptions{padding}.txt')
    os.system(f'cp countries.txt countries{padding}.txt')
    with open(f'cdns{padding}.txt', 'r') as f:
        whitelist_ip = [x for x in f.read().split('\n') if len(x) > 0]
    with open(f'descriptions{padding}.txt', 'r') as f:
        whitelist_description = [x for x in f.read().split('\n') if len(x) > 0]
        print('[*] description : ' + str(whitelist_description))
    with open(f'countries{padding}.txt', 'r') as f:
        whitelist_country = [x for x in f.read().split('\n') if len(x) > 0]
    os.system(f'rm cdns{padding}.txt')
    os.system(f'rm descriptions{padding}.txt')
    os.system(f'rm countries{padding}.txt')
app = Flask(__name__)


@app.route('/kisa', methods=['GET'])
def TestKisa(roomId):
    os.system('wget --mirror --convert-links --adjust-extension --page-requisites  --no-parent https://krcert.or.kr/data/secNoticeView.do?bulletin_writing_sequence=66834')
    time.sleep(2)
    print('[*] zip file')
    os.system('zip -r kisa.zip krcert*')
    SendFile('kisa.zip', roomId,'')
    os.system('rm -rf kisa.zip')
    return {'status' : 'success'}

@app.route('/', methods=['POST'])
def get_tasks():
        
    data = request.json.get('data')
    email, roomId, messageId = data['personEmail'], data['roomId'], data['id']
    
    if email == botEmail:
        return ("")
    #TestKisa(roomId)
    payload = {"roomId": roomId}
    response = json.loads(
    requests.request("GET", "https://api.ciscospark.com/v1/messages/{}".format(messageId), headers=headers).text)
    
    
    try:
    	msgs = response['text'].strip().split('\n')
    except:
        SendMessage(payload, '[*] 명령어를 입력해주세요.')
        return ({'status': 'Failed'})
    
    header = msgs[0]
    
    regex_whitelist = r"/(up|down) (ip|description|country)"
    regex_ip = r'(?:\d{1,3}\.){3}\d{1,3}'
    if header.startswith('/help'):
        menu = '[*] IP 조회\n'
        menu += '● \' [조회 IP] \'\n'
        menu += '\n[*] 화이트리스트 다운/업로드\n'
        menu += '● \' /[up | down]  [ip | country | description] \'\n'
        menu += '● 화이트리스트 파일 업로드시 바로 적용됩니다.\n'
        menu += '\n[*] 파일 양식\n'
        menu += '● IP : ip;;설명\n'
        menu += '● Description : description;;설명\n'
        menu += '● Country : country\n'
        SendMessage(payload, menu)
    elif re.match(regex_whitelist, header):
        action, target = re.findall(regex_whitelist, header)[0]
        if action == 'down':
            if target == 'ip':
            	SendFile('cdns.txt', roomId,'')
            elif target == 'description':
                SendFile('descriptions.txt', roomId,'')
            elif target == 'country':
                SendFile('countries.txt', roomId,'')
        elif action == 'up':
            if not 'files' in response:
                SendMessage(payload, "[*] 파일을 업로드 하세요.")
            if target == 'ip':
                fPath = 'cdns.txt'
            elif target == 'description':
                fPath = 'descriptions.txt'
            elif target == 'country':
                fPath = 'countries.txt'
            files = response['files'][0]
            
            response = requests.request("GET", files, headers=headers)
            response.raise_for_status()
            response.encoding="UTF-8"
            
            with open(fPath, 'w', encoding="UTF-8") as f:
                f.write(response.text)

            LoadWhitelist(email)
            SendMessage(payload, f"[*] 화이트리스트 {target} 적용 완료.")
    elif re.match(regex_ip, header):
        list_ip = re.findall(regex_ip, ' '.join(msgs))
        SendMessage(payload, '[*] 입력한 IP를 조회합니다. [{}개]'.format(len(list_ip)))
        outputs_trusted = []
        outputs_censored = []
        outputs_ip = []
        outputs_failed = []

        extend = 3
        totalLen = len(list_ip)
        progress = 1
        if totalLen > 20:
        	messageId = SendMessage(payload, '[*] 진행률 : 0% [ 0 / {} ] \n'.format(totalLen) + '▷ ' * 10 * extend)['messageId']
        time_start = time.time()
        for idx in range(len(list_ip)):
            ip = list_ip[idx]
            if idx + 1 > progress * (totalLen/10) and progress < 9 and totalLen > 20:
                ModifyMessage(payload, '[*] 진행률 : {}% [ {} / {} ] ; {} seconds\n'.format(round(idx/totalLen, 2)*100, idx+1, totalLen, round(time.time() - time_start, 2)) + '▶ ' * progress * extend + '▷ ' * (10 - progress) * extend, messageId)
                progress += 1
            result = GetInfo(ip)
            #time.sleep(0.2)
            if not result['state']:
                outputs_failed.append(ip)
                continue
            ipInfo = result['whois']
            
            censored = 0
            
            country = pycountry.countries.get(alpha_2=ipInfo['Country code']).name
            
            output = ''
            
            op  = f'IP : {ip} '
            for wl in whitelist_ip:
                cdn, description = wl.split(';;')
                if ip.startswith(cdn):
                    op = "● " + op + ' --> [' + cdn + f' ({description})' + ']'
                    censored = 1
                    break
            output += output + op + '\n'
            
            op = f'Country : {country} '
            for ctry in whitelist_country:
                ctry = ctry.replace(' ', '').lower()
                if ctry in country.replace(' ', '').lower():
                    op = "● " + op + ' --> [화이트리스트]'
                    censored = 1
                    break
            output = output + op + '\n'

            op = f'Description : {ipInfo["Description"]} '
            for wl in whitelist_description:
                owner, description = wl.split(';;')
                owner = owner.replace(' ', '').lower()
                if owner in ipInfo['Description'].replace(' ', '').lower():
                    op = "● " + op + ' --> [' + owner + f' ({description})' + ']'
                    censored = 1
                    break
            output = output + op + '\n'
            
            if not censored:
                outputs_ip.append(ip)
                outputs_trusted.append(output)
            else:
                outputs_censored.append(output)
        
        if totalLen > 20:
        	ModifyMessage(payload, '[*] 진행률 : 100% [ {} / {} ] ; {} seconds\n'.format(totalLen, totalLen, round(time.time() - time_start, 2)) + '▶ ' * 10* extend, messageId)
                    
        outputs = ''
        len_trusted = len(outputs_trusted)
        if len_trusted > 0:
            outputs += f"[*] 안전 [ {len_trusted} / {totalLen} ]\n"
            outputs += "\n".join(outputs_trusted)
            
        len_censored = len(outputs_censored)
        if len(outputs_censored) > 0:
            if len(outputs) > 1:
                outputs += "\n\n"
            outputs += f"[*] 위험 [ {len_censored} / {totalLen} ]\n"
            outputs += "\n".join(outputs_censored)
                    
        len_failed = len(outputs_failed)
        if len(outputs_failed) > 0:
            if len(outputs) > 1:
                outputs += "\n\n"
            outputs += f"[*] 룩업 실패 [ {len_failed} / {totalLen} ]\n"
            outputs += "\n".join(outputs_failed)
        
        if len(outputs_trusted) + len(outputs_censored) > 10 :
            with open('list_whois.txt', 'w') as f:
                f.write(outputs)
            SendFile('list_whois.txt', roomId, '')
        else:
        	SendMessage(payload, outputs)
        
        if len(outputs_ip) > 0:
            msg = "***************************\n\n"
            msg += '\n'.join(outputs_ip) + '\n\n'
        else:
            msg = ""
        msg += "***************************\n"
        msg += "[{} / {} ]".format(len(outputs_ip), len(list_ip))
        msg += "\n"
        
        if len(outputs_ip) > 10:
            with open('list_ip.txt', 'w') as f:
                f.write(msg)
            SendFile('list_ip.txt', roomId, '')
        else:
        	SendMessage(payload, msg)
    else:
        SendMessage(payload, f'-bash: {header}: command not found (Type "/help")')
    return ({'status': 'Success'})


LoadWhitelist()
app.run(host="0.0.0.0", port=8999)
