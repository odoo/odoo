odoo.define('web.search_bar_autocomplete_sources_registry', function (require) {
"use strict";

var Registry = require('web.Registry');

return new Registry();

});

odoo.define('web._search_bar_autocomplete_sources_registry', function(require) {
"use strict";

var registry = require('web.search_bar_autocomplete_sources_registry');
var SearchBarAutoCompleteSources = require('web.SearchBarAutoCompleteSources');

// fields
registry
    .add('char', SearchBarAutoCompleteSources.CharField)
    .add('text', SearchBarAutoCompleteSources.CharField)
    .add('html', SearchBarAutoCompleteSources.CharField)
    .add('boolean', SearchBarAutoCompleteSources.BooleanField)
    .add('integer', SearchBarAutoCompleteSources.IntegerField)
    .add('id', SearchBarAutoCompleteSources.IntegerField)
    .add('float', SearchBarAutoCompleteSources.FloatField)
    .add('monetary', SearchBarAutoCompleteSources.FloatField)
    .add('selection', SearchBarAutoCompleteSources.SelectionField)
    .add('datetime', SearchBarAutoCompleteSources.DateTimeField)
    .add('date', SearchBarAutoCompleteSources.DateField)
    .add('many2one', SearchBarAutoCompleteSources.ManyToOneField)
    .add('many2many', SearchBarAutoCompleteSources.CharField)
    .add('one2many', SearchBarAutoCompleteSources.CharField);

// others
registry.add('filter', SearchBarAutoCompleteSources.Filter);
registry.add('groupby', SearchBarAutoCompleteSources.GroupBy);

});
