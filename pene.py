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

def mySub(pattern, after, s):
    print('len : ', len(re.findall(pattern, s)))
    '''
    if len(re.findall(pattern, s) > 0):
        return re.sub(pattern, after, s)
    else:
        return s
    '''
def getResponse(method, url, headers, data=''):
    '''
    if compare('get', method):
        return requests.get(url, headers=headers, stream=False, verify=False, timeout=3)
    else:
        return requests.post(url, headers=headers, data=data, stream=False, verify=False, timeout=3)
    '''
    return(requests.request(method.upper(), url, headers=headers, data=data, stream=False, verify=False, timeout=3))
        
def main(request, checkType, url = ""):
    setSyntax = lambda s : s[0].upper() + s[1:].lower() if len(s) > 0 else ''
    setErrorAppendix = lambda s, f: s if f == 'file' else '[*] 오류 발생 \n ' + s
    data, headers = {}, {}
    verb, path, host, lineBreak = '', '', '', ''
    type_file = False
    
    try:
        format_REQ = json.loads(request)
    except:
        try:
            search_methodDefinitions = '(\w+)\s(\/.*)\sHTTP\/(?:1\.[10]|2)(\.\.|#015#012|\s*\n\s*)\w'
            verb, path, lineBreak = matched = re.findall(search_methodDefinitions, request)[0]
            lineBreak = lineBreak.strip(' ')
            #request = re.sub('(#015#012|\.\.)([\w-]*\s*:)', r'\1\1\2', unquote(request))
            request = re.sub('({})([\w-]*\s*:)'.format(lineBreak), r'\1\1\2', unquote(request))
            #request = request.strip().split('\n')
            
            request = request.replace(lineBreak*2, '\n').split('\n')
            search_headerFields = '^([\w-]+)\s*:\s*([^/]{2}.+)'
            c = 0
            for i, line in enumerate(request[1:], start = 1):
                matched = re.findall(search_headerFields, line.strip())
                if len(matched) < 1:
                    c = 1
                    break
                matched = matched[0]
                if compare('host', matched[0]):
                    host = matched[1]
                    continue
                elif compare('content-type', matched[0]):
                    if 'boundary' in matched[1]:
                        type_file = True
                #대소문자 형식 맞추기 Content-Type
                convs = matched[0].split('-')
                headers['-'.join([setSyntax(conv) for conv in convs])] = matched[1].strip()
            i += 1 - c
            search_dataset = '[\w_-]+\s*\=\s*.+'
            search_file = '([\w-]+)\s*\=\s*([^&]*)&*'
            rawdata = ''.join(request[i:])
            
            #dataset
            if re.match(search_dataset, rawdata) != None:
                matched = re.findall('([\w-]+)\s*\=\s*(.+)(?=&\w+)', rawdata)
                matched = [re.sub('([\w_-]+)=', r'\1\n', pair).split('\n') for pair in re.sub('&([\w_-]+=)', r'\n\1',rawdata).split('\n')]
                data = reduce(setData, matched, {})
            #rawdata
            else:
                #file set
                if type_file:
                    rawdata = ''.join(request[i:]).strip()
                    search_boundary = 'boundary=(-+\w+)'
                    boundary = '--'+re.search(search_boundary, headers['Content-Type']).group(1)
                    #rawdata = mySub('(?:\.{2}|#015#012)({}(?:-{2})*)'.format(boundary), r'\n\1', rawdata)
                    #rawdata = re.sub('({}(?:-{2})*)(?:\.{2}|#015#012)'.format(boundary), r'\1\n', rawdata)
                    #infoSet = rawdata.split(boundary)
                data = rawdata
            format_REQ = {
                    'Protocol' : setSyntax('HTTPS'),
                    'Verb' : setSyntax(verb),
                    'Path' : path,
                    'Host' : host,
                    'Headers' : headers,
                    'Data' : data
            }
        except Exception as e:
            print('error msg : ', str(e))
            return {'Error' : -1, 'Message' : setErrorAppendix('<요청값을 생성하지 못했습니다>', checkType)}
        
    try:
        if url != "":
            url = url + format_REQ['Path']     
        else:
            url = '{}://'.format(format_REQ['Protocol'].lower()) + format_REQ['Host'] + format_REQ['Path'] 
        response = getResponse(format_REQ['Verb'], url, format_REQ['Headers'], format_REQ['Data'])
    except Exception as e:
        if 'HTTPConnectionPool' in str(e):
            raise HTTPConnectionPool
        print('error msg : ', str(e))
        return {'Error' : -2, 'Message' : setErrorAppendix('<응답값을 받아오지 못했습니다>', checkType), 'Format' : format_REQ}
    return {'Error' : 0, 'Message' : '', 'Format' : format_REQ, 'Response' : response}
if __name__ == '__main__':
    main()