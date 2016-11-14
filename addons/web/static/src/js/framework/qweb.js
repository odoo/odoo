odoo.define('web.QWeb', function (require) {
"use strict";

var translation = require('web.translation');

var _t = translation._t;

function QWeb(debug, default_dict) {
    var qweb = new QWeb2.Engine();
    qweb.default_dict = _.extend({}, default_dict || {}, {
        '_' : _,
        'JSON': JSON,
        '_t' : translation._t,
        '__debug__': debug,
        'moment': function(date) { return new moment(date); },
        'csrf_token': odoo.csrf_token,
    });
    qweb.debug = debug;
    return qweb;
}

return QWeb;

});
