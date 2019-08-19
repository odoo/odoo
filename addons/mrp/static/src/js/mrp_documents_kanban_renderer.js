odoo.define('mrp.MrpDocumentsKanbanRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the MRP Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

const KanbanRenderer = require('web.KanbanRenderer');
const MrpDocumentsKanbanRecord = require('mrp.MrpDocumentsKanbanRecord');

const MrpDocumentsKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: MrpDocumentsKanbanRecord,
    }),
    init: function () {
        this._super.apply(this, arguments);
        this.className += ' o_mrp_documents_kanban_view';
    },
});

return MrpDocumentsKanbanRenderer;

});
