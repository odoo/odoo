odoo.define('mrp.MrpDocumentsKanbanView', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const MrpDocumentsKanbanController = require('mrp.MrpDocumentsKanbanController');
const MrpDocumentsKanbanRenderer = require('mrp.MrpDocumentsKanbanRenderer');
const viewRegistry = require('web.view_registry');

const MrpDocumentsKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: MrpDocumentsKanbanController,
        Renderer: MrpDocumentsKanbanRenderer,
    }),
});

viewRegistry.add('mrp_documents_kanban', MrpDocumentsKanbanView);

return MrpDocumentsKanbanView;

});
