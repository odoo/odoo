odoo.define('web.BasicController', function (require) {
"use strict";

/**
 * The BasicController is mostly here to share code between views that will use
 * a BasicModel (or a subclass).  Currently, the BasicViews are the form, list
 * and kanban views.
 */

var AbstractController = require('web.AbstractController');
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var FieldManagerMixin = require('web.FieldManagerMixin');
var Pager = require('web.Pager');

var _t = core._t;

var BasicController = AbstractController.extend(FieldManagerMixin, {
    custom_events: _.extend({}, AbstractController.prototype.custom_events, FieldManagerMixin.custom_events, {
        reload: '_onReload',
        sidebar_data_asked: '_onSidebarDataAsked'
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
        this.mode = params.mode || 'readonly';
        this.mutex = new concurrency.Mutex();
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
     * Determines if we can discard the current changes. If the model is not
     * dirty, that is not a problem. However, if it is dirty, we have to ask
     * the user for confirmation.
     *
     * @override
     * @param {string} [recordID] - default to main recordID
     * @returns {Deferred<boolean>}
     *          resolved if can be discarded, a boolean value is given to tells
     *          if there is something to discard or not
     *          rejected otherwise
     */
    canBeDiscarded: function (recordID) {
        if (!this.model.isDirty(recordID || this.handle)) {
            return $.when(false);
        }

        var message = _t("The record has been modified, your changes will be discarded. Are you sure you want to ?");
        var def = $.Deferred();
        var dialog = Dialog.confirm(this, message, {
            title: _t("Warning"),
            confirm_callback: def.resolve.bind(def, true),
            cancel_callback: def.reject.bind(def),
        });
        dialog.on('closed', def, def.reject);
        return def;
    },
    /**
     * Ask the renderer if all associated field widget are in a valid state for
     * saving (valid value and non-empty value for required fields). If this is
     * not the case, this notifies the user with a warning containing the names
     * of the invalid fields.
     *
     * Note: changing the style of invalid fields is the renderer's job.
     *
     * @param {string} [recordID] - default to main recordID
     * @return {boolean}
     */
    canBeSaved: function (recordID) {
        var fieldNames = this.renderer.canBeSaved(recordID || this.handle);
        if (fieldNames.length) {
            this._notifyInvalidFields(fieldNames);
            return false;
        }
        return true;
    },
    /**
     * Discards the changes made to the record whose ID is given, if necessary.
     * Automatically leaves to default mode for the given record.
     *
     * @param {string} [recordID] - default to main recordID
     * @param {Object} [options]
     * @param {boolean} [options.readonlyIfRealDiscard=false]
     *        After discarding record changes, the usual option is to make the
     *        record readonly. However, the view manager calls this function
     *        at inappropriate times in the current code and in that case, we
     *        don't want to go back to readonly if there is nothing to discard
     *        (e.g. when switching record in edit mode in form view, we expect
     *        the new record to be in edit mode too, but the view manager calls
     *        this function as the URL changes...) @todo get rid of this when
     *        the view manager is improved.
     * @returns {Deferred}
     */
    discardChanges: function (recordID, options) {
        var self = this;
        recordID = recordID || this.handle;
        return this.canBeDiscarded(recordID).then(function (needDiscard) {
            if (needDiscard) { // Just some optimization
                self.model.discardChanges(recordID);
            }
            if (options && options.readonlyIfRealDiscard && !needDiscard) {
                return;
            }
            self._setMode('readonly', recordID);
        });
    },
    /**
     * Method that will be overriden by the views with the ability to have selected ids
     *
     * @returns []
     */
    getSelectedIds: function () {
        return [];
    },
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
     * Saves the record whose ID is given if necessary (@see _saveRecord).
     *
     * @param {string} [recordID] - default to main recordID
     * @param {Object} [options]
     * @returns {Deferred}
     */
    saveRecord: function (recordID, options) {
        // Some field widgets can't detect (all) their changes immediately or
        // may have to validate them before notifying them, so we ask them to
        // commit their current value before saving. This has to be done outside
        // of the mutex protection of saving because commitChanges will trigger
        // changes and these are also protected. So the actual saving has to be
        // done after these changes. Also the commitChanges operation might not
        // be synchronous for other reason (e.g. the x2m fields will ask the
        // user if some discarding has to be made). This operation must also be
        // mutex-protected as commitChanges function of x2m has to be aware of
        // all final changes made to a row.
        this.mutex.exec(this.renderer.commitChanges.bind(this.renderer, recordID || this.handle)); // TODO write a test for this
        return this.mutex.exec(this._saveRecord.bind(this, recordID, options));
    },
    /**
     * @override
     * @returns {Deferred}
     */
    update: function (params, options) {
        var self = this;
        this.mode = params.mode || this.mode;
        return this._super(params, options).then(function () {
            self._updateEnv();
            self._updatePager();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Does the necessary action when trying to "abandon" a given record (e.g.
     * when trying to make a new record readonly without having saved it). By
     * default, if the abandoned record is the main view one, the only possible
     * action is to leave the current view. Otherwise, it is a x2m line, ask the
     * model to remove it.
     *
     * @private
     * @param {string} [recordID] - default to main recordID
     */
    _abandonRecord: function (recordID) {
        recordID = recordID || this.handle;
        if (recordID === this.handle) {
            this.trigger_up('switch_to_previous_view');
        } else {
            this.model.removeLine(recordID);
        }
    },
    /**
     * We override applyChanges (from the field manager mixin) to protect it
     * with a mutex.
     *
     * @override
     */
    _applyChanges: function (dataPointID, changes, event) {
        var _super = FieldManagerMixin._applyChanges.bind(this);
        return this.mutex.exec(function () {
            return _super(dataPointID, changes, event);
        });
    },
    /**
     * When the user clicks on a 'action button', this function determines what
     * should happen.
     *
     * @private
     * @param {Object} attrs the attrs of the button clicked
     * @param {Object} [record] the current state of the view
     * @returns {Deferred}
     */
    _callButtonAction: function (attrs, record) {
        var self = this;
        var def = $.Deferred();
        var reload = function () {
            if (!self.isDestroyed()) {
                self.reload();
            }
        };
        record = record || this.model.get(this.handle);
        var recordID = record.data.id;
        this.trigger_up('execute_action', {
            action_data: _.extend({}, attrs, {
                context: record.getContext({additionalContext: attrs.context}),
            }),
            model: record.model,
            record_id: recordID,
            on_closed: function (reason) {
                if (!_.isObject(reason)) {
                    reload();
                }
            },
            on_fail: reload,
            on_success: def.resolve.bind(def),
        });
        return this.alive(def);
    },
    /**
     * Called by the field manager mixin to confirm that a change just occured
     * (after that potential onchanges have been applied).
     *
     * Basically, this only relays the notification to the renderer with the
     * new state.
     *
     * @param {string} id - the id of one of the view's records
     * @param {string[]} fields - the changed fields
     * @param {OdooEvent} e - the event that triggered the change
     * @returns {Deferred}
     */
    _confirmChange: function (id, fields, e) {
        var state = this.model.get(this.handle);
        return this.renderer.confirmChange(state, id, fields, e);
    },
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
     * Returns the new sidebar env
     *
     * @private
     * @return {Object} the new sidebar env
     */
    _getSidebarEnv: function () {
        return {
            context: this.model.get(this.handle).getContext(),
            activeIds: this.getSelectedIds(),
            model: this.modelName,
        };
    },
    /**
     * Used by list and kanban views to determine whether or not to display
     * the no content helper (if there is no data in the state to display)
     *
     * @private
     * @param {Object} state
     * @returns {boolean}
     */
    _hasContent: function (state) {
        return state.count !== 0;
    },
    /**
     * Helper function to display a warning that some fields have an invalid
     * value. This is used when a save operation cannot be completed.
     *
     * @private
     * @param {string[]} invalidFields - list of field names
     */
    _notifyInvalidFields: function (invalidFields) {
        var record = this.model.get(this.handle, {raw: true});
        var fields = record.fields;
        var warnings = invalidFields.map(function (fieldName) {
            var fieldStr = fields[fieldName].string;
            return _.str.sprintf('<li>%s</li>', _.escape(fieldStr));
        });
        warnings.unshift('<ul>');
        warnings.push('</ul>');
        this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
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
     * Saves the record whose ID is given, if necessary. Automatically leaves
     * edit mode for the given record, unless told otherwise.
     *
     * @param {string} [recordID] - default to main recordID
     * @param {Object} [options]
     * @param {boolean} [options.stayInEdit=false]
     *        if true, leave the record in edit mode after save
     * @param {boolean} [options.reload=true]
     *        if true, reload the record after (real) save
     * @param {boolean} [options.savePoint=false]
     *        if true, the record will only be 'locally' saved: its changes
     *        will move from the _changes key to the data key
     * @returns {Deferred}
     */
    _saveRecord: function (recordID, options) {
        recordID = recordID || this.handle;
        options = _.defaults(options || {}, {
            stayInEdit: false,
            reload: true,
            savePoint: false,
        });

        var def = $.Deferred();
        // Check if the view is in a valid state for saving
        // Note: it is the model's job to do nothing if there is nothing to save
        if (this.canBeSaved(recordID)) {
            def = this.model.save(recordID, { // Save then leave edit mode
                reload: options.reload,
                savePoint: options.savePoint,
            });
        } else {
            def.reject(); // Cannot be saved, do nothing at all
        }

        if (options.stayInEdit) {
            return def;
        } else {
            return def.then(this._setMode.bind(this, 'readonly', recordID));
        }
    },
    /**
     * Change the mode for the record associated to the given ID.
     * If the given recordID is the view's main one, then the whole view mode is
     * changed (@see BasicController.update).
     *
     * @private
     * @param {string} mode - 'readonly' or 'edit'
     * @param {string} [recordID]
     */
    _setMode: function (mode, recordID) {
        recordID = recordID || this.handle;
        // If trying to make a temporary record readonly, discard the record
        if (mode === 'readonly' && this.model.isNew(recordID)) {
            this._abandonRecord(recordID);
            return;
        }
        if (recordID === this.handle) {
            this.update({mode: mode}, {reload: false});
        }
    },
    /**
     * Helper method, to get the current environment variables from the model
     * and notifies the component chain (by bubbling an event up)
     *
     * @private
     */
    _updateEnv: function () {
        var env = this.model.get(this.handle, {env: true});
        if (this.sidebar) {
            var sidebarEnv = this._getSidebarEnv();
            this.sidebar.updateEnv(sidebarEnv);
        }
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
     * Forces to save directly the changes if the controller is in readonly,
     * because in that case the changes come from widgets that are editable even
     * in readonly (e.g. Priority).
     *
     * @private
     * @param {OdooEvent}
     */
    _onFieldChanged: function (ev) {
        if (this.mode === 'readonly') {
            ev.data.force_save = true;
        }
        FieldManagerMixin._onFieldChanged.apply(this, arguments);
    },
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
    /**
     * Handler used to get all the data necessary when a custom action is
     * performed through the sidebar.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onSidebarDataAsked: function (event) {
        var sidebarEnv = this._getSidebarEnv();
        event.data.callback(sidebarEnv);
    },
});

return BasicController;
});
