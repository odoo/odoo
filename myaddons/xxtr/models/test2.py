import requests
import re
cookies = {
    '.ASPXANONYMOUS': '6oNFc5EL1wEkAAAAOTA3NmRiNDctNTdjYi00ODZhLWJhODUtZDI5OTU5NmUxMDM1qcD1g4n5SrSG_O1J3fO_Frqm8dU1',
    '_uab_collina': '160826973914100214091184',
    'ASP.NET_SessionId': '24lkexn3uryam223aiut1pqq',
    'Hm_lvt_21be24c80829bd7a683b2c536fcf520b': '1608270273',
    'jpckey': '^%^E5^%^8C^%^96^%^E5^%^A6^%^86',
    'LastActivityJoin': '101601324,108094547017',
    'join_101601324': '1',
    'acw_tc': '76b20f6816082721944146230e152d1f130cf5c9f9958c5f964763402f8330',
    'jac101601324': '04025017',
    'SERVERID': '0f3eb8fcde19feef85b46d49c555413b^|1608272239^|1608269736',
    'u_asec': '099^%^23KAFE27EKEqFEhYTLEEEEEpEQz0yFZ6VcSuiIC6zhSXBFW6fFSrBYQ6fcDEFETcZdt9TXE7EFbOR5DqMTE1XCXPi56wO3aUVEutxsrQdtLSCbYOFn97DtlrimhALu9LWluzrVc6wrE7EhssaZttaMBEFE1cZdtM36tiETsEFEpcZdt3illuZdsyaCd^%^2FllsZsP^%^2F3RClllrncZdd^%^2FRlluWFsyaCd^%^2FllsUiUE7Tx16ZoEHq0mWEsVZfvHDSsVZngBB7qLhWGp9N4kYAB6^%^2Fozukj2wmoZVxXv3i26w^%^2BXL0RANIEac2RjQb1ECLzArUBWvyCT0DLO4m^%^2FPAf6G2IsT7VFMTEEyP^%^2F9iSllluE7EFL2xhGG^%^3D^%^3D',
    'Hm_lpvt_21be24c80829bd7a683b2c536fcf520b': '1608272241',
    'ssxmod_itna': 'QqU2DK4mxjhxXDnD+g=O5Dtfp8DRhGhB2du4GXoG8zDnqD=GFDK40E5gAjwRqpa8YG3BDdLK0DaKKrWhWO5W5IFSxGLDmKDyKAB2oDxOq0rD74irDDxD3Db8dDSDWKD97qi3DEAKiaDi4D+WwQDmqG0DDt7R4G2D7tc7ihqWd0j3CUKwkGDv74cD0U5xBLaY6RedZnqnqPRDB=7xBjSIT=B8eDH32oP+BhzWBmxirhoYBvNRG5+VB+qDgOGvBGN/pvqf94ULBDDGfS38O4xD',
    'ssxmod_itna2': 'QqU2DK4mxjhxXDnD+g=O5Dtfp8DRhGhB2dqA6uAwxD/+KtDFhwr/3xAIFGFKAppEHtOrU=Ev=wQSprKr4ZYYu9eml/Wm8uvyt0c7WzTIrWBBOhMrFM5UeO+6LkzTh9dLrSTauugXuIS5SRMKHKuIEIijVUO54YRvkWY5P8gv2/O+5ph5PIOuFCRTiwintXBKT64cfQ=b9I7aPicoOkO48rWcFjEtX8odzWk3zGMnhpo39bFYF=zLvaCaQv8goSl7I6rA+HfpYceoQE=312IojvOOW=jpOKMAykHxTh5MPMgC5cXZi5THegTo2sI8QrRYxfTD+d2wr1+Fe4+3LhnSQw4kHj13nTxxNTWw2dmFlw1lhbb+tC=0kiLxkoTQQTNLxTonpOuwwgp9QT1f3sx=BQtTAIRTv1Sk5p5VlIdp+3pYngO97A0dfLWA7cEmEm5TtowLtPIZ0YAj574k2WKLLsG3tMM4L2svOsg0z/ubbfwgq8ikG/ET3bQ4dddSeD7QR7ydxfolx+WD8E7T=Dlg7YXGklxm0f=G=PidKWEX0IQexkDSv0DtvrTkYjpq5DGcDG75iDD=',
}

headers = {
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

response = requests.get('https://www.wjx.cn/m/101612165.aspx', headers=headers, cookies=cookies)
# print(response.text)
jqnonce = re.search(r'.{8}-.{4}-.{4}-.{4}-.{12}', response.text).group()
print(jqnonce)