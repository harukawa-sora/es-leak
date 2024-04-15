import requests
import os
import csv, sys, time, telegram, asyncio, base64, umsgpack
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


import argparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_last_number():
    with open(os.path.join(BASE_DIR, 'last.csv'), 'r', encoding='utf-8', newline='') as f:
        rdr = csv.reader(f)
        for line in rdr:
            return [int(line[0]), int(line[1]), int(line[2])]

def save_last_number(lasts):
    with open(os.path.join(BASE_DIR, 'last.csv'), 'w', encoding='utf-8', newline='') as f:
        wdr = csv.writer(f)
        wdr.writerow(lasts)

def get_image(image_url, index=0, referer=''):
    time.sleep(0.3)
    img_file_name = str(index) + os.path.splitext(os.path.basename(image_url))[1]   # url을 이름으로 하는 비어있는 데이터생성
    
    if ('basic' in image_url):
        IMAGE_DIR = os.path.join(BASE_DIR, 'basic')
    else:
        IMAGE_DIR = os.path.join(BASE_DIR, 'music')

    if (not os.path.isfile(os.path.join(BASE_DIR, img_file_name))):
        headers = {'Referer': referer.replace('wp-json/wp/v2/media', '')}
        
        response = requests.get(image_url, headers = headers)
        image_data = response.content # binary형식
        

        #파일에 이미지 데이터를 넣기
        with open(os.path.join(IMAGE_DIR, img_file_name), 'wb') as f:
            f.write(image_data)
            
    return os.path.join(IMAGE_DIR, img_file_name)


def get_media(addr, last=0):
    new_media = []

    for i in range(1, 10):
        response = requests.get(addr, { "page": i })
        if (response.status_code != 200): break
        data = response.json()
        list.sort(data, key=lambda media: media["id"], reverse=True)
        check_last = False
        for obj in data:
            if (last >= int(obj["id"])): 
                check_last = True
                break

            new_media.append(obj)

        if (check_last): break
    
    list.sort(new_media, key=lambda media: media["id"])

    if (len(new_media) == 0): return last, []

    new_media_addr = []

    for media in new_media:
        new_media_addr.append(get_image(media['guid']['rendered'], index=media['id'], referer=addr))

    return new_media[-1]['id'], new_media_addr

async def send_message(url, addrs, telegram_token, chat_id):
    bot = telegram.Bot(token = telegram_token)   #bot을 선언합니다.

    if (len(addrs) == 0):
        await bot.send_message(chat_id=chat_id, text=url)
    else:
        await bot.send_message(chat_id=chat_id, text="{}\n새로운 이미지 {}개".format(url.replace('wp-json/wp/v2/media', ''), len(addrs)))
        for key in addrs:
            await bot.send_photo(chat_id, open(key, 'rb'))

    
def aes_decrypt(key, iv, ciphertext):
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return umsgpack.unpackb(decrypted_data)

key = bytes([84,145,25,244,61,108,196,135,253,44,132,132,201,179,61,156,48,22,167,114,58,18,127,223,127,160,232,226,189,122,134,245])
iv = bytes([249,239,64,243,155,120,36,43,134,49,1,6,78,82,43,140])

def get_info(url, last_num, telegram_token, chat_id):
    url = url + str(last_num + 1)
    params={'ec': 'raBP1ImzmLNkGw9ITVBombPmTpTf41RzWQgqeNnibIodZQk8w-IJbahealpRf9CR',
            'ep': 'ts__69hPT84zoMQi3Fzpzx9WhpZhCSZzlp9TkSgfBqsKbqAELOWetxFIoHXPnn29',
            'ua': 'Android',
            'format': 'mpac',
            'version': '3.0.97',
            'device': 'Android'}

    # print(aes_decrypt(bytes([84,145,25,244,61,108,196,135,253,44,132,132,201,179,61,156,48,22,167,114,58,18,127,223,127,160,232,226,189,122,134,245]), iv, base64.urlsafe_b64decode('VbQYqemRm7hAiAk0dlZZ6QBoB5pdQWmPW_9kzwierZ6VZa2KNGiowVKhlnWPZxuF'.encode('ascii'))))
    response = requests.request("get", url, params=params)
    print(response.text)
    code_bytes = response.text
    decoded = base64.urlsafe_b64decode(code_bytes)
    s = aes_decrypt(key, iv, decoded)
    print(s)
    if 'app_message' in s:
        return last_num

    asyncio.run(send_message("새로운 공지:\nTitle:{}\nBody:{}".format(s['info_detail_type']['title'], s['info_detail_type']['body']), [], telegram_token, chat_id))
    last_num = get_info(url, int(last_num + 1), telegram_token, chat_id)
    return last_num

if __name__ == '__main__':
    # 인자값을 받을 수 있는 인스턴스 생성
    parser = argparse.ArgumentParser(description='')
    # 입력받을 인자값 등록
    parser.add_argument('url1')
    parser.add_argument('url2')
    parser.add_argument('info_url')
    parser.add_argument('telegram')
    parser.add_argument('chat')


    # 입력받은 인자값을 args에 저장 (type: namespace)
    args, k = parser.parse_known_args()

    last_numbers = get_last_number()

    for i, url in enumerate([args.url1, args.url2]):
        last, medias = get_media(url, last=last_numbers[i])
        if (len(medias) == 0): continue
        asyncio.run(send_message(url, medias, args.telegram, args.chat))
        last_numbers[i] = last

    last = get_info(args.info_url, last_numbers[2], args.telegram, args.chat)
    last_numbers[2] = (last)
    save_last_number(last_numbers)
