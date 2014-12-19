# -*- coding: utf-8 -*-
import logging
import os
import time

import openerp
import openerp.addons.hw_proxy.controllers.main as hw_proxy
import threading
from openerp import http
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

upgrade_template = """
<!DOCTYPE HTML>
<html>
    <head>
        <title>Odoo's PosBox - Software Upgrade</title>
        <script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
        <script>
        $(function(){
            var upgrading = false;
            $('#upgrade').click(function(){
                console.log('click');
                if(!upgrading){
                    upgrading = true;
                    $('#upgrade').text('Upgrading, Please Wait');
                    $.ajax({
                        url:'/hw_proxy/perform_upgrade/'
                    }).then(function(status){
                        $('#upgrade').html('Upgrade Successful<br \\>Click to Restart the PosBox');
                        $('#upgrade').off('click');
                        $('#upgrade').click(function(){
                            $.ajax({ url:'/hw_proxy/perform_restart' })
                            $('#upgrade').text('Restarting');
                            $('#upgrade').off('click');
                            setTimeout(function(){
                                window.location = '/'
                            },30*1000);
                        });

                    },function(){
                        $('#upgrade').text('Upgrade Failed');
                    });
                }
            });
        });
        </script>
        <style>
        body {
            width: 480px;
            margin: 60px auto;
            font-family: sans-serif;
            text-align: justify;
            color: #6B6B6B;
        }
        .centering{
            text-align: center;
        }
        #upgrade {
            padding: 20px;
            background: rgb(121, 197, 107);
            color: white;
            border-radius: 3px;
            text-align: center;
            margin: 30px; 
            text-decoration: none;
            display: inline-block;
        }
        </style>
    </head>
    <body>
        <h1>PosBox Software Upgrade</h1>
        <p>
        This tool will help you perform an upgrade of the PosBox's software.
        However the preferred method to upgrade the posbox is to flash the sd-card with
        the <a href='http://nightly.openerp.com/trunk/posbox/'>latest image</a>. The upgrade
        procedure is explained into to the <a href='/hw_proxy/static/doc/manual.pdf'>PosBox manual</a>
        </p>
        <p>
        To upgrade the posbox, click on the upgrade button. The upgrade will take a few minutes. <b>Do not reboot</b> the PosBox during the upgrade.
        </p>
        <div class='centering'>
            <a href='#' id='upgrade'>Upgrade</a>
        </div>
    </body>
</html>

"""

class PosboxUpgrader(hw_proxy.Proxy):
    def __init__(self):
        super(PosboxUpgrader,self).__init__()
        self.upgrading = threading.Lock()
        self.last_upgrade = 0

    @http.route('/hw_proxy/upgrade', type='http', auth='none', )
    def upgrade(self):
        return upgrade_template 
    
    @http.route('/hw_proxy/perform_upgrade', type='http', auth='none')
    def perform_upgrade(self):
        self.upgrading.acquire()
        if time.time() - self.last_upgrade < 30:
            self.upgrading.release()
            return 'UPTODATE'
        else:
            os.system('/bin/bash /home/pi/openerp/update.sh')
            self.last_upgrade = time.time()
            self.upgrading.release()
            return 'SUCCESS'

    @http.route('/hw_proxy/perform_restart', type='http', auth='none')
    def perform_restart(self):
        self.upgrading.acquire()
        if time.time() - self.last_upgrade < 30:
            self.upgrading.release()
            return 'RESTARTED'
        else:
            os.system('/bin/bash /home/pi/openerp/restart.sh')
            self.last_upgrade = time.time()
            self.upgrading.release()
            return 'SUCCESS'

        
