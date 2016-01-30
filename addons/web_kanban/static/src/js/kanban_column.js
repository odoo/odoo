odoo.define('web_kanban.Column', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var Widget = require('web.Widget');
var quick_create = require('web_kanban.quick_create');
var KanbanRecord = require('web_kanban.Record');

var _t = core._t;
var QWeb = core.qweb;
var RecordQuickCreate = quick_create.RecordQuickCreate;

var KanbanColumn = Widget.extend({
    template: "KanbanView.Group",

    events: {
        'click .o_kanban_toggle_fold': function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.folded = true;
            this.update_column();
        },
        'click .o_column_edit': 'edit_column',
        'click .o_column_delete': 'delete_column',
        'click .o_column_archive': 'archive_records',
        'click .o_column_unarchive': 'unarchive_records',
        'click .o_kanban_quick_add': 'add_quick_create',
        'click .o_kanban_load_more': 'load_more',
    },

    custom_events: {
        'kanban_record_delete': 'delete_record',
        'cancel_quick_create': 'cancel_quick_create',
        'quick_create_add_record': 'quick_create_add_record',
    },

    init: function(parent, group_data, options, record_options) {
        this._super(parent);
        this.data_records = group_data.records;
        this.dataset = group_data.dataset;
        this.records = [];
        this.title = group_data.title;
        this.id = group_data.id;
        this.folded = group_data.attributes.folded;
        this.fields = options.fields;
        this.values = group_data.values;

        this.quick_create = options.quick_create;
        this.grouped_by_m2o = options.grouped_by_m2o;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.has_active_field = options.has_active_field;
        this.records_editable = options.records_editable;
        this.records_deletable = options.records_deletable;
        this.relation = options.relation;
        this.offset = 0;
        this.remaining = this.dataset.size() - this.data_records.length;

        this.record_options = _.extend(_.clone(record_options), {
            group_info: this.values,
        });

        var self = this;
        if (group_data.options && group_data.options.group_by_tooltip) {
            this.tooltip_info = _.map(group_data.options.group_by_tooltip, function (key, value, list) {
                return (self.values && self.values[value] && "<div>" +key + "<br>" + self.values[value] + "</div>") || '';
            }).join('');
        } else {
            this.tooltip_info = "";
        }
    },

    start: function() {
        var self = this;
        this.$header = this.$('.o_kanban_header');

        for (var i = 0; i < this.data_records.length; i++) {
            this.add_record(this.data_records[i], {no_update: true});
        }
        this.$header.tooltip();

        if (config.device.size_class > config.device.SIZES.XS) {
            // deactivate sortable in mobile mode.  It does not work anyway,
            // and it breaks horizontal scrolling in kanban views.  Someday, we
            // should find a way to use the touch events to make sortable work.
            this.$el.sortable({
                connectWith: '.o_kanban_group',
                revert: 0,
                delay: 0,
                items: '> .o_kanban_record',
                helper: 'clone',
                cursor: 'move',
                over: function () {
                    self.$el.addClass('o_kanban_hover');
                    self.update_column();
                },
                out: function () {
                    self.$el.removeClass('o_kanban_hover');
                },
                update: function (event, ui) {
                    var record = ui.item.data('record');
                    var index = self.records.indexOf(record);
                    var test2 = $.contains(self.$el[0], record.$el[0]);
                    record.$el.removeAttr('style');  // jqueryui sortable add display:block inline
                    if (index >= 0 && test2) {
                        // resequencing records
                        self.trigger_up('kanban_column_resequence');
                    } else if (index >= 0 && !test2) {
                        // removing record from this column
                        self.records.splice(self.records.indexOf(record), 1);
                        self.dataset.remove_ids([record.id]);
                    } else {
                        // adding record to this column
                        self.records.push(record);
                        record.setParent(self);
                        self.trigger_up('kanban_column_add_record', {record: record});
                    }
                    self.update_column();
                }
            });
        }
        this.update_column();
        this.$el.click(function (event) {
            if (self.$el.hasClass('o_column_folded')) {
                event.preventDefault();
                self.folded = false;
                self.update_column();
            }
        });
    },

    is_empty: function () {
        return !this.records.length;
    },

    add_record: function (data, options) {
        var record = new KanbanRecord(this, data, this.record_options);
        this.records.push(record);
        this.dataset.ids = _.uniq(this.dataset.ids.concat(record.id));
        if (options.position === 'before') {
            record.insertAfter(this.quick_create_widget ? this.quick_create_widget.$el : this.$header);
        } else {
            var $load_more = this.$('.o_kanban_load_more');
            if ($load_more.length) {
                record.insertBefore($load_more);
            } else {
                record.appendTo(this.$el);
            }
        }
        if (!options.no_update) {
            this.update_column();
        }
    },

    get_ids: function () {
        var ids = [];
        this.$('.o_kanban_record').each(function (index, r) {
            ids.push($(r).data('record').id);
        });
        return ids;
    },

    update_column: function () {
        var title = this.folded ? this.title + ' (' + this.dataset.size() + ')' : this.title;
        this.$header.find('.o_column_title').text(title);
        this.$header.find('.o-kanban-count').text(this.records.length);

        this.$el.toggleClass('o_column_folded', this.folded);
        var tooltip;
        if (this.remaining) {
            tooltip = this.records.length + '/' + this.dataset.size() + _t(' records');
        } else {
            tooltip = this.records.length + _t(' records');
        }
        tooltip = '<p>' + tooltip + '</p>' + this.tooltip_info;
        this.$header.tooltip({html: true}).attr('data-original-title', tooltip);
        if (!this.remaining) {
            this.$('.o_kanban_load_more').remove();
        } else {
            this.$('.o_kanban_load_more').html(QWeb.render('KanbanView.LoadMore', {widget:this}))
        }
    },

    archive_records: function(event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: true});
    },

    unarchive_records: function(event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: false});
    },

    delete_column: function (event) {
        event.preventDefault();
        var buttons = [
            {
                text: _t("Ok"),
                classes: 'btn-primary',
                close: true,
                click: this.trigger_up.bind(this, 'kanban_column_delete')
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

    edit_column: function (event) {
        event.preventDefault();
        var dialog = new form_common.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            title: _t("Edit Column"),
        }).open();

        dialog.on('record_saved', this, function () {
            this.trigger_up('kanban_reload');
        });
    },

    delete_record: function (event) {
        event.stopped = false;
        var self = this;
        event.data.after = function cleanup () {
            var index = self.records.indexOf(event.data.record);
            self.records.splice(index, 1);
            self.update_column();
        };
    },

    add_quick_create: function () {
        if (this.quick_create_widget) {
            return;
        }
        var self = this;
        var width = this.records.length ? this.records[0].$el.innerWidth() : this.$el.width() - 8;
        this.quick_create_widget = new RecordQuickCreate(this, width);
        this.quick_create_widget.insertAfter(this.$header);
        this.quick_create_widget.$el.focusout(function () {
            var hasFocus = (self.quick_create_widget.$(':focus').length > 0);
            if (! hasFocus && self.quick_create_widget) {
                self.cancel_quick_create();
            }
        });

    },

    cancel_quick_create: function () {
        this.quick_create_widget.destroy();
        this.quick_create_widget = undefined;
    },

    quick_create_add_record: function (event) {
        this.trigger_up('column_add_record', event.data);
    },

    load_more: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_load_more');
    },

});

return KanbanColumn;

});
