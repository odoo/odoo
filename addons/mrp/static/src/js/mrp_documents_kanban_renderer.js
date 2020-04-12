odoo.define('mrp.MrpDocumentsKanbanRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the MRP Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

const KanbanRenderer = require('web.KanbanRenderer');
const MrpDocumentsKanbanRecord = require('mrp.MrpDocumentsKanbanRecord');

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

return MrpDocumentsKanbanRenderer;

});
