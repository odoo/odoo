odoo.define('web.view_registry', function (require) {
"use strict";

/**
 * This module defines the view_registry. Web views are added to the registry
 * in the 'web._view_registry' module to avoid cyclic dependencies.
 * Views defined in other addons should be added in this registry as well,
 * ideally in another module than the one defining the view, in order to
 * separate the declarative part of a module (the view definition) from its
 * 'side-effects' part.
 */

var Registry = require('web.Registry');

return new Registry();

});

odoo.define('web._view_registry', function (require) {
"use strict";

/**
 * The purpose of this module is to add the web views in the view_registry.
 * This can't be done directly in the module defining the view_registry as it
 * would produce cyclic dependencies.
 */

var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var CalendarView = require('web.CalendarView');
var view_registry = require('web.view_registry');

view_registry
    .add('form', FormView)
    .add('list', ListView)
    .add('kanban', KanbanView)
    .add('calendar', CalendarView);
});
