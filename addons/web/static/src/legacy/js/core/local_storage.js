odoo.define('web.local_storage', function (require) {
'use strict';

var RamStorage = require('web.RamStorage');
var mixins = require('web.mixins');

// use a fake localStorage in RAM if the native localStorage is unavailable
// (e.g. private browsing in Safari)
var storage;
var localStorage = window.localStorage;
try {
    var uid = new Date();
    localStorage.setItem(uid, uid);
    localStorage.removeItem(uid);

    /*
     * We create an intermediate object in order to triggered the storage on
     * this object. the localStorage. This simplifies testing and usage as 
     * starages are commutable in services without change. Also, objects
     * that use storage do not have to know that events go through window,
     * it's not up to them to handle these cases.
     */
    storage = (function () {
        var storage = Object.create(_.extend({
                getItem: localStorage.getItem.bind(localStorage),
                setItem: localStorage.setItem.bind(localStorage),
                removeItem: localStorage.removeItem.bind(localStorage),
                clear: localStorage.clear.bind(localStorage),
            },
            mixins.EventDispatcherMixin
        ));
        storage.init();
        $(window).on('storage', function (e) {
            var key = e.originalEvent.key;
            var newValue = e.originalEvent.newValue;
            try {
                JSON.parse(newValue);
                storage.trigger('storage', {
                    key: key,
                    newValue: newValue,
                });
            } catch (_error) {}
        });
        return storage;
    })();

} catch (_exception) {
	console.warn('Fail to load localStorage');
    storage = new RamStorage();
}

return storage;

});
