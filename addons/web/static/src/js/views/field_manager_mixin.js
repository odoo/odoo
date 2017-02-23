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

var FieldManagerMixin = {
    custom_events: {
        field_changed: '_onFieldChanged',
        load: '_onLoad',
        call_service: '_onCallService',
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
     * Some widgets perform model RPCs. These are intercepted so that the
     * context can be automatically added according to the given dataPointID
     * option the AbstractField implementation automatically adds.
     *
     * @param {OdooEvent} e
     * @param {string} e.data.service - the service called, here we are only
     *                                interested in the "ajax" service
     * @param {string} e.data.method - the service method called, here we are
     *                               only interested by the "rpc" method
     * @param {Array} e.data.args
     *        the args parameters contains the route, the route arguments and
     *        the RPC call options. This method purpose is to check the RPC
     *        call options for the dataPointID (and field name) and merge the
     *        appropriate context with the route arguments' one.
     */
    _onCallService: function (e) {
        if (e.data.service !== "ajax" || e.data.method !== "rpc") return;

        var args = e.data.args[1];
        var options = e.data.args[2];
        if (args.kwargs && options.dataPointID) {
            args.kwargs.context = _.extend(
                this.model.getContext(options.dataPointID, {
                    fieldName: options.fieldName || false,
                }),
                args.kwargs.context || {}
            );
        }
    },
};

return FieldManagerMixin;
});
