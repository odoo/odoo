/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useState } = owl;
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";
var rpc = require('web.rpc');
/**
 * Loading Indicator Extend
 */
export class LoadingIndicatorDebug extends LoadingIndicator {
    setup() {
        this.state = useState({
            count: 0,
            show: false,
        });
        this.rpcIds = new Set();
        this.env.bus.on("RPC:REQUEST", this, this.requestCall);
        this.env.bus.on("RPC:RESPONSE", this, this.responseCall);
        this.uiService = useService("ui");
        var self = this
        if (odoo.debug){
        rpc.query({
            model: 'res.users',
            method: 'has_debug_group',
            args: ['odx_restrict_debug.group_allow_debug'],
        }).then(function(hasGroup) {
            if (!hasGroup) {
            $(document.body).addClass('o_ui_blocked');
            $.blockUI.apply($, arguments);
        var newDiv = document.createElement('div');
        document.addEventListener('keydown', function() {
          if (event.keyCode == 16) {
                alert("This Operation is not Allowed, Please Contact Administrator");
                return false;
              } else if (event.ctrlKey && event.shiftKey) {
                alert("This function has been disabled to prevent you from stealing my code!");
                return false;
              }
          }, false);

        if (document.addEventListener) {
          document.addEventListener('contextmenu', function(e) {
            alert("This Operation is not Allowed, Please Contact Administrator");
            e.preventDefault();
          }, false);
        } else {
          document.attachEvent('oncontextmenu', function() {
            alert("This Operation is not Allowed, Please Contact Administrator");
            window.event.returnValue = false;
          });
        }
        //Set content inside the new div
        newDiv.textContent = 'You Are Not Allowed To Continue With Debug Mode Please Contact Administrator or Turn Off Debug';
        var turnOffDebugButton = document.createElement('button');
        turnOffDebugButton.textContent = 'Turn Off Debug Mode';
        turnOffDebugButton.style.marginTop = '10px';
        turnOffDebugButton.style.marginTop = '10px';
        turnOffDebugButton.style.padding = '8px 12px';
        //turnOffDebugButton.style.backgroundColor = '#c9aa42';
        turnOffDebugButton.style.backgroundColor = '#c9aa42';
        turnOffDebugButton.style.color = 'white';
        turnOffDebugButton.style.fontSize = '16px';
        turnOffDebugButton.style.fontWeight = 'bold';
        turnOffDebugButton.style.width = '810px';
        turnOffDebugButton.style.borderColor = '#c9aa42';

        // Add the button to the new div
        newDiv.appendChild(turnOffDebugButton);

        // Add styles to the new div
        newDiv.style.position = 'fixed';
        newDiv.style.top = '50%';
        newDiv.style.left = '50%';
        newDiv.style.transform = 'translate(-50%, -50%)';
        newDiv.style.backgroundColor = 'transparent';
        newDiv.style.padding = '20px';
        newDiv.style.fontWeight = 'bold';
        //newDiv.style.color = 'black';
        newDiv.style.fontSize = '18px';
        // Append the new div to the blockUIElement
        var blockUIElement = document.querySelector('.blockUI.blockOverlay');
        blockUIElement.appendChild(newDiv);
        turnOffDebugButton.onclick = function() {
            // Get the current URL
            // Replace 'debug=1' with 'debug=0' in the URL
            // Update the URL in the address bar
            // Reload the page
            var currentURL = window.location.href;
            var newURL = currentURL
            if (currentURL.includes('debug=assets%2Ctests')) {
            newURL = currentURL.replace(/(\?|&)debug=assets%2Ctests(&|#|$)/, '$1debug=0$2');
            }
            else if (currentURL.includes('debug=assets')) {
            newURL = currentURL.replace(/(\?|&)debug=assets(&|#|$)/, '$1debug=0$2');
            }
            else if (currentURL.includes('debug=1')) {
            newURL = currentURL.replace(/(\?|&)debug=1(&|#|$)/, '$1debug=0$2');
            }
            else{
            newURL = currentURL.replace('/web#', '/web?debug=0#');
            }
            window.history.replaceState({}, document.title, newURL);
            location.reload();
        };
        alert("You Are Not Allowed To Continue With Debug Mode Please Contact Administrator or Turn Off Debug");
        //Logout
        var LogoutUrl = window.location.origin + "/web/session/logout?debug=0"
        window.history.replaceState({}, document.title, LogoutUrl);
        location.reload();

        }
            }).catch(function(error) {
                console.error('Error checking user group:', error);
            });
        }
    }
}

registry.category("main_components").add("LoadingIndicatorDebug", {
    Component: LoadingIndicatorDebug,
});

