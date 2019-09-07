odoo.define('web.QuickCreateFormView', function (require) {
"use strict";

/**
 * This file defines the QuickCreateFormView, an extension of the FormView that
 * is used by the RecordQuickCreate in Kanban views.
 */

var BasicModel = require('web.BasicModel');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');

var QuickCreateFormRenderer = FormRenderer.extend({
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_xxs_form_view');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        var direction = ev.data.direction;
        if (direction === 'cancel' || direction === 'next_line') {
            ev.stopPropagation();
            this.trigger_up(direction === 'cancel' ? 'cancel' : 'add');
        } else {
            this._super.apply(this, arguments);
        }
    },
});

var QuickCreateFormModel = BasicModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object} the changes of the given resource (server commands for
     *   x2manys)
     */
    getChanges: function (localID) {
        var record = this.localData[localID];
        return this._generateChanges(record, {changesOnly: false});
    },
});

var QuickCreateFormController = FormController.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Asks all field widgets to notify the environment with their current value
     * (useful for instance for input fields that still have the focus and that
     * could have not notified the environment of their changes yet).
     * Synchronizes with the controller's mutex in case there would already be
     * pending changes being applied.
     *
     * @return {Promise}
     */
    commitChanges: function () {
        var mutexDef = this.mutex.getUnlockedDef();
        return Promise.all([mutexDef, this.renderer.commitChanges(this.handle)]);
    },
    /**
     * @returns {Object} the changes done on the current record
     */
    getChanges: function () {
        return this.model.getChanges(this.handle);
    },
});

var QuickCreateFormView = FormView.extend({
    withControlPanel: false,
    config: _.extend({}, FormView.prototype.config, {
        Model: QuickCreateFormModel,
        Renderer: QuickCreateFormRenderer,
        Controller: QuickCreateFormController,
    }),
});

return QuickCreateFormView;

});
