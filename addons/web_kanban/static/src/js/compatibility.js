odoo.define('web_kanban.compatibility', ['web_kanban.common', 'web_kanban.KanbanView'], function (require) {
"use strict";

var common = require('web_kanban.common');
var KanbanView = require('web_kanban.KanbanView');

return;
openerp = window.openerp || {};
openerp.web_kanban = openerp.web_kanban || {};
openerp.web_kanban.AbstractField = common.AbstractField;
openerp.web_kanban.KanbanGroup = common.KanbanGroup;
openerp.web_kanban.KanbanRecord = common.KanbanRecord;
openerp.web_kanban.KanbanView = KanbanView;

});
