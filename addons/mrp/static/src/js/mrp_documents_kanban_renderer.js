/** @odoo-module **/

/**
 * This file defines the Renderer for the MRP Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

import KanbanRenderer from 'web.KanbanRenderer';
import MrpDocumentsKanbanRecord from '@mrp/js/mrp_documents_kanban_record';

const MrpDocumentsKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanRecord: MrpDocumentsKanbanRecord,
    }),
    /**
     * @override
     */
    async start() {
        this.$el.addClass('o_mrp_documents_kanban_view');
        await this._super(...arguments);
    },
});

export default MrpDocumentsKanbanRenderer;
