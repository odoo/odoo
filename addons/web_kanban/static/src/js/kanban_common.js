odoo.define('web_kanban.common', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var formats = require('web.formats');
var framework = require('web.framework');
var ProgressBar = require('web.ProgressBar');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;
/**
 * Interface to be implemented by kanban fields.
 *
 */
var FieldInterface = {
    /**
        Constructor.
        - parent: The widget's parent.
        - field: A dictionary giving details about the field, including the current field's value in the
            raw_value field.
        - $node: The field <field> tag as it appears in the view, encapsulated in a jQuery object.
    */
    init: function(parent, field, $node) {},
};

/**
 * Abstract class for classes implementing FieldInterface.
 *
 * Properties:
 *     - value: useful property to hold the value of the field. By default, the constructor
 *     sets value property.
 *
 */
var AbstractField = Widget.extend(FieldInterface, {
    /**
        Constructor that saves the field and $node parameters and sets the "value" property.
    */
    init: function(parent, field, $node) {
        this._super(parent);
        this.field = field;
        this.$node = $node;
        this.options = pyeval.py_eval(this.$node.attr("options") || '{}');
        this.set("value", field.raw_value);
    },
});

var Priority = AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
    },
    prepare_priority: function() {
        var self = this;
        var selection = this.field.selection || [];
        var init_value = selection && selection[0][0] || 0;
        var data = _.map(selection.slice(1), function(element, index) {
            var value = {
                'value': element[0],
                'name': element[1],
                'click_value': element[0],
            };
            if (index === 0 && self.get('value') == element[0]) {
                value.click_value = init_value;
            }
            return value;
        });
        return data;
    },
    renderElement: function() {
        this.record_id = this.parent.id;
        this.priorities = this.prepare_priority();
        var readonly = this.field && this.field.readonly;
        if (readonly){
            this.set('readonly', true);
        }
        this.$el = $(QWeb.render("Priority", {'widget': this}));
        if (!readonly){
            this.$el.find('li').click(this.do_action.bind(this));
        }
    },
    do_action: function(e) {
        var self = this;
        var li = $(e.target).closest( "li" );
        if (li.length) {
            var value = {};
            value[self.name] = String(li.data('value'));
            return self.parent.view.dataset._model.call('write', [[self.record_id], value, self.parent.view.dataset.get_context()]).done(self.reload_record.bind(self.parent));
        }
    },
    reload_record: function() {
        this.do_reload();
    },
});

var KanbanSelection = AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
    },
    prepare_dropdown_selection: function() {
        var self = this;
        var data = [];
        _.map(this.field.selection || [], function(res) {
            var value = {
                'name': res[0],
                'tooltip': res[1],
                'state_name': res[1],
            };
            var leg_opt = self.options && self.options.states_legend || null;
            if (leg_opt && leg_opt[res[0]] && self.parent.group.values && self.parent.group.values[leg_opt[res[0]]]) {
                value['state_name'] = self.parent.group.values[leg_opt[res[0]]];
                value['tooltip'] = self.parent.group.values[leg_opt[res[0]]];
            }
            if (res[0] == 'normal') { value['state_class'] = 'oe_kanban_status'; }
            else if (res[0] == 'done') { value['state_class'] = 'oe_kanban_status oe_kanban_status_green'; }
            else { value['state_class'] = 'oe_kanban_status oe_kanban_status_red'; }
            data.push(value);
        });
        return data;
    },
    renderElement: function() {
        var self = this;
        this.record_id = self.parent.id;
        this.states = self.prepare_dropdown_selection();
        this.$el = $(QWeb.render("KanbanSelection", {'widget': self}));
        this.$el.find('li').click(self.do_action.bind(self));
    },
    do_action: function(e) {
        var self = this;
        var li = $(e.target).closest( "li" );
        if (li.length) {
            var value = {};
            value[self.name] = String(li.data('value'));
            return self.parent.view.dataset._model.call('write', [[self.record_id], value, self.parent.view.dataset.get_context()]).done(self.reload_record.bind(self.parent));
        }
    },
    reload_record: function() {
        this.do_reload();
    },
});


/**
 * Quick creation view.
 *
 * Triggers a single event "added" with a single parameter "name", which is the
 * name entered by the user
 *
 * @class
 * @type {*}
 */
