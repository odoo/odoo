(function() {
"use strict";

var instance = openerp;
var Class    = instance.web.Class;

// The Android/iPhone App is a JS/HTML app that launches the
// Odoo webclient in an iframe, using the Cordova framework.
//
// This class acts as a link between the webclient and the
// Odoo Android/iPhone App implemented with cordova.

instance.web.Cordova = Class.extend({}, instance.web.PropertiesMixin, {
    init: function(parent) {
        var self = this;
        instance.web.PropertiesMixin.init.call(this, parent);

        window.addEventListener('message', function(event) {
            self.receive(event);
        }, false);

    },
    // odoo.send('foobar') in cordova will call messages.foobar()
    messages: {
        // launch the POS !
        pos: function() {
            if (window.location.href.indexOf('/pos/web') < 0) {
                window.location.href = "/pos/web";
            }
        },
    },
    // what happens when we receive an event from cordova
    // -> call messages[event.data]()
    // -> selfs trigger(event.data)
    receive: function(event) {
        if (event.origin !== 'file://') {
            return;
        } 

        if (typeof event.data === 'string') {
            this.trigger(event.data);
            if (this.messages[event.data]) {
                this.messages[event.data].call(this);
            }
        }
    },
    // send a message to cordova
    send: function(message) {
        function inIframe(){
            try {
                return window.self !== window.top;
            } catch (e) {
                return true;
            }
        }
        if (inIframe()) {
            window.parent.postMessage(message,'file://');
        }
    },


    // notifies cordova that the webclient is ready.
    ready:      function() { this.send('ready');     },
    // notifies cordova that we want to exit the app.
    logout:     function() { this.send('logout');    },
    // notifies cordova that the point of sale is ready.
    posready:   function() { this.send('posready');  },
    // notifies cordova that we want to exit the point of sale.
    poslogout:  function() { this.send('poslogout'); },
    // asks cordova to emit a beep.
    beep:       function() { this.send('beep');      },
    // ask cordova to vibrate the phone.
    vibrate:    function() { this.send('vibrate');   },
});

// Singleton module
instance.web.cordova = new instance.web.Cordova();
})();
