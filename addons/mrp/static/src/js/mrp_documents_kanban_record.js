odoo.define('mrp.MrpDocumentsKanbanRecord', function (require) {
"use strict";

/**
 * This file defines the KanbanRecord for the MRP Documents Kanban view.
 */

const KanbanRecord = require('web.KanbanRecord');

const MrpDocumentsKanbanRecord = KanbanRecord.extend({
    events: _.extend({}, KanbanRecord.prototype.events, {
        'click .o_mrp_download': '_onDownload',
        'click .o_kanban_previewer': '_onImageClicked',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDownload(ev) {
        ev.preventDefault();
        window.location = '/web/content/' + this.modelName + '/' + this.id + '/' + 'datas' + '?download=true';
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onImageClicked(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('kanban_image_clicked', {
            recordList: [this.recordData],
            recordID: this.recordData.id
        });
    },
});

return MrpDocumentsKanbanRecord;

});
