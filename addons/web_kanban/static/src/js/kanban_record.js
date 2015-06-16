odoo.define('web_kanban.Record', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var formats = require('web.formats');
var framework = require('web.framework');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');
var kanban_widgets = require('web_kanban.widgets');

var QWeb = core.qweb;
var fields_registry = kanban_widgets.registry;

var KanbanRecord = Widget.extend({
    template: 'KanbanView.record',

    events: {
        'click .oe_kanban_action': 'on_kanban_action_clicked',
        'click .o_kanban_manage_toggle_button': 'toggle_manage_pane',
    },

    custom_events: {
        'kanban_update_record': 'update_record',
    },

    init: function (parent, record, options) {
        this._super(parent);

        this.fields = options.fields;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.draggable = options.draggable;
        this.read_only_mode = options.read_only_mode;
        this.model = options.model;
        this.group_info = options.group_info;
        this.qweb = options.qweb;
        this.sub_widgets = [];

        this.init_content(record);
    },

    init_content: function (record) {
        var self = this;
        this.id = record.id;
        this.values = {};
        _.each(record, function(v, k) {
            self.values[k] = {
                value: v
            };
        });
        this.record = this.transform_record(record);
        var qweb_context = {
            record: this.record,
            widget: this,
            read_only_mode: this.read_only_mode,
        };
        for (var p in this) {
            if (_.str.startsWith(p, 'kanban_')) {
                qweb_context[p] = _.bind(this[p], this);
            }
        }
        this.content = this.qweb.render('kanban-box', qweb_context);
    },

    add_widgets: function () {
        var self = this;
        this.$("field").each(function() {
            var $field = $(this);
            var field = self.record[$field.attr("name")];
            var type = $field.attr("widget") || field.type;
            var Widget = fields_registry.get(type);
            var widget = new Widget(self, field, $field);
            widget.replace($field);
            self.sub_widgets.push(widget);
        });
    },

    start: function() {
        this.add_widgets();
    },

    renderElement: function () {
        this._super();
        this.setup_color_picker();
        this.$el.addClass('o_kanban_record');
        this.$el.data('record', this);
        if (this.$el.hasClass('oe_kanban_global_click') || this.$el.hasClass('oe_kanban_global_click_edit')) {
            this.$el.on('click', this.proxy('on_global_click'));
        }
    },
    transform_record: function(record) {
        var self = this;
        var new_record = {};
        _.each(record, function(value, name) {
            var r = _.clone(self.fields[name] || {});
            if ((r.type === 'date' || r.type === 'datetime') && value) {
                r.raw_value = time.auto_str_to_date(value);
            } else {
                r.raw_value = value;
            }
            r.value = formats.format_value(value, r);
            new_record[name] = r;
        });
        return new_record;
    },

    update: function (record) {
        _.invoke(this.sub_widgets, 'destroy');
         this.sub_widgets = [];
        this.init_content(record);
        this.renderElement();
        this.add_widgets();
    },

    kanban_image: function(model, field, id, cache, options) {
        options = options || {};
        var url;
        if (this.record[field] && this.record[field].value && !utils.is_bin_size(this.record[field].value)) {
            url = 'data:image/png;base64,' + this.record[field].value;
        } else if (this.record[field] && ! this.record[field].value) {
            url = "/web/static/src/img/placeholder.png";
        } else {
            id = JSON.stringify(id);
            if (options.preview_image)
                field = options.preview_image;
            url = session.url('/web/binary/image', {model: model, field: field, id: id});
            if (cache !== undefined) {
                // Set the cache duration in seconds.
                url += '&cache=' + parseInt(cache, 10);
            }
        }
        return url;
    },

    kanban_getcolor: function(variable) {
        if (typeof(variable) === 'number') {
            return Math.round(variable) % 10;
        }
        if (typeof(variable) === 'string') {
            var index = 0;
            for (var i=0; i<variable.length; i++) {
                index += variable.charCodeAt(i);
            }
            return index % 10;
        }
        return 0;
    },

    kanban_color: function(variable) {
        var color = this.kanban_getcolor(variable);
        return 'oe_kanban_color_' + color;
    },

    on_global_click: function (ev) {
        if ($(ev.target).parents('.o_dropdown_kanban').length) {
            return;
        }
        if (!ev.isTrigger) {
            var trigger = true;
            var elem = ev.target;
            var ischild = true;
            var children = [];
            while (elem) {
                var events = $._data(elem, 'events');
                if (elem == ev.currentTarget) {
                    ischild = false;
                }
                if (ischild) {
                    children.push(elem);
                    if (events && events.click) {
                        // do not trigger global click if one child has a click event registered
                        trigger = false;
                    }
                }
                if (trigger && events && events.click) {
                    _.each(events.click, function(click_event) {
                        if (click_event.selector) {
                            // For each parent of original target, check if a
                            // delegated click is bound to any previously found children
                            _.each(children, function(child) {
                                if ($(child).is(click_event.selector)) {
                                    trigger = false;
                                }
                            });
                        }
                    });
                }
                elem = elem.parentElement;
            }
            if (trigger) {
                this.on_card_clicked(ev);
            }
        }
    },

    /* actions when user click on the block with a specific class
     *  open on normal view : oe_kanban_global_click
     *  open on form/edit view : oe_kanban_global_click_edit
     */
    on_card_clicked: function() {
        if (this.$el.hasClass('oe_kanban_global_click_edit') && this.$el.data('routing')) {
            framework.redirect(this.$el.data('routing') + "/" + this.id);
        } else if (this.$el.hasClass('oe_kanban_global_click_edit')) {
            this.trigger_up('kanban_record_edit', {id: this.id});
        } else {
            this.trigger_up('kanban_record_open', {id: this.id});
        }
    },

    toggle_manage_pane: function(event){
        event.preventDefault();
        this.$('.o_kanban_card_content').toggleClass('o_visible o_invisible');
        this.$('.o_kanban_card_manage_pane').toggleClass('o_visible o_invisible');
        this.$('.o_kanban_manage_button_section').toggleClass(this.kanban_color((this.values['color'] && this.values['color'].value) || 0));
    },

    on_kanban_action_clicked: function (ev) {
        ev.preventDefault();

        var $action = $(ev.currentTarget);
        var type = $action.data('type') || 'button';

        switch (type) {
            case 'edit':
                this.trigger_up('kanban_record_edit', {id: this.id});
                break;
            case 'open':
                this.trigger_up('kanban_record_open', {id: this.id});
                break;
            case 'delete':
                this.trigger_up('kanban_record_delete', {record: this});
                break;
            case 'action':
            case 'object':
                this.trigger_up('kanban_do_action', $action.data());
                break;
            default:
                this.do_warn("Kanban: no action for type : " + type);
        }
    },

    kanban_compute_domain: function(domain) {
        return data.compute_domain(domain, this.values);
    },

    update_record: function (event) {
        this.trigger_up('kanban_record_update', event.data);
    },

    setup_color_picker: function() {
        var self = this;
        var $colorpicker = this.$('ul.oe_kanban_colorpicker');
        if (!$colorpicker.length) {
            return;
        }
        $colorpicker.html(QWeb.render('KanbanColorPicker', {
            widget: this
        }));
        $colorpicker.on('click', 'a', function(ev) {
            ev.preventDefault();
            var color_field = $colorpicker.data('field') || 'color';
            var data = {};
            data[color_field] = $(this).data('color');
            self.trigger_up('kanban_record_update', data);
        });
    },

});

return KanbanRecord;

});
