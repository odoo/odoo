odoo.define('web.BasicController', function (require) {
"use strict";

/**
 * The BasicController is mostly here to share code between views that will use
 * a BasicModel (or a subclass).  Currently, the BasicViews are the form, list
 * and kanban views.
 */

var AbstractController = require('web.AbstractController');
var FieldManagerMixin = require('web.FieldManagerMixin');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Pager = require('web.Pager');

var _t = core._t;

return AbstractController.extend(FieldManagerMixin, {
    custom_events: _.extend({}, AbstractController.prototype.custom_events, FieldManagerMixin.custom_events, {
        reload: '_onReload',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {boolean} params.archiveEnabled
     * @param {boolean} params.confirmOnDelete
     * @param {boolean} params.hasButtons
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.archiveEnabled = params.archiveEnabled;
        this.confirmOnDelete = params.confirmOnDelete;
        this.hasButtons = params.hasButtons;
        FieldManagerMixin.init.call(this, this.model);
        this.handle = params.initialState.id;
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        return this._super.apply(this, arguments)
                          .then(this._updateEnv.bind(this));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    renderPager: function ($node, options) {
        var data = this.model.get(this.handle, {raw: true});
        this.pager = new Pager(this, data.count, data.offset + 1, data.limit, options);

        this.pager.on('pager_changed', this, function (newState) {
            var self = this;
            this.pager.disable();
            var limitChanged = (data.limit !== newState.limit);
            this.reload({limit: newState.limit, offset: newState.current_min - 1})
                .then(function () {
                    // Reset the scroll position to the top on page changed only
                    if (!limitChanged) {
                        self.trigger_up('scrollTo', {offset: 0});
                    }
                })
                .then(this.pager.enable.bind(this.pager));
        });
        this.pager.appendTo($node);
        this._updatePager();  // to force proper visibility
    },
    /**
     * @override
     * @returns {Deferred}
     */
    update: function (params, options) {
        var self = this;
        return this._super(params, options).then(function () {
            self._updateEnv();
            self._updatePager();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Delete records (and ask for confirmation if necessary)
     *
     * @param {string[]} ids list of local record ids
     */
    _deleteRecords: function (ids) {
        var self = this;
        function doIt() {
            return self.model
                .deleteRecords(ids, self.modelName, self.handle)
                .then(self._onDeletedRecords.bind(self, ids));
        }
        if (this.confirmOnDelete) {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                confirm_callback: doIt,
            });
        } else {
            doIt();
        }
    },
    /**
     * Hook method, called when record(s) has been deleted.
     *
     * @see _deleteRecord
     * @param {string[]} ids list of deleted ids (basic model local handles)
     */
    _onDeletedRecords: function (ids) {
        this.update({});
    },
    /**
     * Helper method, to get the current environment variables from the model
     * and notifies the component chain (by bubbling an event up)
     */
    _updateEnv: function () {
        var env = this.model.get(this.handle, {env: true});
        this.trigger_up('env_updated', env);
    },
    /**
     * Helper method, to make sure the information displayed by the pager is up
     * to date.
     */
    _updatePager: function () {
        if (this.pager) {
            var data = this.model.get(this.handle, {raw: true});
            this.pager.updateState({
                current_min: data.offset + 1,
                size: data.count,
            });
            var isRecord = data.type === 'record';
            var hasData = !!data.count;
            var isGrouped = data.groupedBy ? !!data.groupedBy.length : false;
            var isNew = this.model.isNew(this.handle);
            var isPagerVisible = isRecord ? !isNew : (hasData && !isGrouped);

            this.pager.do_toggle(isPagerVisible);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When a reload event triggers up, we need to reload the full view.
     * For example, after a form view dialog saved some data.
     *
     * @todo: rename db_id into handle
     *
     * @param {OdooEvent} event
     * @param {Object} event.data
     * @param {string} [event.data.db_id] handle of the data to reload and
     *   re-render (reload the whole form by default)
     * @param {string[]} [event.data.fieldNames] list of the record's fields to
     *   reload
     */
    _onReload: function (event) {
        var data = event && event.data || {};
        var handle = data.db_id;
        if (handle) {
            // reload the relational field given its db_id
            this.model.reload(handle).then(this._confirmSave.bind(this, handle));
        } else {
            // no db_id given, so reload the main record
            this.reload({fieldNames: data.fieldNames});
        }
    },

});

});
