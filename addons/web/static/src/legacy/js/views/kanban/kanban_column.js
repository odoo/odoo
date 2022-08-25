odoo.define('web.KanbanColumn', function (require) {
"use strict";

var core = require('web.core');
var config = require('web.config');
var session = require('web.session');
var Dialog = require('web.Dialog');
var KanbanRecord = require('web.KanbanRecord');
var RecordQuickCreate = require('web.kanban_record_quick_create');
var view_dialogs = require('web.view_dialogs');
var viewUtils = require('web.viewUtils');
var Widget = require('web.Widget');
var KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');

var _t = core._t;
var QWeb = core.qweb;

var KanbanColumn = Widget.extend({
    template: 'KanbanView.Group',
    custom_events: {
        cancel_quick_create: '_onCancelQuickCreate',
        quick_create_add_record: '_onQuickCreateAddRecord',
        tweak_column: '_onTweakColumn',
        tweak_column_records: '_onTweakColumnRecords',
    },
    events: {
        'click .o_column_edit': '_onEditColumn',
        'click .o_column_delete': '_onDeleteColumn',
        'click .o_kanban_quick_add': '_onAddQuickCreate',
        'click .o_kanban_load_more': '_onLoadMore',
        'click .o_kanban_toggle_fold': '_onToggleFold',
        'click .o_column_archive_records': '_onArchiveRecords',
        'click .o_column_unarchive_records': '_onUnarchiveRecords',
        'click .o_kanban_config .dropdown-menu': '_onConfigDropdownClicked',
    },
    /**
     * @override
     */
    init: function (parent, data, options, recordOptions) {
        this._super(parent);
        this.db_id = data.id;
        this.data_records = data.data;
        this.data = data;

        var value = data.value;
        this.id = data.res_id;
        this.folded = !data.isOpen;
        this.has_active_field = 'active' in data.fields;
        this.fields = data.fields;
        this.records = [];
        this.modelName = data.model;

        this.quick_create = options.quick_create;
        this.quickCreateView = options.quickCreateView;
        this.groupedBy = options.groupedBy;
        this.grouped_by_m2o = options.grouped_by_m2o;
        this.grouped_by_m2m = options.grouped_by_m2m;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.archivable = options.archivable;
        this.draggable = options.draggable;
        this.KanbanRecord = options.KanbanRecord || KanbanRecord; // the KanbanRecord class to use
        this.records_editable = options.records_editable;
        this.records_deletable = options.records_deletable;
        this.recordsDraggable = options.recordsDraggable;
        this.relation = options.relation;
        this.offset = 0;
        this.loadMoreCount = data.loadMoreCount;
        this.loadMoreOffset = data.loadMoreOffset;
        this.isMobile = config.device.isMobile;

        if (options.hasProgressBar) {
            this.barOptions = {
                columnID: this.db_id,
                progressBarStates: options.progressBarStates,
            };
        }

        this.record_options = _.clone(recordOptions);

        if (options.grouped_by_m2o || options.grouped_by_date || options.grouped_by_m2m) {
            // For many2x and datetime, a false value means that the field is not set.
            this.title = value ? value : _t('None');
        } else if (this.groupedBy && this.fields[this.groupedBy].type === 'boolean') {
            this.title = value === undefined ? _t('None') : (value ? _t('Yes') : _t('No'));
        } else {
            // False and 0 might be valid values for these fields.
            this.title = value === undefined ? _t('None') : value;
        }

        if (options.group_by_tooltip) {
            this.tooltipInfo = _.compact(_.map(options.group_by_tooltip, function (help, field) {
                help = help ? help + "</br>" : '';
                return (data.tooltipData && data.tooltipData[field] && "<div>" + help + data.tooltipData[field] + "</div>") || '';
            }));
            this.tooltipInfo = this.tooltipInfo.join("<div class='dropdown-divider' role='separator' />");
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        this.$header = this.$('.o_kanban_header');

        for (var i = 0; i < this.data_records.length; i++) {
            defs.push(this._addRecord(this.data_records[i]));
        }

        if (this.recordsDraggable && !config.device.isMobile) {
            this.$el.sortable({
                connectWith: '.o_kanban_group',
                containment: this.draggable ? false : 'parent',
                revert: 0,
                delay: 0,
                items: '> .o_kanban_record:not(.o_updating)',
                cursor: 'move',
                over: function () {
                    self.$el.addClass('o_kanban_hover');
                },
                out: function () {
                    self.$el.removeClass('o_kanban_hover');
                },
                start: function (event, ui) {
                    ui.item.addClass('o_currently_dragged');
                },
                stop: function (event, ui) {
                    var item = ui.item;
                    setTimeout(function () {
                        item.removeClass('o_currently_dragged');
                    });
                },
                update: function (event, ui) {
                    var record = ui.item.data('record');
                    var index = self.records.indexOf(record);
                    record.$el.removeAttr('style');  // jqueryui sortable add display:block inline
                    if (index >= 0) {
                        if ($.contains(self.$el[0], record.$el[0])) {
                            // resequencing records
                            self.trigger_up('kanban_column_resequence', {ids: self._getIDs()});
                        }
                    } else {
                        // adding record to this column
                        ui.item.addClass('o_updating');
                        self.trigger_up('kanban_column_add_record', {record: record, ids: self._getIDs()});
                    }
                }
            });
        }
        if (!config.device.isMobile) {
            this.$el.click(function (event) {
                if (self.folded) {
                    self._onToggleFold(event);
                }
            });
        }
        if (this.barOptions) {
            this.$el.addClass('o_kanban_has_progressbar');
            this.progressBar = this._getKanbanColumnProgressBar();
            defs.push(this.progressBar.appendTo(this.$header));
        }

        var title = !config.device.isMobile && this.folded ? this.title + ' (' + this.data.count + ')' : this.title;
        this.$header.find('.o_column_title').text(title);

        this.$el.toggleClass('o_column_folded', !config.device.isMobile && this.folded);
        if (this.tooltipInfo) {
            this.$header.find('.o_kanban_header_title').tooltip({}).attr('data-bs-original-title', this.tooltipInfo);
        }
        if (!this.loadMoreCount) {
            this.$('.o_kanban_load_more').remove();
        } else {
            this.$('.o_kanban_load_more').html(QWeb.render('KanbanView.LoadMore', {widget: this}));
        }

        return Promise.all(defs);
    },
    /**
     * Called when a record has been quick created, as a new column is rendered
     * and appended into a fragment, before replacing the old column in the DOM.
     * When this happens, the quick create widget is inserted into the new
     * column directly, and it should be focused. However, as it is rendered
     * into a fragment, the focus has to be set manually once in the DOM.
     */
    on_attach_callback: function () {
        _.invoke(this.records, 'on_attach_callback');
        if (this.quickCreateWidget) {
            this.quickCreateWidget.on_attach_callback();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds the quick create record to the top of the column.
     *
     * @returns {Promise}
     */
    addQuickCreate: async function () {
        if (this.folded) {
            // first open the column, and then add the quick create
            this.trigger_up('column_toggle_fold', {
                openQuickCreate: true,
            });
            return;
        }

        if (this.quickCreateWidget) {
            return Promise.reject();
        }
        this.trigger_up('close_quick_create'); // close other quick create widgets
        var context = this.data.getContext();
        var groupByField = viewUtils.getGroupByField(this.groupedBy);
        context['default_' + groupByField] = viewUtils.getGroupValue(this.data, this.groupedBy);
        this.quickCreateWidget = new RecordQuickCreate(this, {
            context: context,
            formViewRef: this.quickCreateView,
            model: this.modelName,
        });
        await this.quickCreateWidget.appendTo(document.createDocumentFragment());
        this.trigger_up('start_quick_create');
        this.quickCreateWidget.$el.insertAfter(this.$header);
        this.quickCreateWidget.on_attach_callback();
    },
    /**
     * Closes the quick create widget if it isn't dirty.
     */
    cancelQuickCreate: function () {
        if (this.quickCreateWidget) {
            this.quickCreateWidget.cancel();
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
     * Adds a record in the column.
     *
     * @private
     * @param {Object} recordState
     * @param {Object} [options]
     * @param {string} [options.position]
     *        'before' to add at the top, add at the bottom by default
     * @return {Promise}
     */
    _addRecord: function (recordState, options) {
        if (this.grouped_by_m2m) {
            this.record_options.deletable = false;
        }
        var record = new this.KanbanRecord(this, recordState, this.record_options);
        this.records.push(record);
        if (options && options.position === 'before') {
            return record.insertAfter(this.quickCreateWidget ? this.quickCreateWidget.$el : this.$header);
        } else {
            var $load_more = this.$('.o_kanban_load_more');
            if ($load_more.length) {
                return record.insertBefore($load_more);
            } else {
                return record.appendTo(this.$el);
            }
        }
    },
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
     * This method can be over-ridden when custom ColumnProgressbar is to be used
     *
     * @private
     * @returns {Widget} the instance of 'KanbanColumnProgressBar'
     */
    _getKanbanColumnProgressBar: function () {
        return new KanbanColumnProgressBar(this, this.barOptions, this.data);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddQuickCreate: function () {
        this.trigger_up('add_quick_create', { groupId: this.db_id });
    },
    /**
     * @private
     */
    _onCancelQuickCreate: function () {
        this._cancelQuickCreate();
    },
    /**
     * Prevent from closing the config dropdown when the user clicks on a
     * disabled item (e.g. 'Fold' in sample mode).
     *
     * @private
     */
    _onConfigDropdownClicked(ev) {
        ev.stopPropagation();
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
     * @param {MouseEvent} event
     */
    _onEditColumn: function (event) {
        event.preventDefault();
        new view_dialogs.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            context: session.user_context,
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
        if (this.folded) {
            this.trigger_up('column_toggle_fold');
        } else {
            this.trigger_up('kanban_load_column_records', { loadMoreOffset: this.loadMoreOffset });
        }
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
     * @param {OdooEvent} ev
     */
    _onTweakColumn: function (ev) {
        ev.data.callback(this.$el);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onTweakColumnRecords: function (ev) {
        _.each(this.records, function (record) {
            ev.data.callback(record.$el, record.state.data);
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onArchiveRecords: function (event) {
        event.preventDefault();
        Dialog.confirm(this, _t("Are you sure that you want to archive all the records from this column?"), {
            confirm_callback: this.trigger_up.bind(this, 'kanban_column_records_toggle_active', {
                archive: true,
            }),
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onUnarchiveRecords: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_records_toggle_active', {
            archive: false,
        });
    }
});

return KanbanColumn;

});
