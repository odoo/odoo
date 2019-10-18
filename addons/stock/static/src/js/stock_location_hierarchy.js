odoo.define('stock.stock_location_hierarchy_qweb', function (require) {
"use strict";

var QwebView = require('web.qweb');
var registry = require('web.view_registry');


var QWebView = QwebView.View.extend({
    icon: 'fa-sitemap',
    searchMenuTypes: ['filter', 'favorite'],
});

registry.add('stock_location_hierarchy_qweb', QWebView);

return {
    View: QWebView,
};

});
