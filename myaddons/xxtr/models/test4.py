#-*- encoding:utf-8 -*-
import requests
import time
import re
import random

cookies = {
    '.ASPXANONYMOUS': '6oNFc5EL1wEkAAAAOTA3NmRiNDctNTdjYi00ODZhLWJhODUtZDI5OTU5NmUxMDM1qcD1g4n5SrSG_O1J3fO_Frqm8dU1',
    '_uab_collina': '160826973914100214091184',
    'ASP.NET_SessionId': '24lkexn3uryam223aiut1pqq',
    'Hm_lvt_21be24c80829bd7a683b2c536fcf520b': '1608270273',
    'join_101612165': '1',
    'jac101601324': '57181331',
    'acw_tc': '781bad3116082760520862832e64fbb662babe0fd9c90fd80197af225dfe35',
    'LastActivityJoin': '101612165,108093416084',
    'jac101612165': '90376450',
    'u_asec': '099%23KAFEq7EKEqFEhYTLEEEEEpEQz0yFZ6VcSuiMa6PTDr35W6zTDusEZ6V1DEFET3llsRNXE7EFD67EE3QTEEjtBKlVjYFET%2FdosyaStHGTEELlluapYwnh7rQTEEMFluuta3%2FbE7EUlllP%2F3iSlllllurdt37El9llWsaStEgtlllO%2F3iS16allurdt37InqMTE195tGEEaquYSpXfNVX3LWc6Ud4dHQz6uVysCg%2BM3ls8DuRBHs1caeaUE7Tx1Q1sEHcf0RA%2FtiEsZHgQb1%2F8cv60JBWv09m4kUDB6OT7QDGO%2B6fPrCvVoaZ6LiR4KW6r2T4IcuVUPJK41ESAzZWgfJcy1JvUyUQSBEt05c6kuG%3D%3D',
    'Hm_lpvt_21be24c80829bd7a683b2c536fcf520b': '1608276359',
    'SERVERID': '3f9180de4977a2b2031e23b89d53baa6|1608276361|1608269736',
    'ssxmod_itna': 'Yq+xyWKGq7qWwqBPGKbm0D0AKKK7K5Xxo4PGCUDBwi4iNDnD8x7YDv+mvWR+KRY62G35O/C225Kf8QhaRpsWBQwfz5xCPGnDB9vxrWexii9DCeDIDWeDiDG4GmB4GtDpxG=yDm4i3jxWPDYxDrjOKDRxi7DD5Q8x07DQ5kQlqkqfchcZBCsQYxe0KD9PoDsgiEO09+I+8KlE+ODlIjDC91c2ICN4Gd/BnDTerNqY95fmDivADNKs4KK1Ru4TiKveQNOWZPqu=xDDacFi6DD=',
    'ssxmod_itna2': 'Yq+xyWKGq7qWwqBPGKbm0D0AKKK7K5Xxo4PGCD8dpG74GXoKPGaY=AoR//Rzx8hD6GnWDWYrQD5QWBEHO8Iu2r8rabmBusQo8DB5E7OKcYHLPH3cCBuIr3l=8grMxd3TbXeRlMcC/pTtsDp=Ea5=NZvrr=x=srW7QWYTTbmwF3W7jrwqE1IwIgAv+9O+Dhwviz4=QlEt6/fihzW7nKmLclKtBlIvmzWXXfMvqeaX523RCPpLSjWWj8E2NIqxxH1Ilz3u2f1rgBwqen9oH2iPPIehr1Ib6unu6dWdaZuI95vZ2MuOv6PO3IWGWknyOU4m4AOWA83Ta+K7iTIenFAywzYyjYwQmCQYsUYr7bPEhw4mYL4TmTsigLAr7WmhGn5hE/im3XBsGO3EnhB7hfENHeKqeZY8NgqQbbvK0meb1Ri3D07Siq/DFTiK9YLW=qF1FO1DO1KMEOOiTQGos07KEP6RjUe6684D7=DYFKeD',
}

