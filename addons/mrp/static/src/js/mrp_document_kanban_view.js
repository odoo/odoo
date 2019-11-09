odoo.define('mrp.MrpDocumentsKanbanView', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const MrpDocumentsKanbanController = require('mrp.MrpDocumentsKanbanController');
const MrpDocumentsKanbanRenderer = require('mrp.MrpDocumentsKanbanRenderer');
const view_registry = require('web.view_registry');

var MrpDocumentsKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: MrpDocumentsKanbanController,
        Renderer: MrpDocumentsKanbanRenderer,
    }),
});

view_registry.add('mrp_documents_kanban', MrpDocumentsKanbanView);

return MrpDocumentsKanbanView;

});
