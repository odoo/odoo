
import openerpweb

class IM(openerpweb.Controller):
    def __init__(self):
        super(IM, self).__init__()
        return;
    
    def chat_login(self, username, password):
        return dict()
    
    def chat_logout(self):
        return dict()
    
    def send(self):
        return dict()
    
    def status(self, status, message):
        return dict()
    
    def poll(self, method):
        return dict()
