odoo.define('web_editor.base', function (require) {
"use strict";

var ajax = require('web.ajax');
var session = require('web.session');

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
    if ($.fn.placeholder) $('input, textarea').placeholder();
});
data.dom_ready = dom_ready;

// todo: remove and load a bundle of translated templates
data.ready = function () {
    return $.when(dom_ready, session.is_bound, ajax.loadXML());
};

return dom_ready;

});
