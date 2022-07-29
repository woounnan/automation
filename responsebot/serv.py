# -*- coding: utf-8 -*-

from flask import Flask, request
from collections import Counter
from functools import reduce
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests.packages.urllib3, requests, json, time, datetime, re, os, csv
import pene
from binascii import hexlify

requests.packages.urllib3.disable_warnings()

botEmail = "hyeok_jang_responsebot@webex.bot"
accessToken = "your bot's access toke"
headers = {"Authorization": "Bearer %s" % accessToken, "Content-Type": "application/json", 'Accept' : 'application/json'}
TIME_WAIT = 0.5

def print_hex_dump(buffer, start_offset=0):
    print('-' * 79)

    offset = 0
    while offset < len(buffer):
        # Offset
        print(' %08X : ' % (offset + start_offset), end='')

        if ((len(buffer) - offset) < 0x10) is True:
            data = buffer[offset:]
        else:
            data = buffer[offset:offset + 0x10]

        # Hex Dump
        for hex_dump in data:
            print('hexdump : ', hex_dump)
            print("%02X" % int(hex_dump, 16), end=' ')

        if ((len(buffer) - offset) < 0x10) is True:
            print(' ' * (3 * (0x10 - len(data))), end='')

        print('  ', end='')

        # Ascii
        for ascii_dump in data:
            if ((ascii_dump >= 0x20) is True) and ((ascii_dump <= 0x7E) is True):
                print(chr(ascii_dump), end='')
            else:
                print('.', end='')

        offset = offset + len(data)
        print('')

    print('-' * 79)
    
class CSVTypeError(Exception):
    pass


def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print('Error: Creating directory. ' + directory)


def sendFile(fullPath, roomId, text=""):
    print('send the file')
    with open(fullPath, 'rb') as f:
        cmd = f"""curl --request POST\
         --header "Authorization: Bearer {accessToken}"\
         --form "files=@{fullPath};type=image/png"\
         --form "roomId={roomId}"\
         --form "text={text}"\
         https://webexapis.com/v1/messages"""
        os.system(cmd)
        os.system('rm -f ' + fullPath)

def MyJsonDumps(jsonData, idx = 0, indent = 5):
    if type(jsonData) != dict:
            print('Not json type')
    indent = ' '*indent
    result = '{\n'
    for key, value in jsonData.items():
        result += indent*(idx+1)
        if type(value) == dict:
            result += f'"{key}"' + ' : ' + MyJsonDumps(value, idx + 1)
        #elif type(value) == str and len(value) > 0:
        else:
            values = value.split('\n')
            if len(values) > 1:
                result += f'"{key}" :\n"'
                result += '\n'.join(values) + '\n'
                result += '"'
                #result += f'"{key}"' + ': "\n'
                # result += indent*(idx+2) + ('\n' + indent*(idx+2)).join(values) + '\n'
                # result += indent*(idx+1) + '"'
            else:
                result += f'"{key}"' + ' : ' + f'"{value}"'
        result += ',\n'
    result += indent*idx + '}'
    return result

app = Flask(__name__)

