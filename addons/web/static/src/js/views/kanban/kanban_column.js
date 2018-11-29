odoo.define('web.KanbanColumn', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var KanbanRecord = require('web.KanbanRecord');
var RecordQuickCreate = require('web.kanban_record_quick_create');
var view_dialogs = require('web.view_dialogs');
var viewUtils = require('web.viewUtils');
var Widget = require('web.Widget');
var KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');

var _t = core._t;
var QWeb = core.qweb;
var Sortable = window.Sortable;

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
        'click .o_column_unarchive_records': '_onUnarchiveRecords'
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
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.archivable = options.archivable;
        this.draggable = options.draggable;
        this.KanbanRecord = options.KanbanRecord || KanbanRecord; // the KanbanRecord class to use
        this.records_editable = options.records_editable;
        this.records_deletable = options.records_deletable;
        this.relation = options.relation;
        this.offset = 0;
        this.remaining = data.count - this.data_records.length;

        if (options.hasProgressBar) {
            this.barOptions = {
                columnID: this.db_id,
                progressBarStates: options.progressBarStates,
            };
        }

        this.record_options = _.clone(recordOptions);

        if (options.grouped_by_m2o) {
            // For many2one, a false value means that the field is not set.
            this.title = value ? value : _t('Undefined');
        } else {
            // False and 0 might be valid values for these fields.
            this.title = value === undefined ? _t('Undefined') : value;
        }

        if (options.group_by_tooltip) {
            this.tooltipInfo = _.map(options.group_by_tooltip, function (help, field) {
                return (data.tooltipData && data.tooltipData[field] && "<div>" + help + "<br>" + data.tooltipData[field] + "</div>") || '';
            }).join('');
        } else {
            this.tooltipInfo = "";
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
            var def = this._addRecord(this.data_records[i]);
            if (def.state() === 'pending') {
                defs.push(def);
            }
        }
        this.$header.find('.o_kanban_header_title').tooltip();

        var scrollDelay = 0;
        var $scrollableParent = this._getScrollableParent();
        new Sortable(this.$('.o_kanban_record_wrap')[0], {
            group: {
                name: '.o_kanban_record_wrap',
                pull: self.draggable,
            },
            ghostClass: 'oe_kanban_card_ghost',
            chosenClass: 'o_kanban_record_chosen',
            draggable: '.o_kanban_record:not(.o_updating)',
            scroll: config.device.isMobile ? true  : $scrollableParent && $scrollableParent[0],
            // bubbleScroll: true,
            scrollSpeed: 20,
            scrollSensitivity: 40,
            delay: config.device.isMobile ? 200 : 0,
            forceFallback: true,
            fallbackClass: 'o_kanban_record_clone',
            rotateElement: 'o_kanban_record_clone', // just pass fallbackClass to rotate
            scrollFn: config.device.isMobile ? function (offsetX, offsetY, originalEvent, touchEvt, hoverTargetEl) {
                // rubaxa calls scrollFn on each 24 miliseconds, 24 seconds are fix we can not configure it
                // we need to add such custom logic to increase delay
                // MSH: we should fork rubaxa and do some customization as per our need, as it has too rigid timeout and some rigid code
                if (offsetX !== 0) { // while dragging horizontally
                    scrollDelay += 1;
                    if (scrollDelay > 50) {
                        var swipeTo = offsetX > 0 ? 'left' : 'right';
                        self.trigger_up("kanban_column_swipe_" + swipeTo);
                        scrollDelay = 0;
                    }
                } else if (offsetY !== 0) { // while dragging vertically
                    self.$el.scrollTop(self.$el.scrollTop() + offsetY);
                }
            } : false,
            onStart: function () {
                if (config.device.isMobile) {
                    self.$el.swipe('disable');
                }
            },
            onAdd: function (event) {
                var $item = $(event.item);
                var record = $item.data('record');
                if ($(event.to).parent().data('id') !== $(event.from).parent().data('id')) {
                    // adding record to this column
                    $(event.item).addClass('o_updating');
                    self.trigger_up('kanban_column_add_record', {record: record, ids: self._getIDs()});
                } else {
                    $item.remove();
                }
            },
            onUpdate: function (event) {
                var record = $(event.item).data('record');
                if ($.contains(self.$el[0], record.$el[0])) {
                    // resequencing records
                    self.trigger_up('kanban_column_resequence', {ids: self._getIDs()});
                }
            },
            onEnd: function () {
                if (config.device.isMobile) {
                    self.$el.swipe('enable');
                }
            },
        });
        this.$el.click(function (event) {
            if (self.folded) {
                self._onToggleFold(event);
            }
        });
        if (this.barOptions) {
            this.$el.addClass('o_kanban_has_progressbar');
            this.progressBar = new KanbanColumnProgressBar(this, this.barOptions, this.data);
            defs.push(this.progressBar.appendTo(this.$header));
        }

        var title = this.folded ? this.title + ' (' + this.data.count + ')' : this.title;
        this.$header.find('.o_column_title').text(title);

        this.$el.toggleClass('o_column_folded', this.folded && !config.device.isMobile);
        var tooltip = this.data.count + _t(' records');
        tooltip = '<p>' + tooltip + '</p>' + this.tooltipInfo;
        this.$header.find('.o_kanban_header_title').tooltip({}).attr('data-original-title', tooltip);
        if (!this.remaining) {
            this.$('.o_kanban_load_more').remove();
        } else {
            this.$('.o_kanban_load_more').html(QWeb.render('KanbanView.LoadMore', {widget: this}));
        }

        return $.when.apply($, defs);
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
     * @returns {Deferred}
     */
    addQuickCreate: function () {
        if (this.folded) {
            // first open the column, and then add the quick create
            this.trigger_up('column_toggle_fold', {
                openQuickCreate: true,
            });
            return;
        }

        if (this.quickCreateWidget) {
            return $.Deferred().reject();
        }
        this.trigger_up('close_quick_create'); // close other quick create widgets
        this.trigger_up('start_quick_create');
        var context = this.data.getContext();
        context['default_' + this.groupedBy] = viewUtils.getGroupValue(this.data, this.groupedBy);
        this.quickCreateWidget = new RecordQuickCreate(this, {
            context: context,
            formViewRef: this.quickCreateView,
            model: this.modelName,
        });
        return this.quickCreateWidget.insertAfter(this.$header);
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

    /**
     * triggers get_scrollable_parent to find scrollable parent element
     * get_scrollable_parent event is hanled by parents to return specific scrollable element
     * else action_manager element is returned
     *
     * @private
     * @returns {jQuery|undefined} scrollable parent element
     */
    _getScrollableParent: function () {
        var $scrollableParent;
        this.trigger_up('get_scrollable_parent', {
            callback: function ($scrollable_parent) {
                $scrollableParent = $scrollable_parent;
            }
        });
        return $scrollableParent;
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
     * @return {Deferred}
     */
    _addRecord: function (recordState, options) {
        var record = new this.KanbanRecord(this, recordState, this.record_options);
        this.records.push(record);
        if (options && options.position === 'before') {
            return record.insertAfter(this.quickCreateWidget ? this.quickCreateWidget.$el : this.$header);
        } else {
            var $load_more = this.$('.o_kanban_load_more');
            if ($load_more.length) {
                return record.insertBefore($load_more);
            } else {
                return record.appendTo(this.$('.o_kanban_record_wrap'));
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
