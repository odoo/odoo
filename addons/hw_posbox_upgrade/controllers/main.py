# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import subprocess
import threading

from odoo import http

from odoo.addons.hw_proxy.controllers import main as hw_proxy

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
                        $('#upgrade').html('Upgrade successful, restarting the posbox...');
                        $('#upgrade').off('click');
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
        This tool will help you perform an upgrade of the PosBox's software over the
	internet. 
	<p></p>
        However the preferred method to upgrade the posbox is to flash the sd-card with
        the <a href='http://nightly.odoo.com/trunk/posbox/'>latest image</a>. The upgrade
        procedure is explained into to the
        <a href='https://www.odoo.com/documentation/user/point_of_sale/posbox/index.html'>PosBox manual</a>
        </p>
        <p>
        To upgrade the posbox, click on the upgrade button. The upgrade will take a few minutes. <b>Do not reboot</b> the PosBox during the upgrade.
        </p>
        <p>
        Latest patch:
        </p>
        <pre>
"""
upgrade_template += subprocess.check_output("git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git log -1", shell=True).decode('utf-8').replace("\n", "<br/>")
upgrade_template += """
        </pre>
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

    @http.route('/hw_proxy/upgrade', type='http', auth='none', )
    def upgrade(self):
        return upgrade_template 
    
    @http.route('/hw_proxy/perform_upgrade', type='http', auth='none')
    def perform_upgrade(self):
        self.upgrading.acquire()

        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/posbox_update.sh')
        
        self.upgrading.release()
        return 'SUCCESS'
