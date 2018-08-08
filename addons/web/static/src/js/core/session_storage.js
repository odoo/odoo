odoo.define('web.sessionStorage', function (require) {
'use strict';

var RamStorage = require('web.RamStorage');
var mixins = require('web.mixins');

// use a fake sessionStorage in RAM if the native sessionStorage is unavailable
// (e.g. private browsing in Safari)
var storage;
var sessionStorage = window.sessionStorage;
try {
    var uid = new Date();
    sessionStorage.setItem(uid, uid);
    sessionStorage.removeItem(uid);

    /*
     * We create an intermediate object in order to triggered the storage on
     * this object. the sessionStorage. This simplifies testing and usage as 
     * starages are commutable in services without change. Also, objects
     * that use storage do not have to know that events go through window,
     * it's not up to them to handle these cases.
     */
    storage = (function () {
        var storage = Object.create(_.extend({
                getItem: sessionStorage.getItem.bind(sessionStorage),
                setItem: sessionStorage.setItem.bind(sessionStorage),
                removeItem: sessionStorage.removeItem.bind(sessionStorage),
                clear: sessionStorage.clear.bind(sessionStorage),
            },
            mixins.EventDispatcherMixin
        ));
        storage.init();
        $(window).on('storage', function (e) {
            var key = e.originalEvent.key;
            var newValue = e.originalEvent.newValue;
            try {
                JSON.parse(newValue);
                if (sessionStorage.getItem(key) === newValue) {
                    storage.trigger('storage', {
                        key: key,
                        newValue: newValue,
                    });
                }
            } catch (error) {}
        });
        return storage;
    })();

} catch (exception) {
    console.warn('Fail to load sessionStorage');
    storage = new RamStorage();
}

return storage;

});
