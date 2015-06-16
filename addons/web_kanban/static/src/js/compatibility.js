odoo.define('web_kanban.compatibility', function (require) {
"use strict";

var kanban_widgets = require('web_kanban.widgets');
var KanbanRecord = require('web_kanban.Record');
var KanbanColumn = require('web_kanban.Column');
var KanbanView = require('web_kanban.KanbanView');

return;
openerp = window.openerp || {};
openerp.web_kanban = openerp.web_kanban || {};
openerp.web_kanban.AbstractField = kanban_widgets.AbstractField;
openerp.web_kanban.KanbanGroup = KanbanColumn;
openerp.web_kanban.KanbanRecord = KanbanRecord;
openerp.web_kanban.KanbanView = KanbanView;

});
