/** @odoo-module **/

import KanbanView from 'web.KanbanView';
import MrpDocumentsKanbanController from '@mrp/js/mrp_documents_kanban_controller';
import MrpDocumentsKanbanRenderer from '@mrp/js/mrp_documents_kanban_renderer';
import viewRegistry from 'web.view_registry';

const MrpDocumentsKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: MrpDocumentsKanbanController,
        Renderer: MrpDocumentsKanbanRenderer,
    }),
});

viewRegistry.add('mrp_documents_kanban', MrpDocumentsKanbanView);

export default MrpDocumentsKanbanView;
