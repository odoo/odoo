#-*- encoding:utf-8 -*-
import requests
import time
import random
cookies = {
    '.ASPXANONYMOUS': '6oNFc5EL1wEkAAAAOTA3NmRiNDctNTdjYi00ODZhLWJhODUtZDI5OTU5NmUxMDM1qcD1g4n5SrSG_O1J3fO_Frqm8dU1',
    '_uab_collina': '160826973914100214091184',
    'ASP.NET_SessionId': '24lkexn3uryam223aiut1pqq',
    'Hm_lvt_21be24c80829bd7a683b2c536fcf520b': '1608270273',
    'join_101612165': '1',
    'jac101601324': '57181331',
    'acw_tc': '781bad2516082741043895984e077d6fae68f37b94b27161fa7689e2425ae5',
    'LastActivityJoin': '101612165,108092699360',
    'jac101612165': '80008875',
    'u_asec': '099%23KAFEB7EKEqFEhGTLEEEEEpEQz0yFZ6VcSui5a6tFScvIW6AHZcloa6A3Df7TEEilluCVlYFETJDovlNhE7EhlAaP%2F3iSWEFE5YUkA7Ti1ZWcqQYt2f0q3IYvzaD4DYVkWLL86LxciiLgKW6r2T4IcuVUPJK41FGQsn8GfBxo8CrG5coSBFtIyUQVVHGbvFtrLLvgBwd6iLlgqXRbE7EUlllP%2F3iSlllllurdt3il%2FlllWsaStEgtlllO%2F3iS16allurdt37IncQTEEMFluuta3PoE7EIlllbCUEPtNBhE7EvEKhCbOaIcL%2BVJBDtUtxsHsbDSwZnZ0XZNV%2BulrRih0Yy8LSpztodBYFETEEEbOI%3D',
    'Hm_lpvt_21be24c80829bd7a683b2c536fcf520b': '1608275313',
    'SERVERID': '3f9180de4977a2b2031e23b89d53baa6|1608275315|1608269736',
    'ssxmod_itna': 'WqRxuDRDBGG=0=D8DzPx2Q6=DQjy004OuiOR7qu4GNLhoDZDiqAPGhDC8+tbOk8e+x1zj8AhQG8jbrwY6WU4rm=Lf/qoGLDmKDybQ2eGG0xBYDQxAYDGDDPDocPD1D3qDk6xYPGWFqA3Di4D+FLQDmqG0DDtO94G2D7Uc87mceCdqEurgQiidj7=DjqbD/8Dby7=PdZn=9kpRDB67xBQMAk6BCeDHDSEEIBvPtr3dz7qeYixsQ2D4nGe4zI4d9GGElops07MQDDff2AhQeD=',
    'ssxmod_itna2': 'WqRxuDRDBGG=0=D8DzPx2Q6=DQjy004OuiOR7u4A=aLAWD/jYjDF27YfKEGqKAPd99WMxideofBY+8e=Kjor45cPj9RGF=Ww8n8V89Go7kYN8M3W4t24WrMj0a4j2tyVGuPSG89Z/i=ZxptVaH=YaeiC2FFCobH0im1drm=KOOmOFg1rjmiy6e4Hf7+=6mt9jeHTxqLUcya+DTGhg56G2c7jOMvEEuv=1cv9Zq0RDv2UhDH3d86Mxq4c9ealevnx8gKby51w+=uGoIQ29nOUQ/6G8Li0mjU0edw07aTqB8UY8hQSNF8nqGpbsCS5CEG5wYtTbemhZRhrTh9G33lGZubuRKvwkCE8bL=FL=wgCyfwUgrvekAWW7dadLpY4rCQIwgaW2pWOYpQIKrvWgaKr3Y3A7Tv8B+YSsP=IhDxQnQBdT=0DKBEUoT51TFcTk1qfDDw=+eYq+l4BQ3+YFv43uUweg+zF957ECGYqlGNYqkehKD5dWHh06ePh575q0xe2q4exZFq4k7eVDPDGcDG7kiDD===',
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
    'X-Forwarded-For': '{}.{}.{}.{}'.format(112, random.randint(64, 68), random.randint(0, 255), random.randint(0, 255)),
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
    ('starttime', '2020/12/18 15:08:31'),
    ('source', 'directphone'),
    ('submittype', '1'),
    ('ktimes', '8'),
    ('hlv', '1'),
    ('rn', '3083604310.80008875'),
    ('jqpram', 'L7UtN7Z8'),
    ('t', '1608275340792'),
    ('jqnonce', '43ca9514-0da2-4463-bb8b-e22f2bed8b64'),
    ('jqsign', '<;ki1=9<%8li:%<<>;%jj0j%m::n:jml0j><'),
    ('u_asec', '099#KAFEjYEmExdEhGTLEEEEEpEQz0yFZ6VcSui5a6tFScvIW6AHZcloa6A3DmQTEE7EERpCuYFEFAYEqyZov3llls88/K9LOikjn0NXE7EFEE1Cb/UTEEalEwrdy8sllllGxOa4E7EFEI1CbP7TEEilluCVlYFETJDovlNhE7EhlAaP/3iSWEFE5YUkA7Ti1ZWcqQYt2f0q3IYvzaD4DYVkWLL86LxciiLgKW6r2T4IcuVUPJK41FGQsn8GfBxo8CrG5coSBFtIyUQVVHGbvFtrLLvgBwd6iLlgqXRbE7EUlllP/3iSlllllurdt3il/lllWsaStEgtlllO/3iS16allurdt37IncQTEEMFluuta3PoE7EIlllbCUEPtNBhE7EvEKhCbOaIcL+VJBDtUtxsHsbDSwZnZ0XZNV+ulrRih0Yy8LSpztodBYFETEEEbOKZE7EKlG1P/q9JlGC/fYFE19dEBsCl/ld7BJMTET5bEw1dzW9lF6xtYbCOCyvfXyhXZdyWE7EqlGTD/1M8llllhpkdBYFETEEEbOK+E7EhlGwP/3cYMYFET/llsyaaJY=='),
    ('u_atype', '2'),
)
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
  'submitdata': '1$2'
}