var QuickCreate = Widget.extend({
    template: 'KanbanView.quick_create',

    /**
     * close_btn: If true, the widget will display a "Close" button able to trigger
     * a "close" event.
     */
    init: function(parent, dataset, context, buttons) {
        this._super(parent);
        this._dataset = dataset;
        this._buttons = buttons || false;
        this._context = context || {};
    },
    start: function () {
        var self = this;
        self.$input = this.$el.find('input');
        self.$input.keyup(function(event){
            if(event.keyCode == 13){
                self.quick_add();
            }
        });
        $(".oe_kanban_quick_create").focusout(function (e) {
            var val = self.$el.find('input').val();
            if (/^\s*$/.test(val)) { self.trigger('close'); }
            e.stopImmediatePropagation();
        });
        $(".oe_kanban_quick_create_add", this.$el).click(function () {
            self.quick_add();
            self.focus();
        });
        $(".oe_kanban_quick_create_close", this.$el).click(function (ev) {
            ev.preventDefault();
            self.trigger('close');
        });
        self.$input.keyup(function(e) {
            if (e.keyCode == 27 && self._buttons) {
                self.trigger('close');
            }
        });
    },
    focus: function() {
        this.$el.find('input').focus();
    },
    /**
     * Handles user event from nested quick creation view
     */
    quick_add: function () {
        var self = this;
        var val = this.$input.val();
        if (/^\s*$/.test(val)) { this.$el.remove(); return; }
        this._dataset.call(
            'name_create', [val, new data.CompoundContext(
                    this._dataset.get_context(), this._context)])
            .then(function(record) {
                self.$input.val("");
                self.trigger('added', record[0]);
            }, function(error, event) {
                event.preventDefault();
                return self.slow_create();
            });
    },
    slow_create: function() {
        var self = this;
        var popup = new form_common.SelectCreatePopup(this);
        popup.select_element(
            self._dataset.model,
            {
                title: _t("Create: ") + (this.string || this.name),
                initial_view: "form",
                disable_multiple_selection: true
            },
            [],
            {"default_name": self.$input.val()}
        );
        popup.on("elements_selected", self, function(element_ids) {
            self.$input.val("");
            self.trigger('added', element_ids[0]);
        });
    }
});

