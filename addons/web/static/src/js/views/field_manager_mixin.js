odoo.define('web.FieldManagerMixin', function (require) {
"use strict";

/**
 * The FieldManagerMixin is a mixin, designed to do the plumbing between field
 * widgets and a basicmodel.  Field widgets can be used outside of a view.  In
 * that case, someone needs to listen to events bubbling up from the widgets and
 * calling the correct methods on the model.  This is the field_manager's job.
 */

var BasicModel = require('web.BasicModel');

var FieldManagerMixin = {
    custom_events: {
        discard_changes: '_onDiscardChanges',
        discard_line: '_onDiscardLine',
        field_changed: '_onFieldChanged',
        load: '_onLoad',
    },
    /**
     * A FieldManagerMixin can be initialized with an instance of a basicModel.
     * If not, it will simply uses its own.
     *
     * @param {BasicModel} [model]
     */
    init: function (model) {
        this.model = model || new BasicModel(this);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply changes by notifying the basic model, then saving the data if
     * necessary, and finally, confirming the changes to the UI.
     *
     * @todo find a way to remove ugly 3rd argument...
     *
     * @param {string} dataPointID
     * @param {Object} changes
     * @param {OdooEvent} event
     * @returns {Deferred} resolves when the change has been done, and the UI
     *   updated
     */
    _applyChanges: function (dataPointID, changes, event) {
        var self = this;
        return this.model.notifyChanges(dataPointID, changes)
            .then(function (result) {
                if (event.data.force_save) {
                    return self.model.save(dataPointID).then(function () {
                        return self._confirmSave(dataPointID);
                    });
                } else {
                    return self._confirmChange(dataPointID, result, event);
                }
            });
    },
    /**
     * This method will be called whenever a field value has changed (and has
     * been confirmed by the model).
     *
     * @abstract
     * @param {string} id basicModel Id for the changed record
     * @param {string[]} fields the fields (names) that have been changed
     * @param {OdooEvent} event the event that triggered the change
     * @returns {Deferred}
     */
    _confirmChange: function (id, fields, event) {
        return $.when();
    },
    /**
     * This method will be called whenever a save has been triggered by a change
     * in some controlled field value.  For example, when a priority widget is
     * being changed in a readonly form.
     *
     * @see _onFieldChanged
     * @abstract
     * @param {string} id The basicModel ID for the saved record
     * @returns {Deferred}
     */
    _confirmSave: function (id) {
        return $.when();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Controlled elements might want to ask for a discard of the changes made
     * to a whole record (see editable list view). In that case, this handler
     * is called and call the appropriate @see BasicModel.discardChanges
     * function. The result is then notified thanks to a call to
     * @see _confirmChange.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardChanges: function (ev) {
        this.model.discardChanges(ev.data.id);
        this._confirmChange(ev.data.id, [], ev); // TODO get real list of changes ?
    },
    /**
     * In some case, we may need to remove an element from a list, without going
     * through the notifyChanges machinery.  The motivation for this is when the
     * user click on 'Add an item' in a field one2many with a required field,
     * then clicks somewhere else.  The new line need to be discarded, but we
     * don't want to trigger a real notifyChanges (no need for that, and also,
     * we don't want to rerender the UI).
     *
     * @param {OdooEvent} event
     */
    _onDiscardLine: function (event) {
        this.model.removeLine(event.data.id);
    },
    /**
     * This is the main job of the FMM: deciding what to do when a controlled
     * field changes.  Most of the time, it notifies the model that a change
     * just occurred, then confirm the change.
     *
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        // in case of field changed in relational record (e.g. in the form view
        // of a one2many subrecord), the field_changed event must be stopped as
        // soon as is it handled by a field_manager (i.e. the one of the
        // subrecord's form view), otherwise it bubbles up to the main form view
        // but its model doesn't have any data related to the given dataPointID
        event.stopPropagation();
        this._applyChanges(event.data.dataPointID, event.data.changes, event);
    },
    /**
     * Some widgets need to trigger a reload of their data.  For example, a
     * one2many with a pager needs to be able to fetch the next page.  To do
     * that, it can trigger a load event. This will then ask the model to
     * actually reload the data, then call the on_success callback.
     *
     * @param {OdooEvent} event
     * @param {number} [event.data.limit]
     * @param {number} [event.data.offset]
     * @param {function} [event.data.on_success] callback
     */
    _onLoad: function (event) {
        var self = this;
        var data = event.data;
        if (!data.on_success) { return; }
        var params = {};
        if ('limit' in data) {
            params.limit = data.limit;
        }
        if ('offset' in data) {
            params.offset = data.offset;
        }
        this.model.reload(data.id, params).then(function (db_id) {
            data.on_success(self.model.get(db_id));
        });
    },
};

return FieldManagerMixin;
});
