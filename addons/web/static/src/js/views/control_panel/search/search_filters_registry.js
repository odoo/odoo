odoo.define('web.search_filters_registry', function (require) {
"use strict";

var Registry = require('web.Registry');

return new Registry();

});

odoo.define('web._search_filters_registry', function(require) {
"use strict";

var registry = require('web.search_filters_registry');
var search_filters = require('web.search_filters');

registry
    .add('boolean', search_filters.Boolean)
    .add('char', search_filters.Char)
    .add('date', search_filters.Date)
    .add('datetime', search_filters.DateTime)
    .add('float', search_filters.Float)
    .add('id', search_filters.Id)
    .add('integer', search_filters.Integer)
    .add('many2many', search_filters.Char)
    .add('many2one', search_filters.Char)
    .add('monetary', search_filters.Float)
    .add('one2many', search_filters.Char)
    .add('text', search_filters.Char)
    .add('selection', search_filters.Selection);
});
