from binascii import hexlify
from functools import reduce
import re, json, requests
import urllib3
from urllib.parse import unquote, quote
urllib3.disable_warnings()


class HTTPConnectionPool(Exception):
    pass


def pr(*output):
    result = ''
    for op in output:
        result += str(op)
    print('[*] ', result)


def setData(data, pair):
    data[pair[0]] = pair[1]
    return data


def compare(name, target):
    pt = re.compile(name, re.IGNORECASE)
    result = re.search(pt, target)
    if result == None:
        return False
    else:
        return True

def getResponse(method, url, headers, data=''):
    response = requests.request(method.upper(), url, headers=headers, data=data, stream=False, verify=False, timeout=10)
    if str(response.status_code)[0] == '2':
        response.raise_for_status()
        response.encoding = None
    return response


def main(request, checkType, url="", beautify=False):
    setSyntax = lambda s: s[0].upper() + s[1:].lower() if len(s) > 0 else ''
    setErrorAppendix = lambda s, f: s if f == 'file' else '[*] 오류 발생 \n ' + s
    data, headers = {}, {}
    verb, path, host, lineBreak = '', '', '', ''
    type_file = False
    protocol = 'HTTPS'
    try:
        format_REQ = json.loads(unquote(request))
    except:
        try:
            search_methodDefinitions = '(\w+)\s(\/.*)\sHTTP\/(?:1\.[10]|2)(\.\.|#015#012|\s*\n\s*|\\r\\n)\w'
            request = unquote(request)
            verb, path, lineBreak = matched = re.findall(search_methodDefinitions, request)[0]
            lineBreak = lineBreak.strip(' ')
            
            #request = re.sub('({})([\w-]*\s*:)'.format(lineBreak), r'\1\1\2', unquote(request))
            #print('rawdata : ', request, '\n\n')

            #request = request.replace(lineBreak * 2, '\n').split('\n')
            raw_request = request.replace(lineBreak, '\n')
            request = raw_request.split('\n')
            
            
            search_headerFields = '^([\w-]+)\s*:\s*(.+)'
            c = 0
            for i, line in enumerate(request[1:], start=1):
                matched = re.findall(search_headerFields, line.strip())
                if len(matched) < 1:
                    c = 1
                    break
                matched = matched[0]
                if compare('host', matched[0]):
                    port = re.search(':(\d+)', matched[1])
                    host = re.sub(':\d+', '', matched[1])
                    continue
                elif compare('content-type', matched[0]):
                    if 'boundary' in matched[1]:
                        type_file = True
                # 대소문자 형식 맞추기 Content-Type
                convs = matched[0].split('-')
                headers['-'.join([setSyntax(conv) for conv in convs])] = matched[1].strip()
            i += 1 - c
            #print('rawdata : ', request, '\n\n')
            search_dataset = '[\w_-]+\s*\=\s*.+'
            search_file = '([\w-]+)\s*\=\s*([^&]*)&*'
            rawdata = '\n'.join(request[i:])

            # dataset
            if re.match(search_dataset, rawdata) != None:
                matched = re.findall('([\w-]+)\s*\=\s*(.+)(?=&\w+)', rawdata)
                matched = [re.sub('([\w_-]+)=', r'\1\n', pair).split('\n') for pair in
                           re.sub('&([\w_-]+=)', r'\n\1', rawdata).split('\n')]
                data = reduce(setData, matched, {})
            # rawdata
            else:
                # file set
                #if type_file:
                    #rawdata = ''.join(request[i:]).strip()
                    # search_boundary = 'boundary=(-*\w+)'
                    # boundary = '--' + re.search(search_boundary, headers['Content-Type']).group(1)
                    #rawdata = mySub(f'(?:{lineBreak})(' + boundary + '(?:-{2})*)', r'\n\1', rawdata)
                    #rawdata = re.sub('({}(?:-{2})*)(?:\.{2}|#015#012)'.format(boundary), r'\1\n', rawdata)
                data = rawdata.strip()
            if port != None:
                port = port.group(1)
                if port == '443':
                    protocol = 'HTTPS'
                elif port == '80':
                    protocol = 'HTTP'
            format_REQ = {
                'Protocol': protocol.upper(),
                'Verb': verb.upper(),
                'Path': path,
                'Host': host,
                'Headers': headers,
                'Data': data
            }
        except Exception as e:
            print('error msg : ', str(e))
            return {'Error': -1, 'Message': setErrorAppendix('<요청값을 생성하지 못했습니다>', checkType)}

    try:
        if url != "":
            url = url + format_REQ['Path']
        else:
            url = '{}://'.format(format_REQ['Protocol'].lower()) + format_REQ['Host'] + format_REQ['Path']
        len_rawdata = len(rawdata)
        if len_rawdata > 0:
            format_REQ['Headers']['Content-Length'] = str(len(rawdata) + 10)
        if beautify:
            return {'Error': 0, 'Format': format_REQ, 'RAW_REQUEST' : raw_request}
        response = getResponse(format_REQ['Verb'], url, format_REQ['Headers'], format_REQ['Data'])
    except Exception as e:
        print('error msg : ', str(e))
        return {'Error': -2, 'Message': setErrorAppendix('<응답값을 받아오지 못했습니다> \n[{}]'.format(re.sub('0x[0-9a-f]{2,16}', '0x[***************]', str(e))), checkType), 'Format': format_REQ, 'RAW_REQUEST' : raw_request}
    return {'Error': 0, 'Message': '', 'Format': format_REQ, 'Response': response, 'RAW_REQUEST' : raw_request}


if __name__ == '__main__':
    main()
