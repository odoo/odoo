odoo.define('web.KanbanController', function (require) {
"use strict";

/**
 * The KanbanController is the class that coordinates the kanban model and the
 * kanban renderer.  It also makes sure that update from the search view are
 * properly interpreted.
 */

var BasicController = require('web.BasicController');
var core = require('web.core');
var Context = require('web.Context');
var form_common = require('web.view_dialogs');

var _t = core._t;
var qweb = core.qweb;

var KanbanController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        quick_create_add_column: '_onAddColumn',
        quick_create_record: '_onQuickCreateRecord',
        resequence_columns: '_onResequenceColumn',
        kanban_do_action: '_onOpenAction',
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

        // true iff grouped by an m2o field and group_create action enabled
        this.create_column_enabled = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        var self = this;
        if (this.hasButtons && this.is_action_enabled('create')) {
            this.$buttons = $(qweb.render("KanbanView.buttons", {}));
            this.$buttons.on('click', 'button.o-kanban-button-new', function () {
                var data = self.model.get(self.handle, {raw: true});
                if (data.groupedBy.length > 0 && data.count > 0 && self.on_create === 'quick_create') {
                    // Activate the quick create in the first column
                    self.renderer.add_quick_create();
                } else if (self.on_create && self.on_create !== 'quick_create') {
                    // Execute the given action
                    self.do_action(self.on_create, {
                        on_close: self.reload.bind(self),
                        additional_context: data.context,
                    });
                } else {
                    // Open the form view
                    self.trigger_up('switch_view', {
                        view_type: 'form',
                        res_id: undefined
                    });
                }
            });
            this._updateButtons();
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Override update method to recompute create_column_enabled.
     *
     * @returns {Deferred}
     */
    update: function () {
        var state = this.model.get(this.handle, {raw: true});
        var group_by_field = state.fields[state.groupedBy[0]];
        var grouped_by_m2o = group_by_field && (group_by_field.type === 'many2one');
        var groupCreate = this.is_action_enabled('group_create');
        this.create_column_enabled = grouped_by_m2o && groupCreate;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override method comes from field manager mixin
     * @param {string} id local id from the basic record data
     */
    _confirmSave: function (id) {
        this.renderer.update_record(this.model.get(id));
    },
    /**
     * @todo this is dead code right now. resurrect this?
     *
     * @returns {boolean}
     */
    _hasContent: function () {
        return this._super.apply(this, arguments) || this.create_column_enabled;
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
            var create_muted = data.count === 0 && this.create_column_enabled;
            this.$buttons.find('.o-kanban-button-new')
                .toggleClass('btn-primary', !create_muted)
                .toggleClass('btn-default', create_muted);
        }
    },
    /**
     * @override
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function (state) {
        var hasNoContent = state.count === 0 && !this.create_column_enabled;
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
                            self.renderer.update_column(db_id, data);
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
        var record_ids = [];
        _.each(column.records, function (kanban_record) {
            if (kanban_record.record.active.value !== active_value) {
                record_ids.push(kanban_record.db_id);
            }
        });
        if (record_ids.length) {
            this.model
                .toggleActive(record_ids, active_value, column.db_id)
                .then(function (db_id) {
                    var data = self.model.get(db_id);
                    self.renderer.update_column(db_id, data);
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
            .deleteRecords([column.db_id], relatedModelName, this.handle)
            .done(function () {
                if (column.is_empty()) {
                    self.renderer.remove_widget(column);
                    self._updateButtons();
                } else {
                    self.reload();
                }
            });
    },
    /**
     * This method comes from the field manager mixin.  Since there is no
     * onchange for kanban, we force a save for every change
     *
     * @override
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        event.data.force_save = true;
        this._super.apply(this, arguments);
    },
    /**
     * @param {OdooRevent} event
     */
    _onLoadMore: function (event) {
        var self = this;
        var column = event.target;
        this.model.load_more(column.db_id).then(function (db_id) {
            var data = self.model.get(db_id);
            self.renderer.update_column(db_id, data);
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onOpenAction: function (event) {
        var self = this;
        var record = event.target;
        if (event.data.context) {
            event.data.context = new Context(event.data.context)
                .set_eval_context({
                    active_id: event.target.id,
                    active_ids: [event.target.id],
                    active_model: this.modelName,
                });
        }
        this.trigger_up('execute_action', {
            action_data: event.data,
            model: this.modelName,
            record_id: event.target.id,
            on_close: function () {
                self.model.reload(record.db_id).then(function (db_id) {
                    var data = self.model.get(db_id);
                    record.update(data);
                });
            },
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onQuickCreateRecord: function (event) {
        var self = this;
        var column = event.target;
        var data = this.model.get(column.db_id);
        function add_record(records) {
            return self.model
                .addRecordToGroup(data.id, records[0])
                .then(function (db_id) {
                    column.add_record(self.model.get(db_id), {position: 'before'});
                });
        }
        data.context['default_' + data.groupedBy[0]] = column.id;
        this.model
            .nameCreate(data.model, event.data.value, data.context)
            .then(add_record)
            .fail(function (event) {
                event.preventDefault();
                var popup = new form_common.SelectCreatePopup(this);
                popup.select_element(
                    data.model,
                    {
                        title: _t("Create: "),
                        initial_view: "form",
                        disable_multiple_selection: true,
                    },
                    [],
                    { default_name: event.data.value }
                );
                popup.on("elements_selected", null, add_record);
            });
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
        var grouped_by = this.model.get(this.handle).groupedBy[0];
        var model = this.fields_view.fields[grouped_by].relation;
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
            self.renderer.update_column(db_id, data);
        });
    },
    /**
     * @param {OdooEvent} event
     */
    _onUpdateRecord: function (event) {
        var record = event.target;
        this.alive(this.model.save(record.db_id, event.data))
            .then(record.update.bind(record));
    },
});

return KanbanController;

});
