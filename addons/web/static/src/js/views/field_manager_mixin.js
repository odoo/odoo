odoo.define('web.FieldManagerMixin', function (require) {
"use strict";

/**
 * The FieldManagerMixin is a mixin, designed to do the plumbing between field
 * widgets and a basicmodel.  Field widgets can be used outside of a view.  In
 * that case, someone needs to listen to events bubbling up from the widgets and
 * calling the correct methods on the model.  This is the field_manager's job.
 */

var BasicModel = require('web.BasicModel');
var Dialog = require('web.Dialog');
var core = require('web.core');

var qweb = core.qweb;

return {
    custom_events: {
        field_changed: '_onFieldChanged',
        name_create: '_onNameCreate',
        name_get: '_onNameGet',
        name_search: '_onNameSearch',
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
     * This method will be called whenever a field value has changed (and has
     * been confirmed by the model).
     *
     * @abstract
     * @param {string} id basicModel Id for the changed record
     * @param {string[]} fields the fields (names) that have been changed
     * @param {OdooEvent} event the event that triggered the change
     */
    _confirmChange: function (id, fields, event) {
        // to be implemented
    },
    /**
     * This method will be called whenever a save has been triggered by a change
     * in some controlled field value.  For example, when a priority widget is
     * being changed in a readonly form.
     *
     * @see _onFieldChanged
     * @abstract
     * @param {string} id The basicModel ID for the saved record
     */
    _confirmSave: function (id) {
        // to be implemented, if necessary
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This is the main job of the FMM: deciding what to do when a controlled
     * field changes.  Most of the time, it notifies the model that a change
     * just occurred, then confirm the change.
     *
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        var self = this;
        // in case of field changed in relational record (e.g. in the form view of a one2many
        // subrecord), the field_changed event must be stopped as soon as is it handled by a
        // field_manager (i.e. the one of the subrecord's form view), otherwise it bubbles up to
        // the main form view but its model doesn't have any data related to the given dataPointID
        event.stopPropagation();
        var dataPointID = event.data.dataPointID;
        this.model.notifyChanges(dataPointID, event.data.changes).then(function (result) { // FIXME if datamodel is not a BasicModel, notifyChanges does not exists
            if (event.data.force_save) {
                self.model.save(dataPointID).then(function () {
                    self._confirmSave(dataPointID);
                });
            } else {
                self._confirmChange(dataPointID, result, event);
            }
        }).fail(function (warning) {
            new Dialog(self, {
                size: 'medium',
                title: warning.title,
                $content: qweb.render("CrashManager.warning", warning)
            }).open();
        });
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
    /**
     * When a name_create event arrives, the nameCreate method from the model
     * should be called.
     *
     * @param {OdooEvent} event
     */
    _onNameCreate: function (event) {
        var data = event.data;
        if (!data.on_success) { return; }
        this.model
            .nameCreate(data.model, data.name)
            .then(data.on_success)
            .fail(function () {
                if (data.on_fail) {
                    data.on_fail();
                }
            });
    },
    /**
     * When a name_get event arrives, the name_get method from the model should
     * be called.
     *
     * @param {OdooEvent} event
     */
    _onNameGet: function (event) {
        var data = event.data;
        if (!data.on_success) { return; }
        this.model.name_get(data.model, data.ids)
                  .then(data.on_success); // fixme: handle context
    },
    /**
     * Some field widgets need to perform a namesearch. For example, a many2one
     * widget when it needs to fetch its autocompletion data.
     *
     * @todo Note: I think that this is wrong, the field widget should just perform
     * a name_search rpc on its own, no need for this.
     *
     * @deprecated Just do a regular name_search
     * @param {OdooEvent} event
     */
    _onNameSearch: function (event) {
        var data = event.data;
        if (!data.on_success) { return; }
        this.model
            .nameSearch(data.model, data.search_val, data.domain, data.operator, data.limit)
            .then(data.on_success);
    },
};

});
