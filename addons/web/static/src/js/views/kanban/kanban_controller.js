odoo.define('web.KanbanController', function (require) {
"use strict";

/**
 * The KanbanController is the class that coordinates the kanban model and the
 * kanban renderer.  It also makes sure that update from the search view are
 * properly interpreted.
 */

var BasicController = require('web.BasicController');
var Context = require('web.Context');
var core = require('web.core');
var Domain = require('web.Domain');
var view_dialogs = require('web.view_dialogs');
var viewUtils = require('web.viewUtils');

var _t = core._t;
var qweb = core.qweb;

var KanbanController = BasicController.extend({
    buttons_template: 'KanbanView.buttons',
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        quick_create_add_column: '_onAddColumn',
        quick_create_record: '_onQuickCreateRecord',
        resequence_columns: '_onResequenceColumn',
        button_clicked: '_onButtonClicked',
        kanban_record_delete: '_onRecordDelete',
        kanban_record_update: '_onUpdateRecord',
        kanban_column_delete: '_onDeleteColumn',
        kanban_column_add_record: '_onAddRecordToColumn',
        kanban_column_resequence: '_onColumnResequence',
        kanban_load_more: '_onLoadMore',
        kanban_load_records: '_onLoadColumnRecords',
        column_toggle_fold: '_onToggleColumn',
        kanban_column_records_toggle_active: '_onToggleActiveRecords',
        search_panel_domain_updated: '_onSearchPanelDomainUpdated',
    }),
    events: _.extend({}, BasicController.prototype.events, {
        click: '_onClick',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {boolean} params.quickCreateEnabled set to false to disable the
     *   quick create feature
     * @param {SearchPanel} [params.searchPanel]
     * @param {Array[]} [params.controlPanelDomain=[]] initial domain coming
     *   from the controlPanel
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.on_create = params.on_create;
        this.hasButtons = params.hasButtons;
        this.quickCreateEnabled = params.quickCreateEnabled;

        // the following attributes are used when there is a searchPanel
        this._searchPanel = params.searchPanel;
        this.controlPanelDomain = params.controlPanelDomain || [];
        this.searchPanelDomain = this._searchPanel ? this._searchPanel.getDomain() : [];
    },
    /**
     * @override
     */
    start: function () {
        if (this._searchPanel) {
            this.$('.o_content')
                .addClass('o_kanban_with_searchpanel')
                .prepend(this._searchPanel.$el);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {jQueryElement} $node
     * @returns {Promise}
     */
    renderButtons: function ($node) {
        if (this.hasButtons && this.is_action_enabled('create')) {
            this.$buttons = $(qweb.render(this.buttons_template, {
                btnClass: 'btn-primary',
                widget: this,
            }));
            this.$buttons.on('click', 'button.o-kanban-button-new', this._onButtonNew.bind(this));
            this.$buttons.on('keydown', this._onButtonsKeyDown.bind(this));
            this._updateButtons();
            return Promise.resolve(this.$buttons.appendTo($node));
        }
        return Promise.resolve();
    },
    /**
     * Override to add the domain coming from the searchPanel (if any) to the
     * domain coming from the controlPanel.
     *
     * @override
     */
    update: function (params) {
        if (!this._searchPanel) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        if (params.domain) {
            this.controlPanelDomain = params.domain;
        }
        // do not re-render the view as soon as records have been fetched,  but
        // wait for the searchPanel to be ready as well, such that the view
        // isn't re-rendered before the searchPanel
        params.noRender = true;
        params.domain = this.controlPanelDomain.concat(this.searchPanelDomain);
        var superProm = this._super.apply(this, arguments);
        var searchPanelProm = this._updateSearchPanel();
        return Promise.all([superProm, searchPanelProm]).then(function () {
            // searchPanel has been re-rendered, so re-render the view
            return self.renderer.render();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override method comes from field manager mixin
     * @private
     * @param {string} id local id from the basic record data
     * @returns {Promise}
     */
    _confirmSave: function (id) {
        var data = this.model.get(this.handle, {raw: true});
        var grouped = data.groupedBy.length;
        if (grouped) {
            var columnState = this.model.getColumn(id);
            return this.renderer.updateColumn(columnState.id, columnState);
        }
        return this.renderer.updateRecord(this.model.get(id));
    },
    /**
     * Only display the pager in the ungrouped case, with data.
     *
     * @override
     * @private
     */
    _isPagerVisible: function () {
        var state = this.model.get(this.handle, {raw: true});
        return !!(state.count && !state.groupedBy.length);
    },
    /**
     * @private
     * @param {Widget} kanbanRecord
     * @param {Object} params
     */
    _reloadAfterButtonClick: function (kanbanRecord, params) {
        var self = this;
        var recordModel = this.model.localData[params.record.id];
        var group = this.model.localData[recordModel.parentID];
        var parent = this.model.localData[group.parentID];

        this.model.reload(params.record.id).then(function (db_id) {
            var data = self.model.get(db_id);
            kanbanRecord.update(data);

            // Check if we still need to display the record. Some fields of the domain are
            // not guaranteed to be in data. This is for example the case if the action
            // contains a domain on a field which is not in the Kanban view. Therefore,
            // we need to handle multiple cases based on 3 variables:
            // domInData: all domain fields are in the data
            // activeInDomain: 'active' is already in the domain
            // activeInData: 'active' is available in the data

            var domain = (parent ? parent.domain : group.domain) || [];
            var domInData = _.every(domain, function (d) {
                return d[0] in data.data;
            });
            var activeInDomain = _.pluck(domain, 0).indexOf('active') !== -1;
            var activeInData = 'active' in data.data;

            // Case # | domInData | activeInDomain | activeInData
            //   1    |   true    |      true      |      true     => no domain change
            //   2    |   true    |      true      |      false    => not possible
            //   3    |   true    |      false     |      true     => add active in domain
            //   4    |   true    |      false     |      false    => no domain change
            //   5    |   false   |      true      |      true     => no evaluation
            //   6    |   false   |      true      |      false    => no evaluation
            //   7    |   false   |      false     |      true     => replace domain
            //   8    |   false   |      false     |      false    => no evaluation

            // There are 3 cases which cannot be evaluated since we don't have all the
            // necessary information. The complete solution would be to perform a RPC in
            // these cases, but this is out of scope. A simpler one is to do a try / catch.

            if (domInData && !activeInDomain && activeInData) {
                domain = domain.concat([['active', '=', true]]);
            } else if (!domInData && !activeInDomain && activeInData) {
                domain = [['active', '=', true]];
            }
            try {
                var visible = new Domain(domain).compute(data.evalContext);
            } catch (e) {
                return;
            }
            if (!visible) {
                kanbanRecord.destroy();
            }
        });
    },
    /**
     * @param {number[]} ids
     * @private
     * @returns {Promise}
     */
    _resequenceColumns: function (ids) {
        var state = this.model.get(this.handle, {raw: true});
        var model = state.fields[state.groupedBy[0]].relation;
        return this.model.resequence(model, ids, this.handle);
    },
    /**
     * This method calls the server to ask for a resequence.  Note that this
     * does not rerender the user interface, because in most case, the
     * resequencing operation has already been displayed by the renderer.
     *
     * @private
     * @param {string} column_id
     * @param {string[]} ids
     * @returns {Promise}
     */
    _resequenceRecords: function (column_id, ids) {
        var self = this;
        return this.model.resequence(this.modelName, ids, column_id).then(function () {
            self._updateEnv();
        });
    },
    /**
     * Overrides to update the control panel buttons when the state is updated.
     *
     * @override
     * @private
     */
    _update: function () {
        this._updateButtons();
        return this._super.apply(this, arguments);
    },
    /**
     * In grouped mode, set 'Create' button as btn-secondary if there is no column
     * (except if we can't create new columns)
     *
     * @private
     * @override from abstract controller
     */
    _updateButtons: function () {
        if (this.$buttons) {
            var state = this.model.get(this.handle, {raw: true});
            var createHidden = this.is_action_enabled('group_create') && state.isGroupedByM2ONoColumn;
            this.$buttons.find('.o-kanban-button-new').toggleClass('o_hidden', createHidden);
        }
    },
    /**
     * @private
     * @returns {Promise}
     */
    _updateSearchPanel: function () {
        return this._searchPanel.update({searchDomain: this.controlPanelDomain});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This handler is called when an event (from the quick create add column)
     * event bubbles up. When that happens, we need to ask the model to create
     * a group and to update the renderer
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAddColumn: function (ev) {
        var self = this;
        this.mutex.exec(function () {
            return self.model.createGroup(ev.data.value, self.handle).then(function () {
                var state = self.model.get(self.handle, {raw: true});
                var ids = _.pluck(state.data, 'res_id').filter(_.isNumber);
                return self._resequenceColumns(ids);
            }).then(function () {
                return self.update({}, {reload: false});
            }).then(function () {
                self._updateButtons();
                self.renderer.quickCreateToggleFold();
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onAddRecordToColumn: function (ev) {
        var self = this;
        var record = ev.data.record;
        var column = ev.target;
        this.alive(this.model.moveRecord(record.db_id, column.db_id, this.handle))
            .then(function (column_db_ids) {
                return self._resequenceRecords(column.db_id, ev.data.ids)
                    .then(function () {
                        _.each(column_db_ids, function (db_id) {
                            var data = self.model.get(db_id);
                            self.renderer.updateColumn(db_id, data);
                        });
                    });
            }).guardedCatch(this.reload.bind(this));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onButtonClicked: function (ev) {
        ev.stopPropagation();
        var attrs = ev.data.attrs;
        var record = ev.data.record;
        if (attrs.context) {
            attrs.context = new Context(attrs.context)
                .set_eval_context({
                    active_id: record.res_id,
                    active_ids: [record.res_id],
                    active_model: record.model,
                });
        }
        this.trigger_up('execute_action', {
            action_data: attrs,
            env: {
                context: record.getContext(),
                currentID: record.res_id,
                model: record.model,
                resIDs: record.res_ids,
            },
            on_closed: this._reloadAfterButtonClick.bind(this, ev.target, ev.data),
        });
    },
    /**
     * @private
     */
    _onButtonNew: function () {
        var self = this;
        var state = this.model.get(this.handle, {raw: true});
        var quickCreateEnabled = this.quickCreateEnabled && viewUtils.isQuickCreateEnabled(state);
        if (this.on_create === 'quick_create' && quickCreateEnabled && state.data.length) {
            // activate the quick create in the first column when the mutex is
            // unlocked, to ensure that there is no pending re-rendering that
            // would remove it (e.g. if we are currently adding a new column)
            this.mutex.getUnlockedDef().then(function () {
                self.renderer.addQuickCreate();
            });
        } else if (this.on_create && this.on_create !== 'quick_create') {
            // Execute the given action
            this.do_action(this.on_create, {
                on_close: this.reload.bind(this, {}),
                additional_context: state.context,
            });
        } else {
            // Open the form view
            this.trigger_up('switch_view', {
                view_type: 'form',
                res_id: undefined
            });
        }
    },
    /**
     * Moves the focus from the controller buttons to the first kanban record
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onButtonsKeyDown: function (ev) {
        switch(ev.keyCode) {
            case $.ui.keyCode.DOWN:
                this.$('.o_kanban_record:first').focus();
        }
    },
    /**
     * Bounce the 'Create' button.
     *
     * @private
     * @param {MouseEvent} ev
     **/
    _onClick: function (ev) {
        var state = this.model.get(this.handle, {raw: true});
        if (!state.count && this.buttons) {
            var classesList = ['o_kanban_view', 'o_kanban_group', 'o_column_quick_create', 'o_view_nocontent_smiling_face'];
            var $target = $(ev.target);
            var hasClassList = _.map(classesList, function(klass){ return $target.hasClass(klass) });
            if (_.some(hasClassList)) {
                this.$buttons.find('.o-kanban-button-new').odooBounce();
            }
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onColumnResequence: function (ev) {
        this._resequenceRecords(ev.target.db_id, ev.data.ids);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onDeleteColumn: function (ev) {
        var self = this;
        var column = ev.target;
        var state = this.model.get(this.handle, {raw: true});
        var relatedModelName = state.fields[state.groupedBy[0]].relation;
        this.model
            .deleteRecords([column.db_id], relatedModelName)
            .then(function () {
                self.update({}, {reload: !column.isEmpty()});
            });
    },
    /**
     * Loads the record of a given column (used in mobile, as the columns are
     * lazy loaded)
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onLoadColumnRecords: function (ev) {
        var self = this;
        this.model.loadColumnRecords(ev.data.columnID).then(function (dbID) {
            var data = self.model.get(dbID);
            return self.renderer.updateColumn(dbID, data).then(function() {
                self._updateEnv();
                if (ev.data.onSuccess) {
                    ev.data.onSuccess();
                }
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onLoadMore: function (ev) {
        var self = this;
        var column = ev.target;
        this.model.loadMore(column.db_id).then(function (db_id) {
            var data = self.model.get(db_id);
            self.renderer.updateColumn(db_id, data);
            self._updateEnv();
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {KanbanColumn} ev.target the column in which the record should
     *   be added
     * @param {Object} ev.data.values the field values of the record to
     *   create; if values only contains the value of the 'display_name', a
     *   'name_create' is performed instead of 'create'
     * @param {function} [ev.data.onFailure] called when the quick creation
     *   failed
     */
    _onQuickCreateRecord: function (ev) {
        var self = this;
        var values = ev.data.values;
        var column = ev.target;
        var onFailure = ev.data.onFailure || function () {};

        // function that updates the kanban view once the record has been added
        // it receives the local id of the created record in arguments
        var update = function (db_id) {
            self._updateEnv();

            var columnState = self.model.getColumn(db_id);
            var state = self.model.get(self.handle);
            return self.renderer
                .updateColumn(columnState.id, columnState, {openQuickCreate: true, state: state})
                .then(function () {
                    if (ev.data.openRecord) {
                        self.trigger_up('open_record', {id: db_id, mode: 'edit'});
                    }
                });
        };

        this.model.createRecordInGroup(column.db_id, values)
            .then(update)
            .guardedCatch(function (reason) {
                reason.event.preventDefault();
                var columnState = self.model.get(column.db_id, {raw: true});
                var context = columnState.getContext();
                var state = self.model.get(self.handle, {raw: true});
                var groupedBy = state.groupedBy[0];
                context['default_' + groupedBy] = viewUtils.getGroupValue(columnState, groupedBy);
                new view_dialogs.FormViewDialog(self, {
                    res_model: state.model,
                    context: _.extend({default_name: values.name || values.display_name}, context),
                    title: _t("Create"),
                    disable_multiple_selection: true,
                    on_saved: function (record) {
                        self.model.addRecordToGroup(column.db_id, record.res_id)
                            .then(update);
                    },
                }).open().opened(onFailure);
            });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onRecordDelete: function (ev) {
        this._deleteRecords([ev.data.id]);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onResequenceColumn: function (ev) {
        var self = this;
        this._resequenceColumns(ev.data.ids).then(function () {
            self._updateEnv();
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Array[]} ev.data.domain the current domain of the searchPanel
     */
    _onSearchPanelDomainUpdated: function (ev) {
        this.searchPanelDomain = ev.data.domain;
        this.reload({offset: 0});
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {boolean} [ev.data.openQuickCreate=false] if true, opens the
     *   QuickCreate in the toggled column (it assumes that we are opening it)
     */
    _onToggleColumn: function (ev) {
        var self = this;
        var column = ev.target;
        this.model.toggleGroup(column.db_id).then(function (db_id) {
            var data = self.model.get(db_id);
            var options = {
                openQuickCreate: !!ev.data.openQuickCreate,
            };
            self.renderer.updateColumn(db_id, data, options);
            self._updateEnv();
        });
    },
    /**
     * @todo should simply use field_changed event...
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} [ev.data.onSuccess] callback to execute after applying
     *   changes
     */
    _onUpdateRecord: function (ev) {
        var onSuccess = ev.data.onSuccess;
        delete ev.data.onSuccess;
        var changes = _.clone(ev.data);
        ev.data.force_save = true;
        this._applyChanges(ev.target.db_id, changes, ev).then(onSuccess);
    },
    /**
     * Allow the user to archive/restore all the records of a column.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onToggleActiveRecords: function (ev) {
        var self = this;
        var column = ev.target;
        var recordIds = _.pluck(column.records, 'db_id');
        if (recordIds.length) {
            this.model
                .toggleActive(recordIds, column.db_id)
                .then(function (dbID) {
                    var data = self.model.get(dbID);
                    self.renderer.updateColumn(dbID, data);
                    self._updateEnv();
                });
        }
    },
});

return KanbanController;

});