#@app.post("/")
@app.route('/', methods=['POST'])
def get_tasks():
    data = request.json.get('data')
    email, roomId, messageId = data['personEmail'], data['roomId'], data['id']
    payload = {"roomId": roomId}
    fPath = '/workspace/news/storage/{}'.format(email)
    createFolder(fPath)
    # print('roomId : ', roomId)
    # help
    # option
    if email == botEmail:
        return ("")

    response = json.loads(
        requests.request("GET", "https://api.ciscospark.com/v1/messages/{}".format(messageId), headers=headers).text)
    if 'files' in response:
        print('파일을 받음')
        payload["text"] = '[*] 파일 업로드 완료...'
        requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload), headers=headers)

        try:
            #웹엑스 서버에서 파일 로우데이터를 가져와서 csv 형식의 파일로 로컬에 저장
            files = response['files'][0]
            fullPath = fPath + '/' + re.search('\d{4}-\d{2}-\d{2}', response['created']).group() + '.csv'
            response = requests.request("GET", files, headers=headers)
            stats = []
            idx_payload, idx_host = -1, -1

            with open(fullPath, 'wb') as f:
                f.write(response.text.encode())

            payload["text"] = '[*] 파일에서 페이로드를 찾는 중...'
            response = requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload),
                                        headers=headers)
            while True:
                try:
                    # windows
                    # with open(fullPath, 'r', encoding='utf-8') as f:
                    # linux
                    with open(fullPath, 'r') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        for i, s in enumerate(rows[0]):
                            #payload와 host가 담긴 필드의 인덱스를 저장
                            if 'payload' in s:
                                idx_payload = i
                            elif 'host' in s:
                                idx_host = i
                            elif idx_host != -1 and idx_payload != -1:
                                break
                        break
                # If null byte exists
                except Exception as e:
                    #널 바이트가 포함되어 있을 경우 csv 리더로 파싱되지 않기 때문에 널바이트를 제거하여 저장한 후 다시 파싱 진행
                    print(f'error [{e}]')
                    with open(fullPath, 'rb') as fi:
                        data = fi.read()
                    with open(fullPath, 'wb') as fo:
                        fo.write(data.replace(b'\x00', b''))
                    continue

            payload["text"] = '[*] 페이로드 확인...'
            response = requests.request("POST", "https://webexapis.com/v1/messages/", data=json.dumps(payload),
                                        headers=headers)
            if idx_payload < 0:
                raise CSVTypeError
            #앞서 저장했던 임시 csv 파일 삭제
            os.system('rm -f ' + fullPath)

            c = 0
            errorCount = 3
            totalLen = len(rows) - 1
            extend = 3
            payload["text"] = '[*] 진행률 : 0% [ 0 / {} ] \n'.format(totalLen) + '▷ ' * 10 * extend
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                        headers=headers)
            response = json.loads(response.text)
            messageId = response['id']

            rows[0].append('응답 코드')
            idx = 1
            while idx < len(rows):
                print(f'idx : [{idx} / {totalLen}]')
                progress = int(((idx - 1) / totalLen) * 100)
                row = rows[idx]
                rawdata = row[idx_payload]
                #행에 하나씩 접근하면서 페이로드를 pene.main로 전달하여 응답값 확인
                if re.match('https*://(\w+\.*)+/*', row[idx_host]) != None:
                    result = pene.main(rawdata, 'file', row[idx_host])
                else:
                    result = pene.main(rawdata, 'file')
                if result['Error'] != 0:
                    print('Failure')
                    #에러일 경우 에러 처리
                    if 'HTTPConnectionPool' in result['Message'] or 'Exceeded' in result['Message']:
                        print('실패 host + url : {}'.format(result['Format']['Host'] + result['Format']['Path']))
                        if errorCount < 3:
                            
                            payload["text"] = '[*] HTTP 연결 실패! \n[*] 5분 후 재시도 합니다. [{} / {}] --- 실패 URL : {}'.format(
                                errorCount + 1, 3, (result['Format']['Host'] + result['Format']['Path']))
                            response = requests.request("POST", "https://webexapis.com/v1/messages",
                                                        data=json.dumps(payload), headers=headers)

                            # time.sleep(5 * 60)
                            time.sleep(1)
                            payload["text"] = '[*] 작업을 다시 시작합니다.'
                            response = requests.request("POST", "https://webexapis.com/v1/messages",
                                                        data=json.dumps(payload), headers=headers)

                            payload["text"] = '[*] 진행률 : {0}% [ {1} / {2} ] \n'.format(progress, idx - 1,
                                                                                       totalLen) + '▶' * (
                                                          c * extend) + '▷ ' * (10 * extend - (c * extend))
                            response = requests.request("POST", "https://webexapis.com/v1/messages",
                                                        data=json.dumps(payload), headers=headers)
                            response = json.loads(response.text)
                            messageId = response['id']
                            errorCount += 1
                            rows[idx].append(result['Message'])
                            continue
                        else:
                            payload["text"] = '[*] 연결이 되지 않아 작업을 중지합니다.'
                            response = requests.request("POST", "https://webexapis.com/v1/messages",
                                                        data=json.dumps(payload), headers=headers)
                            break
                    else:
                        errorCount = 0
                        rows[idx].append(result['Message'])
                else:
                    print('Success')
                    errorCount = 0
                    responseCode = result['Response'].status_code
                    rows[idx].append(responseCode)
                    stats.append(responseCode)

                if idx - 1 > (c + 1) * int(totalLen / 10) and c < 9:
                    c += 1
                    payload["text"] = '[*] 진행률 : {0}% [ {1} / {2} ] \n'.format(progress, idx - 1, totalLen) + '▶' * (
                                c * extend) + '▷ ' * (10 * extend - (c * extend))
                    response = requests.request("PUT", "https://webexapis.com/v1/messages/{}".format(messageId),
                                                data=json.dumps(payload), headers=headers)
                idx += 1
            print('Completion!')
            payload["text"] = '[*] 진행률 : 100% [ {0} / {1} ] \n'.format(idx - 1, totalLen) + '▶' * (10*extend)
            response = requests.request("PUT", "https://webexapis.com/v1/messages/{}".format(messageId),
                                        data=json.dumps(payload), headers=headers)
            #작업이 완료되면 응답 통계를 계산
            stats = sorted(dict(Counter(stats)).items(), key=lambda x: x[0])
            stats = [[str(cells[0]), str(cells[1])] for cells in stats]
            csv_content = [['응답 코드 통계']]
            csv_content += [['응답 코드', '반환 수']]
            csv_content += stats
            csv_content += rows
            print('fullPath : ', fullPath)
            with open(fullPath, 'w', newline='') as f_write:
                writer = csv.writer(f_write)
                for row in csv_content:
                    writer.writerow(row)
        except CSVTypeError:
            print('CSV Upload Error')
            payload["text"] = '[*] 파일 처리 실패'
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                        headers=headers)
            return ("")
        sendFile(fullPath, roomId)


    else:
        print('메시지를 받음')
        beautify = False
        msg = response['text']
        #beautify;가 입력된 경우 : 테스트는 하지 않고 정리된 요청값을 보여주기만 함
        if msg.startswith('beautify;'):
            beautify = True
            msg = msg[len('beautify;'):]

        result = pene.main(msg, 'string', beautify=beautify)
        #요청값을 파싱하는 도중 에러가 발생했을 때
        if result['Error'] == -1:
            payload["text"] = result['Message']
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                        headers=headers)
            return ({'status': 'Failure'})

        #요청값 파싱이 완료되었으면 채팅방으로 전송
        payload["text"] = '[*] 요청값\n' + result['RAW_REQUEST']
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)
        
        payload["text"] = '[*] 요청값 - JSON\n' + json.dumps(result['Format'], indent=2)
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload), headers=headers)

        #beautify가 설정된 경우 요청값 반환만 하고 종료
        if beautify:
            return ({'status': 'Success'})
        
        #응답값 확인 도중 에러가 발생했을 때
        if result['Error'] == -2:
            payload["text"] = result['Message']
            response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                        headers=headers)
            return ({'status': 'Failure'})
        #응답 결과를 반환
        payload["text"] = '[*] 응답 코드 \n<' + str(result['Response'].status_code) + '>'
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                    headers=headers)
        payload["text"] = '[*] 응답 헤더 \n' + json.dumps(dict(result['Response'].headers), indent=2)
        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                    headers=headers)

        #요청 URL에서 파일이름을 가져옴
        fName = re.search('\/(\w+(?:\.\w+)*|\.\w+)(?=(?:\?\w*=.*|$))', result['Format']['Path'])
        if fName != None:
            fName = fName.group() + '.html'
        else:
            fName = 'response.html'

        payload["text"] = '[*] 응답 페이지(html)'
        with open(fPath + '/' + fName, 'wb') as f:
            # 응답 페이지 내에 있는 상대 경로를 절대 경로로 수정(리소스 불러와야 하니까)
            host = 'https://' + result['Format']['Host']
            source = re.sub('(<.+=")(/\S+")', r'\1{}\2'.format(host), result['Response'].text)
            f.write(source.encode())


        response = requests.request("POST", "https://webexapis.com/v1/messages", data=json.dumps(payload),
                                    headers=headers)
        fullPath = fPath + '/' + fName
        sendFile(fullPath, roomId, '외부망 실행 권장')
    print('[', datetime.datetime.now(), '] from (', email, ') in {', roomId, '}')
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

    return ({'status': 'Success'})


app.run(host="0.0.0.0", port=8899)
