odoo.define('web_editor.base', function (require) {
"use strict";

var core = require('web.core');
var ajax = require('web.ajax');
var qweb = core.qweb;
var _t = core._t;

var get_context = function (dict) {
    var html = document.documentElement;
    return _.extend({
        'lang': (html.getAttribute('lang') || '').replace('-', '_'),
    }, dict);
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////

var data = {
    'get_context': get_context,
};

var dom_ready = $.Deferred();
$(document).ready(function () {
    dom_ready.resolve(data);
    // fix for ie
    if($.fn.placeholder) $('input, textarea').placeholder();
});

return dom_ready;

});
