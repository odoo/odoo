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
var TranslationDialog = require('web.TranslationDialog');

var _t = core._t;

var BasicController = AbstractController.extend(FieldManagerMixin, {
    events: Object.assign({}, AbstractController.prototype.events, {
        'click .o_content': '_onContentClicked',
    }),
    custom_events: _.extend({}, AbstractController.prototype.custom_events, FieldManagerMixin.custom_events, {
        discard_changes: '_onDiscardChanges',
        pager_changed: '_onPagerChanged',
        reload: '_onReload',
        resequence_records: '_onResequenceRecords',
        set_dirty: '_onSetDirty',
        load_optional_fields: '_onLoadOptionalFields',
        save_optional_fields: '_onSaveOptionalFields',
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
        this.mode = params.mode || 'readonly';
        // savingDef is used to ensure that we always wait for pending save
        // operations to complete before checking if there are changes to
        // discard when discardChanges is called
        this.savingDef = Promise.resolve();
        // discardingDef is used to ensure that we don't ask twice the user if
        // he wants to discard changes, when 'canBeDiscarded' is called several
        // times "in parallel"
        this.discardingDef = null;
        this.viewId = params.viewId;
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: async function () {
        // add classname to reflect the (absence of) access rights (used to
        // correctly display the nocontent helper)
        this.$el.toggleClass('o_cannot_create', !this.activeActions.create);
        await this._super(...arguments);
    },
    /**
     * Called each time the controller is dettached into the DOM
     */
    on_detach_callback() {
        this._super.apply(this, arguments);
        this.renderer.resetLocalState();
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
     * @returns {Promise<boolean>}
     *          resolved if can be discarded, a boolean value is given to tells
     *          if there is something to discard or not
     *          rejected otherwise
     */
    canBeDiscarded: function (recordID) {
        var self = this;
        if (this.discardingDef) {
            // discard dialog is already open
            return this.discardingDef;
        }
        if (!this.isDirty(recordID)) {
            return Promise.resolve(false);
        }

        var message = _t("The record has been modified, your changes will be discarded. Do you want to proceed?");
        this.discardingDef = new Promise(function (resolve, reject) {
            var dialog = Dialog.confirm(self, message, {
                title: _t("Warning"),
                confirm_callback: () => {
                    resolve(true);
                    self.discardingDef = null;
                },
                cancel_callback: () => {
                    reject();
                    self.discardingDef = null;
                },
            });
            dialog.on('closed', self.discardingDef, reject);
        });
        return this.discardingDef;
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
     * Waits for the mutex to be unlocked and for changes to be saved, then
     * calls _.discardChanges.
     * This ensures that the confirm dialog isn't displayed directly if there is
     * a pending 'write' rpc.
     *
     * @see _.discardChanges
     */
    discardChanges: function (recordID, options) {
        return Promise.all([this.mutex.getUnlockedDef(), this.savingDef])
            .then(this._discardChanges.bind(this, recordID || this.handle, options));
    },
    /**
     * Method that will be overridden by the views with the ability to have selected ids
     *
     * @returns {Array}
     */
    getSelectedIds: function () {
        return [];
    },
    /**
     * Returns true iff the given recordID (or the main recordID) is dirty.
     *
     * @param {string} [recordID] - default to main recordID
     * @returns {boolean}
     */
    isDirty: function (recordID) {
        return this.model.isDirty(recordID || this.handle);
    },
    /**
     * Saves the record whose ID is given if necessary (@see _saveRecord).
     *
     * @param {string} [recordID] - default to main recordID
     * @param {Object} [options]
     * @returns {Promise}
     *        Resolved with the list of field names (whose value has been modified)
     *        Rejected if the record can't be saved
     */
    saveRecord: function (recordID, options) {
        var self = this;
        // Some field widgets can't detect (all) their changes immediately or
        // may have to validate them before notifying them, so we ask them to
        // commit their current value before saving. This has to be done outside
        // of the mutex protection of saving because commitChanges will trigger
        // changes and these are also protected. However, we must wait for the
        // mutex to be idle to ensure that onchange RPCs returned before asking
        // field widgets to commit their value (and validate it, for instance
        // for one2many with required fields). So the actual saving has to be
        // done after these changes. Also the commitChanges operation might not
        // be synchronous for other reason (e.g. the x2m fields will ask the
        // user if some discarding has to be made). This operation must also be
        // mutex-protected as commitChanges function of x2m has to be aware of
        // all final changes made to a row.
        var unlockedMutex = this.mutex.getUnlockedDef()
            .then(function () {
                return self.renderer.commitChanges(recordID || self.handle);
            })
            .then(function () {
                return self.mutex.exec(self._saveRecord.bind(self, recordID, options));
            });
        this.savingDef = new Promise(function (resolve) {
            unlockedMutex.then(resolve).guardedCatch(resolve);
        });

        return unlockedMutex;
    },
    /**
     * @override
     * @returns {Promise}
     */
    update: async function (params, options) {
        this.mode = params.mode || this.mode;
        return this._super(params, options);
    },
    /**
     * @override
     */
    reload: function (params) {
        if (params && params.controllerState) {
            if (params.controllerState.currentId) {
                params.currentId = params.controllerState.currentId;
            }
            params.ids = params.controllerState.resIds;
        }
        return this._super.apply(this, arguments);
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
     * Archive the current selection
     *
     * @private
     * @param {number[]} ids
     * @param {boolean} archive
     * @returns {Promise}
     */
    _archive: async function (ids, archive) {
        if (ids.length === 0) {
            return Promise.resolve();
        }
        if (archive) {
            await this.model.actionArchive(ids, this.handle);
        } else {
            await this.model.actionUnarchive(ids, this.handle);
        }
        return this.update({}, {reload: false});
    },
    /**
     * When the user clicks on a 'action button', this function determines what
     * should happen.
     *
     * @private
     * @param {Object} attrs the attrs of the button clicked
     * @param {Object} [record] the current state of the view
     * @returns {Promise}
     */
    _callButtonAction: function (attrs, record) {
        record = record || this.model.get(this.handle);
        const actionData = Object.assign({}, attrs, {
            context: record.getContext({additionalContext: attrs.context || {}})
        });
        const recordData = {
            context: record.getContext(),
            currentID: record.data.id,
            model: record.model,
            resIDs: record.res_ids,
        };
        return this._executeButtonAction(actionData, recordData);
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
     * @returns {Promise}
     */
    _confirmChange: function (id, fields, e) {
        if (e.name === 'discard_changes' && e.target.reset) {
            // the target of the discard event is a field widget.  In that
            // case, we simply want to reset the specific field widget,
            // not the full view
            return  e.target.reset(this.model.get(e.target.dataPointID), e, true);
        }

        var state = this.model.get(this.handle);
        return this.renderer.confirmChange(state, id, fields, e);
    },
    /**
     * Ask the user to confirm he wants to save the record
     * @private
     */
    _confirmSaveNewRecord: function () {
        var self = this;
        var def = new Promise(function (resolve, reject) {
            var message = _t("You need to save this new record before editing the translation. Do you want to proceed?");
            var dialog = Dialog.confirm(self, message, {
                title: _t("Warning"),
                confirm_callback: resolve.bind(self, true),
                cancel_callback: reject,
            });
            dialog.on('closed', self, reject);
        });
        return def;
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
            const message = ids.length > 1 ?
                            _t("Are you sure you want to delete these records?") :
                            _t("Are you sure you want to delete this record?");
            Dialog.confirm(this, message, { confirm_callback: doIt });
        } else {
            doIt();
        }
    },
    /**
     * Disables buttons so that they can't be clicked anymore.
     *
     * @private
     */
    _disableButtons: function () {
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
     * @param {boolean} [options.noAbandon=false]
     * @returns {Promise}
     */
    _discardChanges: function (recordID, options) {
        var self = this;
        recordID = recordID || this.handle;
        options = options || {};
        return this.canBeDiscarded(recordID)
            .then(function (needDiscard) {
                if (options.readonlyIfRealDiscard && !needDiscard) {
                    return;
                }
                self.model.discardChanges(recordID);
                if (options.noAbandon) {
                    return;
                }
                if (self.model.canBeAbandoned(recordID)) {
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
    _enableButtons: function () {
        if (this.$buttons) {
            this.$buttons.find('button').removeAttr('disabled');
        }
    },
    /**
     * Executes the action associated with a button
     *
     * @private
     * @param {Object} actionData: the descriptor of the action
     * @param {string} actionData.type: the button's action's type, accepts "object" or "action"
     * @param {string} actionData.name: the button's action's name
     *    either the model method's name for type "object"
     *    or the action's id in database, or xml_id
     * @param {string} actionData.context: the action's execution context
     *
     * @param {Object} recordData: basic information on the current record(s)
     * @param {number[]} recordData.resIDs: record ids:
     *     - on which an object method applies
     *     - that will be used as active_ids to load an action
     * @param {string} recordData.model: model name
     * @param {Object} recordData.context: the records' context, will be used to load
     *     the action, and merged into actionData.context at execution time
     *
     * @returns {Promise}
     */
    async _executeButtonAction(actionData, recordData) {
        const prom = new Promise((resolve, reject) => {
            this.trigger_up('execute_action', {
                action_data: actionData,
                env: recordData,
                on_closed: () => this.isDestroyed() ? Promise.resolve() : this.reload(),
                on_success: resolve,
                on_fail: () => this.update({}, { reload: false }).then(reject).guardedCatch(reject)
            });
        });
        return this.alive(prom);
    },
    /**
     * Override to add the current record ID (currentId) and the list of ids
     * (resIds) in the current dataPoint to the exported state.
     *
     * @override
     */
    exportState: function () {
        var state = this._super.apply(this, arguments);
        var env = this.model.get(this.handle, {env: true});
        return _.extend(state, {
            currentId: env.currentId,
            resIds: env.ids,
        });
    },
    /**
     * Compute the optional fields local storage key using the given parts.
     *
     * @param {Object} keyParts
     * @param {string} keyParts.viewType view type
     * @param {string} [keyParts.relationalField] name of the field with subview
     * @param {integer} [keyParts.subViewId] subview id
     * @param {string} [keyParts.subViewType] type of the subview
     * @param {Object} keyParts.fields fields
     * @param {string} keyParts.fields.name field name
     * @param {string} keyParts.fields.type field type
     * @returns {string} local storage key for optional fields in this view
     * @private
     */
    _getOptionalFieldsLocalStorageKey: function (keyParts) {
        keyParts.model = this.modelName;
        keyParts.viewType = this.viewType;
        keyParts.viewId = this.viewId;

        var parts = [
            'model',
            'viewType',
            'viewId',
            'relationalField',
            'subViewType',
            'subViewId',
        ];

        var viewIdentifier = parts.reduce(function (identifier, partName) {
            if (partName in keyParts) {
                return identifier + ',' + keyParts[partName];
            }
            return identifier;
        }, 'optional_fields');

        viewIdentifier =
            keyParts.fields.sort(this._nameSortComparer)
                           .reduce(function (identifier, field) {
                                return identifier + ',' + field.name;
                            }, viewIdentifier);

        return viewIdentifier;
    },
    /**
     * Return the params (currentMinimum, limit and size) to pass to the pager,
     * according to the current state.
     *
     * @private
     * @returns {Object}
     */
    _getPagingInfo: function (state) {
        const isGrouped = state.groupedBy && state.groupedBy.length;
        return {
            currentMinimum: (isGrouped ? state.groupsOffset : state.offset) + 1,
            limit: isGrouped ? state.groupsLimit : state.limit,
            size: isGrouped ? state.groupsCount : state.count,
        };
    },
    /**
     * Return the new actionMenus props.
     *
     * @override
     * @private
     */
    _getActionMenuItems: function (state) {
        return {
            activeIds: this.getSelectedIds(),
            context: state.getContext(),
        };
    },
    /**
     *  Sort function used to sort the fields by names, to compute the optional fields keys
     *
     *  @param {Object} left
     *  @param {Object} right
     *  @private
      */
    _nameSortComparer: function(left, right) {
        return left.name < right.name ? -1 : 1;
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
        this.do_warn(_t("Invalid fields:"), warnings.join(''));
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
     * @returns {Promise}
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
            return Promise.reject("SaveRecord: this.canBeSave is false"); // Cannot be saved
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
     * @returns {Promise}
     */
    _setMode: function (mode, recordID) {
        if ((recordID || this.handle) === this.handle) {
            return this.update({mode: mode}, {reload: false}).then(function () {
                // necessary to allow all sub widgets to use their dimensions in
                // layout related activities, such as autoresize on fieldtexts
                core.bus.trigger('DOM_updated');
            });
        }
        return Promise.resolve();
    },
    /**
     * To override such that it returns true iff the primary action button must
     * bounce when the user clicked on the given element, according to the
     * current state of the view.
     *
     * @private
     * @param {HTMLElement} element the node the user clicked on
     * @returns {boolean}
     */
    _shouldBounceOnClick: function (/* element */) {
        return false;
    },
    /**
     * Helper method, to get the current environment variables from the model
     * and notifies the component chain (by bubbling an event up)
     *
     * @private
     * @param {Object} [newProps={}]
     */
    _updateControlPanel: function (newProps = {}) {
        const state = this.model.get(this.handle);
        const props = Object.assign(newProps, {
            actionMenus: this._getActionMenuItems(state),
            pager: this._getPagingInfo(state),
            title: this.getTitle(),
        });
        return this.updateControlPanel(props);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the user clicks on the 'content' part of the controller
     * (typically the renderer area). Makes the first primary button in the
     * control panel bounce, in some situations (see _shouldBounceOnClick).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onContentClicked(ev) {
        if (this.$buttons && this._shouldBounceOnClick(ev.target)) {
            this.$buttons.find('.btn-primary:visible:first').odooBounce();
        }
    },
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
            .then(function () {
                // TODO this will tell the renderer to rerender the widget that
                // asked for the discard but will unfortunately lose the click
                // made on another row if any
                self._confirmChange(recordID, [ev.data.fieldName], ev)
                    .then(ev.data.onSuccess).guardedCatch(ev.data.onSuccess);
            })
            .guardedCatch(ev.data.onFailure);
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
        if (this.mode === 'readonly' && !('force_save' in ev.data)) {
            ev.data.force_save = true;
        }
        FieldManagerMixin._onFieldChanged.apply(this, arguments);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onPagerChanged: async function (ev) {
        ev.stopPropagation();
        const { currentMinimum, limit } = ev.data;
        const state = this.model.get(this.handle, { raw: true });
        const reloadParams = state.groupedBy && state.groupedBy.length ? {
                groupsLimit: limit,
                groupsOffset: currentMinimum - 1,
            } : {
                limit,
                offset: currentMinimum - 1,
            };
        await this.reload(reloadParams);
        // reset the scroll position to the top on page changed only
        if (state.limit === limit) {
            this.trigger_up('scrollTo', { top: 0 });
        }
    },
    /**
     * When a reload event triggers up, we need to reload the full view.
     * For example, after a form view dialog saved some data.
     *
     * @todo: rename db_id into handle
     *
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {string} [ev.data.db_id] handle of the data to reload and
     *   re-render (reload the whole form by default)
     * @param {string[]} [ev.data.fieldNames] list of the record's fields to
     *   reload
     * @param {Function} [ev.data.onSuccess] callback executed after reload is resolved
     * @param {Function} [ev.data.onFailure] callback executed when reload is rejected
     */
    _onReload: function (ev) {
        ev.stopPropagation(); // prevent other controllers from handling this request
        var data = ev && ev.data || {};
        var handle = data.db_id;
        var prom;
        if (handle) {
            // reload the relational field given its db_id
            prom = this.model.reload(handle).then(this._confirmSave.bind(this, handle));
        } else {
            // no db_id given, so reload the main record
            prom = this.reload({
                fieldNames: data.fieldNames,
                keepChanges: data.keepChanges || false,
            });
        }
        prom.then(ev.data.onSuccess).guardedCatch(ev.data.onFailure);
    },
    /**
     * Resequence records in the given order.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string[]} ev.data.recordIds
     * @param {integer} ev.data.offset
     * @param {string} ev.data.handleField
     */
    _onResequenceRecords: function (ev) {
        ev.stopPropagation(); // prevent other controllers from handling this request
        this.trigger_up('mutexify', {
            action: async () => {
                let state = this.model.get(this.handle);
                const resIDs = ev.data.recordIds
                    .map(recordID => state.data.find(d => d.id === recordID).res_id);
                const options = {
                    offset: ev.data.offset,
                    field: ev.data.handleField,
                };
                await this.model.resequence(this.modelName, resIDs, this.handle, options);
                this._updateControlPanel();
                state = this.model.get(this.handle);
                return this._updateRendererState(state, { noRender: true });
            },
        });
    },
    /**
     * Load the optional columns settings in local storage for this view
     *
     * @param {OdooEvent} ev
     * @param {Object} ev.data.keyParts see _getLocalStorageKey
     * @param {function} ev.data.callback function to call with the result
     * @private
     */
    _onLoadOptionalFields: function (ev) {
        var res = this.call(
            'local_storage',
            'getItem',
            this._getOptionalFieldsLocalStorageKey(ev.data.keyParts)
        );
        ev.data.callback(res);
    },
    /**
     * Save the optional columns settings in local storage for this view
     *
     * @param {OdooEvent} ev
     * @param {Object} ev.data.keyParts see _getLocalStorageKey
     * @param {Array<string>} ev.data.optionalColumnsEnabled list of optional
     *   field names that have been enabled
     * @private
     */
    _onSaveOptionalFields: function (ev) {
        this.call(
            'local_storage',
            'setItem',
            this._getOptionalFieldsLocalStorageKey(ev.data.keyParts),
            ev.data.optionalColumnsEnabled
        );
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
     * open the translation view for the current field
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onTranslate: async function (ev) {
        ev.stopPropagation();

        if (this.model.isNew(ev.data.id)) {
            await this._confirmSaveNewRecord();
            var updatedFields = await this.saveRecord(ev.data.id, { stayInEdit: true });
            await this._confirmChange(ev.data.id, updatedFields, ev);
        }
        var record = this.model.get(ev.data.id, { raw: true });
        var res_id = record.res_id || record.res_ids[0];
        var result = await this._rpc({
            route: '/web/dataset/call_button',
            params: {
                model: 'ir.translation',
                method: 'translate_fields',
                args: [record.model, res_id, ev.data.fieldName],
                kwargs: { context: record.getContext() },
            }
        });

        this.translationDialog = new TranslationDialog(this, {
            domain: result.domain,
            searchName: result.context.search_default_name,
            fieldName: ev.data.fieldName,
            userLanguageValue: ev.target.value || '',
            dataPointID: record.id,
            isComingFromTranslationAlert: ev.data.isComingFromTranslationAlert,
            isText: result.context.translation_type === 'text',
            showSrc: result.context.translation_show_src,
        });
        return this.translationDialog.open();
    },
});

return BasicController;
});