headers = {
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Accept': 'text/plain, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://www.wjx.cn',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://www.wjx.cn/m/101612165.aspx',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

params = (
    ('curid', '101612165'),
    ('starttime', '2020/12/18 15:25:57'),
    ('source', 'directphone'),
    ('submittype', '1'),
    ('ktimes', '15'),
    ('hlv', '1'),
    ('rn', '3083604310.90376450'),
    ('jqpram', 'pkWSQaPRs'),
    ('t', '1608276371576'),
    ('jqnonce', 'b49f4e64-0e2c-4be2-91c0-e55fd3c21188'),
    ('jqsign', 'g1<c1`31(5`7f(1g`7(<4f5(`00ca6f744=='),
    ('u_asec', '099#KAFEe7EiExYEhYTLEEEEEpEQz0yFZ6VcSuiMa6PTDr35W6zTDusEZ6V1BYFET6i5EETXE7EFD67EEJMTETIYThZtZt/lFI2mg68Mlq8jaow4E7EFD65EE67TEEilluCVBYFET6i5EEwuE7EF9mC9u5MTEEylJcZdt3joE7EIlllbCUEtA4RrE7EhT3l//oassEFEp3llsyaSt3lllllO/3iSE3nllurdt37I99llWsaStELolllO/3iS16ahE7EvD3oEEqa3U61vv0XBLQuLL23K3TXpi9rkudUM8wluVP9+DAXGLbWbWEFE5YrErGTivkxdyl5GctgMXREOVLzakjDuzZBD0He6ma2G5c6opQLByybzuBqtLMSCV1XLy8Y01w/r2RjC0EY6q2frUBja8GgVWhWc6HG3kmwLm/PZE7EKlGjf/ypClAE1fYFEw7GFeOnUW3d7IQZFCbBWE7E5lGTi/EI1llllvwett5sl83tqs2g+E7EhlGwP/6GuMYFET/llsyayg9UTETqMTRxtvzsllll7xOCBQWSD4fZ0'),
    ('u_atype', '2'),
)

data = {
  'submitdata': '1$3'
}
# proxies = [
#         'http://58.220.95.30:10174',
#         'http://222.132.229.79:9999',
#         'http://27.220.51.197:9000',
#         'https://39.81.150.190:9000',
#     ]


for i in range(1,1000):
    time.sleep(10)

    # proxies = random.choice(proxies)
    response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx', headers=headers, params=params, cookies=cookies, data=data)
    print(response)
    print(response.text)
    text = response.text
    imageUrl = re.search(r'sojumpindex=(.*?)$', text)
    if imageUrl:
        print(imageUrl.group(1))
        print('第'+imageUrl.group(1)+'份')
        if imageUrl.group(1)==100:
            break


#NB. Original query string below. It seems impossible to parse and
#reproduce query strings 100% accurately so the one below is given
#in case the reproduced version is not "correct".
# response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx?curid=101612165&starttime=2020%2F12%2F18%2015%3A25%3A57&source=directphone&submittype=1&ktimes=15&hlv=1&rn=3083604310.90376450&jqpram=pkWSQaPRs&t=1608276371576&jqnonce=b49f4e64-0e2c-4be2-91c0-e55fd3c21188&jqsign=g1%3Cc1%6031(5%607f(1g%607(%3C4f5(%6000ca6f744%3D%3D&u_asec=099%23KAFEe7EiExYEhYTLEEEEEpEQz0yFZ6VcSuiMa6PTDr35W6zTDusEZ6V1BYFET6i5EETXE7EFD67EEJMTETIYThZtZt%2FlFI2mg68Mlq8jaow4E7EFD65EE67TEEilluCVBYFET6i5EEwuE7EF9mC9u5MTEEylJcZdt3joE7EIlllbCUEtA4RrE7EhT3l%2F%2FoassEFEp3llsyaSt3lllllO%2F3iSE3nllurdt37I99llWsaStELolllO%2F3iS16ahE7EvD3oEEqa3U61vv0XBLQuLL23K3TXpi9rkudUM8wluVP9%2BDAXGLbWbWEFE5YrErGTivkxdyl5GctgMXREOVLzakjDuzZBD0He6ma2G5c6opQLByybzuBqtLMSCV1XLy8Y01w%2Fr2RjC0EY6q2frUBja8GgVWhWc6HG3kmwLm%2FPZE7EKlGjf%2FypClAE1fYFEw7GFeOnUW3d7IQZFCbBWE7E5lGTi%2FEI1llllvwett5sl83tqs2g%2BE7EhlGwP%2F6GuMYFET%2Fllsyayg9UTETqMTRxtvzsllll7xOCBQWSD4fZ0&u_atype=2', headers=headers, cookies=cookies, data=data)
