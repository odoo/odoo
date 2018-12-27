odoo.define('mass_mailing.ListKanbanView', function (require) {
"use strict";

var MassMailingListKanbanRenderer = require('mass_mailing.ListKanbanRenderer');

var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var MassMailingListKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: MassMailingListKanbanRenderer,
    }),
});

view_registry.add('mass_mailing_list_kanban', MassMailingListKanbanView);

return MassMailingListKanbanView;

});
