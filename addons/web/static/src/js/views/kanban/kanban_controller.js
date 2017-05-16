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
var view_dialogs = require('web.view_dialogs');

var _t = core._t;
var qweb = core.qweb;

var KanbanController = BasicController.extend({
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
        kanban_column_archive_records: '_onArchiveRecords',
        kanban_load_more: '_onLoadMore',
        column_toggle_fold: '_onToggleColumn',
    }),
    /**
     * @override
     * @param {Object} params
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.on_create = params.on_create;
        this.hasButtons = params.hasButtons;

        this.createColumnEnabled = this._isCreateColumnEnabled();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        if (this.hasButtons && this.is_action_enabled('create')) {
            this.$buttons = $(qweb.render('KanbanView.buttons', {widget: this}));
            this.$buttons.on('click', 'button.o-kanban-button-new', this._onButtonNew.bind(this));
            this._updateButtons();
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Override update method to recompute createColumnEnabled.
     *
     * @returns {Deferred}
     */
    update: function () {
        this.createColumnEnabled = this._isCreateColumnEnabled();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override method comes from field manager mixin
     * @param {string} id local id from the basic record data
     * @returns {Deferred}
     */
    _confirmSave: function (id) {
        return this.renderer.updateRecord(this.model.get(id));
    },
    /**
     * The nocontent helper should be displayed in kanban:
     *   - ungrouped: if there is no records
     *   - grouped: if there is no groups and no column quick create
     *
     * @override
     * @private
     */
    _hasContent: function (state) {
        return this._super.apply(this, arguments) ||
               this.createColumnEnabled ||
               (state.groupedBy.length && state.data.length);
    },
    /**
     * The column quick create should be displayed in kanban iff grouped by an
     * m2o field and group_create action enabled.
     *
     * @returns {boolean}
     */
    _isCreateColumnEnabled: function () {
        var groupCreate = this.is_action_enabled('group_create');
        if (!groupCreate) {
            // pre-return to avoid a lot of the following processing
            return false;
        }
        var state = this.model.get(this.handle, {raw: true});
        var groupByField = state.fields[state.groupedBy[0]];
        var groupedByM2o = groupByField && (groupByField.type === 'many2one');
        return groupedByM2o;
    },
    /**
     * This method calls the server to ask for a resequence.  Note that this
     * does not rerender the user interface, because in most case, the
     * resequencing operation has already been displayed by the renderer.
     *
     * @param {string} column_id
     * @param {string[]} ids
     * @returns {Deferred}
     */
    _resequenceRecords: function (column_id, ids) {
        return this.model.resequence(this.modelName, ids, column_id);
    },
    /**
     * In grouped mode, set 'Create' button as btn-default if there is no column
     * (except if we can't create new columns)
     *
     * @override from abstract controller
     */
    _updateButtons: function () {
        if (this.$buttons) {
            var data = this.model.get(this.handle, {raw: true});
            var createMuted = data.count === 0 && this.createColumnEnabled;
            this.$buttons.find('.o-kanban-button-new')
                .toggleClass('btn-primary', !createMuted)
                .toggleClass('btn-default', createMuted);
        }
    },
    /**
     * @override
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function (state) {
        var hasNoContent = !this._hasContent(state);
        this.$el.toggleClass('o_kanban_nocontent', hasNoContent);
        this._toggleNoContentHelper(hasNoContent);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This handler is called when an event (from the quick create add column)
     * event bubbles up. When that happens, we need to ask the model to create
     * a group and to update the renderer
     *
     * @param {OdooEvent} event
     */
    _onAddColumn: function (event) {
        var self = this;
        this.model.createGroup(event.data.value, this.handle).then(function () {
            self.update({}, {reload: false});
            self._updateButtons();
            self.trigger_up('scrollTo', {selector: '.o_column_quick_create'});
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onAddRecordToColumn: function (event) {
        var self = this;
        var record = event.data.record;
        var column = event.target;
        this.alive(this.model.moveRecord(record.db_id, column.db_id, this.handle))
            .then(function (column_db_ids) {
                return self._resequenceRecords(column.db_id, event.data.ids)
                    .then(function () {
                        _.each(column_db_ids, function (db_id) {
                            var data = self.model.get(db_id);
                            self.renderer.updateColumn(db_id, data);
                        });
                });
            }).fail(this.reload.bind(this));
    },
    /**
     * The interface allows in some case the user to archive a column. This is
     * what this handler is for.
     *
     * @param {OdooEvent} event
     */
    _onArchiveRecords: function (event) {
        var self = this;
        var active_value = !event.data.archive;
        var column = event.target;
        var record_ids = _.pluck(column.records, 'db_id');
        if (record_ids.length) {
            this.model
                .toggleActive(record_ids, active_value, column.db_id)
                .then(function (db_id) {
                    var data = self.model.get(db_id);
                    self.renderer.updateColumn(db_id, data);
                });
        }
    },
    /**
     * @param {OdooEvent} event
     */
    _onColumnResequence: function (event) {
        this._resequenceRecords(event.target.db_id, event.data.ids);
    },
    /**
     * @param {OdooEvent} event
     */
    _onDeleteColumn: function (event) {
        var self = this;
        var column = event.target;
        var state = this.model.get(this.handle, {raw: true});
        var relatedModelName = state.fields[state.groupedBy[0]].relation;
        this.model
            .deleteRecords([column.db_id], relatedModelName)
            .done(function () {
                if (column.isEmpty()) {
                    self.renderer.removeWidget(column);
                    self._updateButtons();
                } else {
                    self.reload();
                }
            });
    },
    /**
     * @param {OdooRevent} event
     */
    _onLoadMore: function (event) {
        var self = this;
        var column = event.target;
        this.model.loadMore(column.db_id).then(function (db_id) {
            var data = self.model.get(db_id);
            self.renderer.updateColumn(db_id, data);
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        var self = this;
        var attrs = event.data.attrs;
        var record = event.data.record;
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
            model: record.model,
            record_id: record.res_id,
            on_closed: function () {
                self.model.reload(record.id).then(function (db_id) {
                    var data = self.model.get(db_id);
                    var kanban_record = event.target;
                    kanban_record.update(data);
                });
            },
        });
    },
    /**
     * @private
     */
    _onButtonNew: function () {
        var data = this.model.get(this.handle, {raw: true});
        if (data.groupedBy.length > 0 && data.count > 0 && this.on_create === 'quick_create') {
            // Activate the quick create in the first column
            this.renderer.addQuickCreate();
        } else if (this.on_create && this.on_create !== 'quick_create') {
            // Execute the given action
            this.do_action(this.on_create, {
                on_close: this.reload.bind(this),
                additional_context: data.context,
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
     * @param {OdooEvent} event
     */
    _onQuickCreateRecord: function (event) {
        var self = this;
        var column = event.target;
        var name = event.data.value;
        var state = this.model.get(this.handle, {raw: true});
        var columnState = this.model.get(column.db_id, {raw: true});
        var context = columnState.getContext();
        context['default_' + state.groupedBy[0]] = columnState.res_id;

        this._rpc({
                model: state.model,
                method: 'name_create',
                args: [name],
                context: context,
            })
            .then(add_record)
            .fail(function (error, event) {
                event.preventDefault();
                new view_dialogs.FormViewDialog(self, {
                    res_model: state.model,
                    context: _.extend({default_name: name}, context),
                    title: _t("Create"),
                    disable_multiple_selection: true,
                    on_saved: function(record) {
                        add_record([record.res_id]);
                    },
                }).open();
            });

        function add_record(records) {
            return self.model
                .addRecordToGroup(columnState.id, records[0])
                .then(function (db_id) {
                    column.addRecord(self.model.get(db_id), {position: 'before'});
                });
        }
    },
    /**
     * @param {OdooEvent} event
     */
    _onRecordDelete: function (event) {
        this._deleteRecords([event.data.id]);
    },
    /**
     * @param {OdooEvent} event
     */
    _onResequenceColumn: function (event) {
        var state = this.model.get(this.handle, {raw: true});
        var model = state.fields[state.groupedBy[0]].relation;
        this.model.resequence(model, event.data.ids, this.handle);
    },
    /**
     * @param {OdooEvent} event
     */
    _onToggleColumn: function (event) {
        var self = this;
        var column = event.target;
        this.model.toggleGroup(column.db_id).then(function (db_id) {
            var data = self.model.get(db_id);
            self.renderer.updateColumn(db_id, data);
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onUpdateRecord: function (event) {
        var self = this;
        var record = event.target;
        this.model.notifyChanges(record.db_id, event.data).then(function () {
            self.model.save(record.db_id).then(function () {
                var state = self.model.get(record.db_id);
                record.update(state);
            });
        });
    },
});

return KanbanController;

});