import requests

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

response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx', headers=headers, params=params, cookies=cookies, data=data)

#NB. Original query string below. It seems impossible to parse and
#reproduce query strings 100% accurately so the one below is given
#in case the reproduced version is not "correct".
# response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx?curid=101612165&starttime=2020%2F12%2F18%2015%3A25%3A57&source=directphone&submittype=1&ktimes=15&hlv=1&rn=3083604310.90376450&jqpram=pkWSQaPRs&t=1608276371576&jqnonce=b49f4e64-0e2c-4be2-91c0-e55fd3c21188&jqsign=g1%3Cc1%6031(5%607f(1g%607(%3C4f5(%6000ca6f744%3D%3D&u_asec=099%23KAFEe7EiExYEhYTLEEEEEpEQz0yFZ6VcSuiMa6PTDr35W6zTDusEZ6V1BYFET6i5EETXE7EFD67EEJMTETIYThZtZt%2FlFI2mg68Mlq8jaow4E7EFD65EE67TEEilluCVBYFET6i5EEwuE7EF9mC9u5MTEEylJcZdt3joE7EIlllbCUEtA4RrE7EhT3l%2F%2FoassEFEp3llsyaSt3lllllO%2F3iSE3nllurdt37I99llWsaStELolllO%2F3iS16ahE7EvD3oEEqa3U61vv0XBLQuLL23K3TXpi9rkudUM8wluVP9%2BDAXGLbWbWEFE5YrErGTivkxdyl5GctgMXREOVLzakjDuzZBD0He6ma2G5c6opQLByybzuBqtLMSCV1XLy8Y01w%2Fr2RjC0EY6q2frUBja8GgVWhWc6HG3kmwLm%2FPZE7EKlGjf%2FypClAE1fYFEw7GFeOnUW3d7IQZFCbBWE7E5lGTi%2FEI1llllvwett5sl83tqs2g%2BE7EhlGwP%2F6GuMYFET%2Fllsyayg9UTETqMTRxtvzsllll7xOCBQWSD4fZ0&u_atype=2', headers=headers, cookies=cookies, data=data)


for i in range(1,100):
    time.sleep(5)
    response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx', headers=headers, params=params, cookies=cookies, data=data)
    print("第"+str(i)+"份答卷")
    print(response)
    print(response.text)
#NB. Original query string below. It seems impossible to parse and
#reproduce query strings 100% accurately so the one below is given
#in case the reproduced version is not "correct".
# response = requests.post('https://www.wjx.cn/joinnew/processjq.ashx?curid=101612165&starttime=2020%2F12%2F18%2015%3A08%3A31&source=directphone&submittype=1&ktimes=8&hlv=1&rn=3083604310.80008875&jqpram=L7UtN7Z8&t=1608275340792&jqnonce=43ca9514-0da2-4463-bb8b-e22f2bed8b64&jqsign=%3C%3Bki1%3D9%3C%258li%3A%25%3C%3C%3E%3B%25jj0j%25m%3A%3An%3Ajml0j%3E%3C&u_asec=099%23KAFEjYEmExdEhGTLEEEEEpEQz0yFZ6VcSui5a6tFScvIW6AHZcloa6A3DmQTEE7EERpCuYFEFAYEqyZov3llls88%2FK9LOikjn0NXE7EFEE1Cb%2FUTEEalEwrdy8sllllGxOa4E7EFEI1CbP7TEEilluCVlYFETJDovlNhE7EhlAaP%2F3iSWEFE5YUkA7Ti1ZWcqQYt2f0q3IYvzaD4DYVkWLL86LxciiLgKW6r2T4IcuVUPJK41FGQsn8GfBxo8CrG5coSBFtIyUQVVHGbvFtrLLvgBwd6iLlgqXRbE7EUlllP%2F3iSlllllurdt3il%2FlllWsaStEgtlllO%2F3iS16allurdt37IncQTEEMFluuta3PoE7EIlllbCUEPtNBhE7EvEKhCbOaIcL%2BVJBDtUtxsHsbDSwZnZ0XZNV%2BulrRih0Yy8LSpztodBYFETEEEbOKZE7EKlG1P%2Fq9JlGC%2FfYFE19dEBsCl%2Fld7BJMTET5bEw1dzW9lF6xtYbCOCyvfXyhXZdyWE7EqlGTD%2F1M8llllhpkdBYFETEEEbOK%2BE7EhlGwP%2F3cYMYFET%2FllsyaaJY%3D%3D&u_atype=2', headers=headers, cookies=cookies, data=data)
