odoo.define('web.BasicController', function (require) {
"use strict";

/**
 * The BasicController is mostly here to share code between views that will use
 * a BasicModel (or a subclass).  Currently, the BasicViews are the form, list
 * and kanban views.
 */

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var Dialog = require('web.Dialog');
var FieldManagerMixin = require('web.FieldManagerMixin');
var Pager = require('web.Pager');

var _t = core._t;

var BasicController = AbstractController.extend(FieldManagerMixin, {
    custom_events: _.extend({}, AbstractController.prototype.custom_events, FieldManagerMixin.custom_events, {
        discard_changes: '_onDiscardChanges',
        reload: '_onReload',
        set_dirty: '_onSetDirty',
        sidebar_data_asked: '_onSidebarDataAsked',
        translate: '_onTranslate',
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
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        // add classname to reflect the (absence of) access rights (used to
        // correctly display the nocontent helper)
        this.$el.toggleClass('o_cannot_create', !this.activeActions.create);
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

        var message = _t("The record has been modified, your changes will be discarded. Do you want to proceed?");
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
     * Waits for the mutex to be unlocked and then calls _.discardChanges.
     * This ensures that the confirm dialog isn't displayed directly if there is
     * a pending 'write' rpc.
     *
     * @see _.discardChanges
     */
    discardChanges: function (recordID, options) {
        return this.mutex.exec(function () {})
            .then(this._discardChanges.bind(this, recordID || this.handle, options));
    },
    /**
     * Method that will be overriden by the views with the ability to have selected ids
     *
     * @returns {Array}
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
     *        Resolved with the list of field names (whose value has been modified)
     *        Rejected if the record can't be saved
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
        var self = this;
        return this.mutex
            .exec(this.renderer.commitChanges.bind(this.renderer, recordID || this.handle))
            .then(function () {
                return self.mutex.exec(self._saveRecord.bind(self, recordID, options));
            });
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
            this.trigger_up('history_back');
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
            return self.isDestroyed() ? $.when() : self.reload();
        };
        record = record || this.model.get(this.handle);

        this.trigger_up('execute_action', {
            action_data: _.extend({}, attrs, {
                context: record.getContext({additionalContext: attrs.context || {}}),
            }),
            env: {
                context: record.getContext(),
                currentID: record.data.id,
                model: record.model,
                resIDs: record.res_ids,
            },
            on_success: def.resolve.bind(def),
            on_fail: function () {
                reload().always(def.reject.bind(def));
            },
            on_closed: reload,
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
                .deleteRecords(ids, self.modelName)
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
     * Disables buttons so that they can't be clicked anymore.
     *
     * @private
     */
    _disableButtons: function () {
        if (this.$buttons) {
            this.$buttons.find('button').attr('disabled', true);
        }
    },
    /**
     * Discards the changes made to the record whose ID is given, if necessary.
     * Automatically leaves to default mode for the given record.
     *
     * @private
     * @param {string} [recordID] - default to main recordID
     * @param {Object} [options]
     * @param {boolean} [options.readonlyIfRealDiscard=false]
     *        After discarding record changes, the usual option is to make the
     *        record readonly. However, the action manager calls this function
     *        at inappropriate times in the current code and in that case, we
     *        don't want to go back to readonly if there is nothing to discard
     *        (e.g. when switching record in edit mode in form view, we expect
     *        the new record to be in edit mode too, but the view manager calls
     *        this function as the URL changes...) @todo get rid of this when
     *        the webclient/action_manager's hashchange mechanism is improved.
     * @returns {Deferred}
     */
    _discardChanges: function (recordID, options) {
        var self = this;
        recordID = recordID || this.handle;
        return this.canBeDiscarded(recordID)
            .then(function (needDiscard) {
                if (options && options.readonlyIfRealDiscard && !needDiscard) {
                    return;
                }
                self.model.discardChanges(recordID);
                if (self.model.isNew(recordID)) {
                    self._abandonRecord(recordID);
                    return;
                }
                return self._confirmSave(recordID);
            });
    },
    /**
     * Enables buttons so they can be clicked again.
     *
     * @private
     */
    _enableButtons: function () {
        if (this.$buttons) {
            this.$buttons.find('button').removeAttr('disabled');
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
     *        Resolved with the list of field names (whose value has been modified)
     *        Rejected if the record can't be saved
     */
    _saveRecord: function (recordID, options) {
        recordID = recordID || this.handle;
        options = _.defaults(options || {}, {
            stayInEdit: false,
            reload: true,
            savePoint: false,
        });

        // Check if the view is in a valid state for saving
        // Note: it is the model's job to do nothing if there is nothing to save
        if (this.canBeSaved(recordID)) {
            var self = this;
            var saveDef = this.model.save(recordID, { // Save then leave edit mode
                reload: options.reload,
                savePoint: options.savePoint,
                viewType: options.viewType,
            });
            if (!options.stayInEdit) {
                saveDef = saveDef.then(function (fieldNames) {
                    var def = fieldNames.length ? self._confirmSave(recordID) : self._setMode('readonly', recordID);
                    return def.then(function () {
                        return fieldNames;
                    });
                });
            }
            return saveDef;
        } else {
            return $.Deferred().reject(); // Cannot be saved
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
     * @returns {Deferred}
     */
    _setMode: function (mode, recordID) {
        if ((recordID || this.handle) === this.handle) {
            return this.update({mode: mode}, {reload: false}).then(function () {
                // necessary to allow all sub widgets to use their dimensions in
                // layout related activities, such as autoresize on fieldtexts
                core.bus.trigger('DOM_updated');
            });
        }
        return $.when();
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
        this.trigger_up('env_updated', {controllerID: this.controllerID, env: env});
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
     * Called when a list element asks to discard the changes made to one of
     * its rows.  It can happen with a x2many (if we are in a form view) or with
     * a list view.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardChanges: function (ev) {
        var self = this;
        ev.stopPropagation();
        var recordID = ev.data.recordID;
        this._discardChanges(recordID)
            .done(function () {
                // TODO this will tell the renderer to rerender the widget that
                // asked for the discard but will unfortunately lose the click
                // made on another row if any
                self._confirmChange(self.handle, [ev.data.fieldName], ev)
                    .always(ev.data.onSuccess);
            })
            .fail(ev.data.onFailure);
    },
    /**
     * Forces to save directly the changes if the controller is in readonly,
     * because in that case the changes come from widgets that are editable even
     * in readonly (e.g. Priority).
     *
     * @private
     * @param {OdooEvent} ev
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
        event.stopPropagation(); // prevent other controllers from handling this request
        var data = event && event.data || {};
        var handle = data.db_id;
        if (handle) {
            // reload the relational field given its db_id
            this.model.reload(handle).then(this._confirmSave.bind(this, handle));
        } else {
            // no db_id given, so reload the main record
            this.reload({
                fieldNames: data.fieldNames,
                keepChanges: data.keepChanges || false,
            });
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSetDirty: function (ev) {
        ev.stopPropagation(); // prevent other controllers from handling this request
        this.model.setDirty(ev.data.dataPointID);
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
    /**
     * open the translation view for the current field
     *
     * @private
     * @param {OdooEvent} event
     */
    _onTranslate: function (event) {
        event.stopPropagation();
        var self = this;
        var record = this.model.get(event.data.id, {raw: true});
        this._rpc({
            route: '/web/dataset/call_button',
            params: {
                model: 'ir.translation',
                method: 'translate_fields',
                args: [record.model, record.res_id, event.data.fieldName, record.getContext()],
            }
        }).then(function (result) {
            self.do_action(result, {
                on_reverse_breadcrumb: function () {
                    if (self.renderer.alertFields.length) {
                        self.renderer.displayTranslationAlert();
                    }
                    return false
                },
            })
        });
    },
});

return BasicController;
});
