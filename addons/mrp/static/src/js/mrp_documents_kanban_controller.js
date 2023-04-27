odoo.define('mrp.MrpDocumentsKanbanController', function (require) {
"use strict";

/**
 * This file defines the Controller for the MRP Documents Kanban view, which is an
 * override of the KanbanController.
 */

const MrpDocumentsControllerMixin = require('mrp.controllerMixin');

const KanbanController = require('web.KanbanController');

const MrpDocumentsKanbanController = KanbanController.extend(MrpDocumentsControllerMixin, {
    events: Object.assign({}, KanbanController.prototype.events, MrpDocumentsControllerMixin.events),
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, MrpDocumentsControllerMixin.custom_events),

    /**
     * @override
    */
    init() {
        this._super(...arguments);
        MrpDocumentsControllerMixin.init.apply(this, arguments);
    },
    /**
     * Override to update the records selection.
     *
     * @override
    */
    async reload() {
        await this._super(...arguments);
        await MrpDocumentsControllerMixin.reload.apply(this, arguments);
    },
});

return MrpDocumentsKanbanController;

});
