
odoo.define('point_of_sale.main', function (require) {
"use strict";

var chrome = require('point_of_sale.chrome');
var core = require('web.core');

core.action_registry.add('pos.ui', chrome.Chrome);

});
