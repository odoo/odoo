import requests

def sendNotification(auth_token, dispositivo_token, data, notification):
    url = 'fcm.googleapis.com/v1/projects/fir-notificacion-41516/messages:send HTTP/1.1'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': auth_token,
        'Content-Length': 684
    }
    data = {
        'message': {
            'token': dispositivo_token,
            'data': data,
            'notification': {
                'title': notification['title'],
                'body': notification['body']
            },
            "android": {
                "notification": {
                    "image": "https://i.pinimg.com/564x/81/99/26/81992670e52a84bc219c9e1f7a454a23.jpg"
                }
            }
        }
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 200
        