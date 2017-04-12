odoo.define('web.KanbanColumn', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var kanban_quick_create = require('web.kanban_quick_create');
var KanbanRecord = require('web.KanbanRecord');
var view_dialogs = require('web.view_dialogs');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;
var RecordQuickCreate = kanban_quick_create.RecordQuickCreate;

var KanbanColumn = Widget.extend({
    template: 'KanbanView.Group',
    custom_events: {
        cancel_quick_create: '_onCancelQuickCreate',
        kanban_record_delete: '_onDeleteRecord',
        quick_create_add_record: '_onQuickCreateAddRecord',
    },
    events: {
        'click .o_column_edit': '_onEditColumn',
        'click .o_column_delete': '_onDeleteColumn',
        'click .o_column_archive': '_onArchiveRecords',
        'click .o_column_unarchive': '_onUnarchiveRecords',
        'click .o_kanban_quick_add': '_onAddQuickCreate',
        'click .o_kanban_load_more': '_onLoadMore',
        'click .o_kanban_toggle_fold': '_onToggleFold',
    },
    /**
     * @override
     */
    init: function (parent, data, options, recordOptions) {
        this._super(parent);
        this.db_id = data.id;
        this.data_records = data.data;

        var value = data.value;
        this.id = data.res_id || value;
        var field = data.fields[data.groupedBy[0]]; // fixme: grouped by field might not be in the fvg
        if (field && field.type === "selection") {
            value = _.find(field.selection, function (s) { return s[0] === data.value; })[1]; // fixme: same process done in list_renderer
        }
        // todo: handle group_by_m2o (nameget)
        this.title = value || _t('Undefined');
        this.folded = !data.isOpen;
        this.has_active_field = 'active' in data.fields;
        this.size = data.count;
        this.values = data.values;
        this.fields = data.fields;
        this.records = [];
        this.modelName = data.model;

        this.quick_create = options.quick_create;
        this.grouped_by_m2o = options.grouped_by_m2o;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.draggable = recordOptions.draggable;
        this.records_editable = options.records_editable;
        this.records_deletable = options.records_deletable;
        this.relation = options.relation;
        this.offset = 0;
        this.remaining = this.size - this.data_records.length;

        this.record_options = _.clone(recordOptions);

        if (data.options && data.options.group_by_tooltip) {
            var self = this;
            this.tooltip_info = _.map(data.options.group_by_tooltip, function (key, value) {
                return (self.values && self.values[value] && "<div>" +key + "<br>" + self.values[value] + "</div>") || '';
            }).join('');
        } else {
            this.tooltip_info = "";
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$header = this.$('.o_kanban_header');

        for (var i = 0; i < this.data_records.length; i++) {
            this.addRecord(this.data_records[i], {no_update: true});
        }
        this.$header.tooltip();

        if (config.device.size_class > config.device.SIZES.XS && this.draggable !== false) {
            // deactivate sortable in mobile mode.  It does not work anyway,
            // and it breaks horizontal scrolling in kanban views.  Someday, we
            // should find a way to use the touch events to make sortable work.
            this.$el.sortable({
                connectWith: '.o_kanban_group',
                revert: 0,
                delay: 0,
                items: '> .o_kanban_record:not(.o_updating)',
                helper: 'clone',
                cursor: 'move',
                over: function () {
                    self.$el.addClass('o_kanban_hover');
                    self._update();
                },
                out: function () {
                    self.$el.removeClass('o_kanban_hover');
                },
                update: function (event, ui) {
                    var record = ui.item.data('record');
                    var index = self.records.indexOf(record);
                    record.$el.removeAttr('style');  // jqueryui sortable add display:block inline
                    ui.item.addClass('o_updating');
                    if (index >= 0) {
                        if ($.contains(self.$el[0], record.$el[0])) {
                            // resequencing records
                            self.trigger_up('kanban_column_resequence', {ids: self._getIDs()});
                        }
                    } else {
                        // adding record to this column
                        self.trigger_up('kanban_column_add_record', {record: record, ids: self._getIDs()});
                    }
                }
            });
        }
        this.$el.click(function (event) {
            if (self.folded) {
                self._onToggleFold(event);
            }
        });
        this._update();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds the quick create record to the top of the column.
     */
    addQuickCreate: function () {
        if (this.quickCreateWidget) {
            return;
        }
        var self = this;
        var width = this.records.length ? this.records[0].$el.innerWidth() : this.$el.width() - 8;
        this.quickCreateWidget = new RecordQuickCreate(this, width);
        this.quickCreateWidget.insertAfter(this.$header);
        this.quickCreateWidget.$el.focusout(function () {
            var hasFocus = (self.quickCreateWidget.$(':focus').length > 0);
            if (! hasFocus && self.quickCreateWidget) {
                self._cancelQuickCreate();
            }
        });
    },
    /**
     * Adds a record in the column.
     *
     * @param {Object} recordState
     * @param {Object} options
     * @params {string} options.position 'before' to add the record at the top,
     *                  added at the bottom by default
     * @params {Boolean} options.no_update set to true not to update the column
     */
    addRecord: function (recordState, options) {
        var record = new KanbanRecord(this, recordState, this.record_options);
        this.records.push(record);
        if (options.position === 'before') {
            record.insertAfter(this.quickCreateWidget ? this.quickCreateWidget.$el : this.$header);
        } else {
            var $load_more = this.$('.o_kanban_load_more');
            if ($load_more.length) {
                record.insertBefore($load_more);
            } else {
                record.appendTo(this.$el);
            }
        }
        if (!options.no_update) {
            this._update();
        }
    },
    /**
     * @returns {Boolean} true iff the column is empty
     */
    isEmpty: function () {
        return !this.records.length;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Destroys the QuickCreate widget.
     *
     * @private
     */
    _cancelQuickCreate: function () {
        this.quickCreateWidget.destroy();
        this.quickCreateWidget = undefined;
    },
    /**
     * @returns {integer[]} the res_ids of the records in the column
     */
    _getIDs: function () {
        var ids = [];
        this.$('.o_kanban_record').each(function (index, r) {
            ids.push($(r).data('record').id);
        });
        return ids;
    },
    /**
     * @private
     */
    _update: function () {
        var title = this.folded ? this.title + ' (' + this.size + ')' : this.title;
        this.$header.find('.o_column_title').text(title);
        this.$header.find('.o-kanban-count').text(this.records.length);

        this.$el.toggleClass('o_column_folded', this.folded);
        var tooltip = this.size + _t(' records');
        tooltip = '<p>' + tooltip + '</p>' + this.tooltip_info;
        this.$header.tooltip({html: true}).attr('data-original-title', tooltip);
        if (!this.remaining) {
            this.$('.o_kanban_load_more').remove();
        } else {
            this.$('.o_kanban_load_more').html(QWeb.render('KanbanView.LoadMore', {widget: this}));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddQuickCreate: function () {
        this.addQuickCreate();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onArchiveRecords: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: true});
    },
    /**
     * @private
     */
    _onCancelQuickCreate: function () {
        this._cancelQuickCreate();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onDeleteColumn: function (event) {
        event.preventDefault();
        var buttons = [
            {
                text: _t("Ok"),
                classes: 'btn-primary',
                close: true,
                click: this.trigger_up.bind(this, 'kanban_column_delete'),
            },
            {text: _t("Cancel"), close: true}
        ];
        new Dialog(this, {
            size: 'medium',
            buttons: buttons,
            $content: $('<div>', {
                text: _t("Are you sure that you want to remove this column ?")
            }),
        }).open();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDeleteRecord: function (event) {
        var self = this;
        event.data.parent_id = this.db_id;
        event.data.after = function cleanup() {
            var index = self.records.indexOf(event.data.record);
            self.records.splice(index, 1);
            self._update();
        };
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onEditColumn: function (event) {
        event.preventDefault();
        new view_dialogs.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            title: _t("Edit Column"),
            on_saved: this.trigger_up.bind(this, 'reload'),
        }).open();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onLoadMore: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_load_more');
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreateAddRecord: function (event) {
        this.trigger_up('quick_create_record', event.data);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onToggleFold: function (event) {
        event.preventDefault();
        this.trigger_up('column_toggle_fold');
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onUnarchiveRecords: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: false});
    },
});

return KanbanColumn;

});
