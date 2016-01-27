odoo.define('web_editor.base', function (require) {
"use strict";

var data = {
    get_context: function (dict) {
        var html = document.documentElement;
        return _.extend({
            'lang': (html.getAttribute('lang') || '').replace('-', '_'),
        }, dict);
    }
};

var dom_ready = $.Deferred();
$(document).ready(function () {
    dom_ready.resolve(data);
    // fix for ie
    if($.fn.placeholder) $('input, textarea').placeholder();
});

return dom_ready;

});