var KanbanRecord = Widget.extend({
    template: 'KanbanView.record',

    events: {
        'click .o_kanban_manage_toogle_button': 'toogle_manage_pane',
    },

    init: function (parent, record) {
        this._super(parent);
        this.group = parent;
        this.view = parent.view;
        this.id = null;
        this.set_record(record);
        if (!this.view.state.records[this.id]) {
            this.view.state.records[this.id] = {
                folded: false
            };
        }
        this.state = this.view.state.records[this.id];
        this.fields = {};
    },
    set_record: function(record) {
        var self = this;
        this.id = record.id;
        this.values = {};
        _.each(record, function(v, k) {
            self.values[k] = {
                value: v
            };
        });
        this.record = this.transform_record(record);
    },
    start: function() {
        var self = this;
        this._super();
        this.init_content();
    },
    init_content: function() {
        var self = this;
        self.sub_widgets = [];
        this.$("[data-field_id]").each(function() {
            self.add_widget($(this));
        });
        this.$el.data('widget', this);
        this.bind_events();
    },
    transform_record: function(record) {
        var self = this,
            new_record = {};
        _.each(record, function(value, name) {
            var r = _.clone(self.view.fields_view.fields[name] || {});
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
    renderElement: function() {
        this.qweb_context = {
            record: this.record,
            widget: this,
            read_only_mode: this.view.options.read_only_mode,
        };
        for (var p in this) {
            if (_.str.startsWith(p, 'kanban_')) {
                this.qweb_context[p] = _.bind(this[p], this);
            }
        }
        var $el = QWeb.render(this.template, {
            'widget': this,
            'content': this.view.qweb.render('kanban-box', this.qweb_context)
        });
        this.replaceElement($el);
        this.replace_fields();
    },
    replace_fields: function() {
        var self = this;
        this.$("field").each(function() {
            var $field = $(this);
            var $nfield = $("<span></span");
            var id = _.uniqueId("kanbanfield");
            self.fields[id] = $field;
            $nfield.attr("data-field_id", id);
            $field.replaceWith($nfield);
        });
    },
    add_widget: function($node) {
        var $orig = this.fields[$node.data("field_id")];
        var field = this.record[$orig.attr("name")];
        var type = field.type;
        type = $orig.attr("widget") ? $orig.attr("widget") : type;
        var obj = fields_registry.get(type);
        var widget = new obj(this, field, $orig);
        this.sub_widgets.push(widget);
        widget.replace($node);
    },
    bind_events: function() {
        var self = this;
        this.setup_color_picker();
        this.$el.find('[title]').each(function(){
            $(this).tooltip({
                delay: { show: 500, hide: 0},
                title: function() {
                    var template = $(this).attr('tooltip');
                    if (!self.view.qweb.has_template(template)) {
                        return false;
                    }
                    return self.view.qweb.render(template, self.qweb_context);
                },
            });
        });

        // If no draghandle is found, make the whole card as draghandle (provided one can edit)
        if (!this.$el.find('.oe_kanban_draghandle').length) {
            this.$el.children(':first')
                .toggleClass('oe_kanban_draghandle', this.view.is_action_enabled('edit'));
        }

        this.$el.find('.oe_kanban_action').click(function(ev) {
            ev.preventDefault();
            var $action = $(this),
                type = $action.data('type') || 'button',
                method = 'do_action_' + (type === 'action' ? 'object' : type);
            if ((type === 'edit' || type === 'delete') && ! self.view.is_action_enabled(type)) {
                self.view.open_record(self.id, true);
            } else if (_.str.startsWith(type, 'switch_')) {
                self.view.do_switch_view(type.substr(7));
            } else if (typeof self[method] === 'function') {
                self[method]($action);
            } else {
                self.do_warn("Kanban: no action for type : " + type);
            }
        });

        if (this.$el.find('.oe_kanban_global_click,.oe_kanban_global_click_edit').length) {
            this.$el.on('click', function(ev) {
                if (!ev.isTrigger && !$._data(ev.target, 'events')) {
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
                        self.on_card_clicked(ev);
                    }
                }
            });
        }
    },
    /* actions when user click on the block with a specific class
     *  open on normal view : oe_kanban_global_click
     *  open on form/edit view : oe_kanban_global_click_edit
     */
    on_card_clicked: function(ev) {
        if (this.$el.find('.oe_kanban_global_click').size() > 0 && this.$el.find('.oe_kanban_global_click').data('routing')) {
            framework.redirect(this.$el.find('.oe_kanban_global_click').data('routing') + "/" + this.id);
        }
        else if (this.$el.find('.oe_kanban_global_click_edit').size()>0)
            this.do_action_edit();
        else
            this.do_action_open();
    },
    setup_color_picker: function() {
        var self = this;
        var $el = this.$el.find('ul.oe_kanban_colorpicker');
        if ($el.length) {
            $el.html(QWeb.render('KanbanColorPicker', {
                widget: this
            }));
            $el.on('click', 'a', function(ev) {
                ev.preventDefault();
                var color_field = $(this).parents('.oe_kanban_colorpicker').first().data('field') || 'color';
                var data = {};
                data[color_field] = $(this).data('color');
                self.view.dataset.write(self.id, data, {}).done(function() {
                    self.record[color_field] = $(this).data('color');
                    self.do_reload();
                });
            });
        }
    },
    toogle_manage_pane: function(){
        this.$('.o_kanban_card_content').toggleClass('o_visible o_invisible');
        this.$('.o_kanban_card_manage_pane').toggleClass('o_visible o_invisible');
        this.$('.o_kanban_manage_button_section').toggleClass(this.kanban_color(this.values['color'].value));
    },

    do_action_delete: function($action) {
        var self = this;
        function do_it() {
            return $.when(self.view.dataset.unlink([self.id])).done(function() {
                self.group.remove_record(self.id);
                self.destroy();
            });
        }
        if (this.view.options.confirm_on_delete) {
            if (confirm(_t("Are you sure you want to delete this record ?"))) {
                return do_it();
            }
        } else
            return do_it();
    },
    do_action_edit: function($action) {
        this.view.open_record(this.id, true);
    },
    do_action_open: function($action) {
        this.view.open_record(this.id);
    },
    do_action_object: function ($action) {
        var button_attrs = $action.data();
        var node_context = button_attrs.context || {};
        var context = new data.CompoundContext(node_context);
        context.set_eval_context({
            active_id: this.id,
            active_ids: [this.id],
            active_model: this.view.dataset.model
        });
        var action_data = _.extend({}, button_attrs, {context: context});
        this.view.do_execute_action(action_data, this.view.dataset, this.id, this.do_reload);
    },
    do_action_url: function($action) {
        return framework.redirect($action.attr("href"));
     },
    do_reload: function() {
        var self = this;
        this.view.dataset.read_ids([this.id], this.view.fields_keys.concat(['__last_update'])).done(function(records) {
             _.each(self.sub_widgets, function(el) {
                 el.destroy();
             });
             self.sub_widgets = [];
            if (records.length) {
                self.set_record(records[0]);
                self.renderElement();
                self.init_content();
                self.group.compute_cards_auto_height();
                self.view.postprocess_m2m_tags();
            } else {
                self.destroy();
            }
        });
    },
    kanban_getcolor: function(variable) {
        var index = 0;
        switch (typeof(variable)) {
            case 'string':
                for (var i=0, ii=variable.length; i<ii; i++) {
                    index += variable.charCodeAt(i);
                }
                break;
            case 'number':
                index = Math.round(variable);
                break;
            default:
                return '';
        }
        var color = (index % this.view.number_of_color_schemes);
        return color;
    },
    kanban_color: function(variable) {
        var color = this.kanban_getcolor(variable);
        return color === '' ? '' : 'oe_kanban_color_' + color;
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
    kanban_text_ellipsis: function(s, size) {
        size = size || 160;
        if (!s) {
            return '';
        } else if (s.length <= size) {
            return s;
        } else {
            return s.substr(0, size) + '...';
        }
    },
    kanban_compute_domain: function(domain) {
        return data.compute_domain(domain, this.values);
    }
});


var KanbanGroup = Widget.extend({
    template: 'KanbanView.group_header',
    init: function (parent, records, group, dataset) {
        var self = this;
        this._super(parent);
        this.$has_been_started = $.Deferred();
        this.view = parent;
        this.group = group;
        this.dataset = dataset;
        this.dataset_offset = 0;
        this.value = this.title = this.values = null;
        if (this.group) {
            this.values = group.values;
            this.value = group.get('value');
            this.title = group.get('value');
            if (this.value instanceof Array) {
                this.title = this.value[1];
                this.value = this.value[0];
            }
            var field = this.view.group_by_field;
            if (!_.isEmpty(field)) {
                try {
                    this.title = formats.format_value(group.get('value'), field, false);
                } catch(e) {}
            }
        }

        if (this.title === false) {
            this.title = _t('Undefined');
            this.undefined_title = true;
        }
        var key = this.view.group_by + '-' + this.value;
        if (!this.view.state.groups[key]) {
            this.view.state.groups[key] = {
                folded: group ? group.get('folded') : false
            };
        }
        this.state = this.view.state.groups[key];
        this.$records = null;

        this.records = [];
        this.$has_been_started.done(function() {
            self.do_add_records(records);
        });
    },
    start: function() {
        var self = this,
            def = this._super();
        if (! self.view.group_by) {
            self.$el.addClass("oe_kanban_no_group");
            var QuickCreateClass = self.view.get_quick_create_class();
            self.quick = (new QuickCreateClass(this, self.dataset, {}, false))
                .on('added', self, self.proxy('quick_created'));
            self.quick.replace($(".oe_kanban_no_group_qc_placeholder"));
        }
        this.$records = $(QWeb.render('KanbanView.group_records_container', { widget : this}));
        this.$records.insertBefore(this.view.$el.find('.oe_kanban_groups_records td:last'));

        this.$el.on('click', '.oe_kanban_group_dropdown li a', function(ev) {
            var fn = 'do_action_' + $(ev.target).data().action;
            if (typeof(self[fn]) === 'function') {
                self[fn]($(ev.target));
            }
        });

        this.$el.find('.oe_kanban_add').click(function () {
            if (self.view.quick) {
                self.view.quick.trigger('close');
            }
            if (self.quick) {
                return false;
            }
            self.view.$el.find('.oe_view_nocontent').hide();
            var ctx = {};
            ctx['default_' + self.view.group_by] = self.value;
            self.quick = new (self.view.get_quick_create_class())(this, self.dataset, ctx, true)
                .on('added', self, self.proxy('quick_created'))
                .on('close', self, function() {
                    self.view.$el.find('.oe_view_nocontent').show();
                    this.quick.destroy();
                    delete self.view.quick;
                    delete this.quick;
                });
            self.quick.appendTo($(".oe_kanban_group_list_header", self.$records));
            self.quick.focus();
            self.view.quick = self.quick;
        });
        // Add bounce effect on image '+' of kanban header when click on empty space of kanban grouped column.
        this.$records.on('click', '.oe_kanban_show_more', this.do_show_more);
        if (this.state.folded) {
            this.do_toggle_fold();
        }
        this.$el.data('widget', this);
        this.$records.data('widget', this);
        this.$has_been_started.resolve();
        var add_btn = this.$el.find('.oe_kanban_add');
        add_btn.tooltip({delay: { show: 500, hide:1000 }});
        this.$records.find(".oe_kanban_column_cards").click(function (ev) {
            if (ev.target == ev.currentTarget) {
                if (!self.state.folded) {
                    add_btn.openerpBounce();
                }
            }
        });
        this.is_started = true;
        this.fetch_tooltip();
        return def;
    },
    /*
     * Form the tooltip, based on optional group_by_tooltip on the grouping field.
     * This function goes through the arch of the view, finding the declaration
     * of the field used to group. If group_by_tooltip is defined, use the previously
     * computed values of the group to form the tooltip. */
    fetch_tooltip: function() {
        var self = this;
        if (! this.group)
            return;
        var options = null;
        var recurse = function(node) {
            if (node.tag === "field" && node.attrs.name == self.view.group_by) {
                options = pyeval.py_eval(node.attrs.options || '{}');
                return;
            }
            _.each(node.children, function(child) {
                recurse(child);
            });
        };
        recurse(this.view.fields_view.arch);
        if (options && options.group_by_tooltip) {
            this.tooltip = _.compact(
                _.union(
                    [this.title],
                    _.map(
                        options.group_by_tooltip,
                        function (key, value, list) { return self.values && self.values[value] && (key + "\n" + self.values[value]) || ''; }))
            ).join('\n\n');
            this.$(".oe_kanban_group_title_text").attr("title", this.tooltip || this.title || "");
        }
    },
    compute_cards_auto_height: function() {
        // oe_kanban_no_auto_height is an empty class used to disable this feature
        if (!this.view.group_by) {
            var min_height = 0;
            var els = [];
            _.each(this.records, function(r) {
                var $e = r.$el.children(':first:not(.oe_kanban_no_auto_height)').css('min-height', 0);
                if ($e.length) {
                    els.push($e[0]);
                    min_height = Math.max(min_height, $e.outerHeight());
                }
            });
            $(els).css('min-height', min_height);
        }
    },
    destroy: function() {
        this._super();
        if (this.$records) {
            this.$records.remove();
        }
    },
    do_show_more: function(evt) {
        var self = this;
        var ids = self.view.dataset.ids.slice(0);
        return this.dataset.read_slice(this.view.fields_keys.concat(['__last_update']), {
            'limit': self.view.limit,
            'offset': self.dataset_offset += self.view.limit
        }).then(function(records) {
            self.view.dataset.ids = ids.concat(_.difference(self.dataset.ids, ids));
            self.do_add_records(records);
            self.compute_cards_auto_height();
            self.view.postprocess_m2m_tags();
            return records;
        });
    },
    do_add_records: function(records, prepend) {
        var self = this;
        var $list_header = this.$records.find('.oe_kanban_group_list_header');
        var $show_more = this.$records.find('.oe_kanban_show_more');
        var $cards = this.$records.find('.oe_kanban_column_cards');

        _.each(records, function(record) {
            var rec = new KanbanRecord(self, record);
            if (!prepend) {
                rec.appendTo($cards);
                self.records.push(rec);
            } else {
                rec.prependTo($cards);
                self.records.unshift(rec);
            }
        });
        if ($show_more.length) {
            var size = this.dataset.size();
            $show_more.toggle(this.records.length < size).find('.oe_kanban_remaining').text(size - this.records.length);
        }
    },
    remove_record: function(id, remove_from_dataset) {
        for (var i = 0; i < this.records.length; i++) {
            if (this.records[i]['id'] === id) {
                this.records.splice(i, 1);
                i--;
            }
        }
    },
    do_toggle_fold: function(compute_width) {
        this.$el.add(this.$records).toggleClass('oe_kanban_group_folded');
        this.state.folded = this.$el.is('.oe_kanban_group_folded');
        this.$("ul.oe_kanban_group_dropdown li a[data-action=toggle_fold]").text((this.state.folded) ? _t("Unfold") : _t("Fold"));
    },
    do_action_toggle_fold: function() {
        this.do_toggle_fold();
    },
    do_action_edit: function() {
        var self = this;
        self.do_action({
            res_id: this.value,
            name: _t("Edit column"),
            res_model: self.view.group_by_field.relation,
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            target: "new",
            flags: {
                action_buttons: true,
                headless: true,
            }
        });
        // to do : remove this horrible hack
        var am = web_client.action_manager;
        var form = am.dialog_widget.views.form.controller;
        form.on("on_button_cancel", am.dialog, function() { return am.dialog.$dialog_box.modal('hide'); });
        form.on('record_saved', self, function() {
            am.dialog.$dialog_box.modal('hide');
            self.view.do_reload();
        });
    },
    do_action_delete: function() {
        var self = this;
        if (confirm(_t("Are you sure to remove this column ?"))) {
            (new data.DataSet(self, self.view.group_by_field.relation)).unlink([self.value]).done(function(r) {
                self.view.do_reload();
            });
        }
    },
    do_save_sequences: function() {
        var self = this;
        if (_.indexOf(this.view.fields_keys, 'sequence') > -1) {
            var new_sequence = _.pluck(this.records, 'id');
            self.view.dataset.resequence(new_sequence);
        }
    },
    /**
     * Handles a newly created record
     *
     * @param {id} id of the newly created record
     */
    quick_created: function (record) {
        var id = record, self = this;
        self.view.remove_no_result();
        self.trigger("add_record");
        this.dataset.read_ids([id], this.view.fields_keys)
            .done(function (records) {
                self.view.dataset.ids.push(id);
                self.do_add_records(records, true);
            });
    },
    highlight: function(show){
        if(show){
            this.$el.addClass('oe_kanban_column_higlight');
            this.$records.addClass('oe_kanban_column_higlight');
        }else{
            this.$el.removeClass('oe_kanban_column_higlight');
            this.$records.removeClass('oe_kanban_column_higlight');
        }
    }
});


/**
 * Kanban widgets: ProgressBar
 * options
 * - editable: boolean if current_value is editable
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - title: title of the gauge, displayed on top of the gauge
 * - on_change: action to call when cliking and setting a value
 */
var KanbanProgressBar = AbstractField.extend({
    events: {
        'click': function() {
            if(this.progressbar.readonly) {
                this.toggle_progressbar();
            }
        }
    },

    init: function (parent, field, node) {
        this._super(parent, field, node);

        var record = this.getParent().record;
        this.progressbar = new ProgressBar(this, {
            readonly: true,
            value: record[this.options.current_value].raw_value,
            max_value: record[this.options.max_value].raw_value,
            title: this.options.title
        });

        this.readonly = !this.options.editable;
        this.on_change = this.options.on_change;
    },

    start: function () {
        var self = this;

        var def = this.progressbar.appendTo('<div>').done(function() {
            self.progressbar.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.progressbar.$el);
        });

        return $.when(this._super(), def).then(function() {
            if(!self.readonly) {
                var parent = self.getParent();
                self.progressbar.on('change:value', self, function(e) {
                    var value = this.progressbar.get('value') || 0;
                    if(!isNaN(value)) {
                        parent.view.dataset.call(this.on_change, [parent.id, value]).then(function() {
                            self.toggle_progressbar();
                        });
                    } 
                });
            }
        });
    },

    toggle_progressbar: function() {
        this.progressbar.readonly = !this.progressbar.readonly;
        var $div = $('<div/>').insertAfter(this.$el);
        this.progressbar.replace($div);
        this.setElement(this.progressbar.$el);
    },
});

var fields_registry = new Registry();

fields_registry
    .add('priority', Priority)
    .add('kanban_state_selection', KanbanSelection)
    .add("progress", KanbanProgressBar);


return {
    AbstractField: AbstractField,
    registry: fields_registry,
    QuickCreate: QuickCreate,
    KanbanRecord: KanbanRecord,
    KanbanGroup: KanbanGroup,
};

});
