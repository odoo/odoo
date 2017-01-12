odoo.define('web.form_widgets', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var datepicker = require('web.datepicker');
var dom_utils = require('web.dom_utils');
var Priority = require('web.Priority');
var ProgressBar = require('web.ProgressBar');
var Dialog = require('web.Dialog');
var DomainSelector = require("web.DomainSelector");
var DomainSelectorDialog = require("web.DomainSelectorDialog");
var common = require('web.form_common');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');

var _t = core._t;
var QWeb = core.qweb;

var WidgetButton = common.FormWidget.extend({
    template: 'WidgetButton',
    init: function(field_manager, node) {
        node.attrs.type = node.attrs['data-button-type'];
        this._super(field_manager, node);
        this.force_disabled = false;
        this.string = (this.node.attrs.string || '').replace(/_/g, '');
        if (JSON.parse(this.node.attrs.default_focus || "0")) {
            // TODO fme: provide enter key binding to widgets
            this.view.default_focus_button = this;
        }
        if (this.node.attrs.icon) {
            this.fa_icon = this.node.attrs.icon.indexOf('fa-') === 0;
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.view.on('view_content_has_changed', this, this.check_disable);
        this.check_disable();
        this.$el.click(this.on_click);
        if (this.node.attrs.help || session.debug) {
            this.do_attach_tooltip();
        }
        this.setupFocus(this.$el);
    },
    on_click: function() {
        var self = this;
        if (this.view.is_disabled) {
            return;
        }
        this.force_disabled = true;
        this.check_disable();
        this.view.disable_button();
        this.execute_action().always(function() {
            self.view.enable_button();
            self.force_disabled = false;
            self.check_disable();
            if (self.$el.hasClass('o_wow')) {
                self.show_wow();
            }
        });
    },
    execute_action: function() {
        var self = this;
        var exec_action = function() {
            if (self.node.attrs.confirm) {
                var def = $.Deferred();
                Dialog.confirm(self, self.node.attrs.confirm, { confirm_callback: self.on_confirmed })
                      .on("closed", null, function() { def.resolve(); });
                return def.promise();
            } else {
                return self.on_confirmed();
            }
        };
        if (!this.node.attrs.special) {
            return this.view.recursive_save().then(exec_action);
        } else {
            return exec_action();
        }
    },
    on_confirmed: function() {
        var self = this;
        var context = this.build_context();
        return this.view.do_execute_action(
            _.extend({}, this.node.attrs, {context: context}),
            this.view.dataset, this.view.datarecord.id, function (reason) {
                if (!_.isObject(reason)) {
                    self.view.recursive_reload();
                }
            }).fail(function () {
                self.view.recursive_reload();
            });
    },
    check_disable: function() {
        var disabled = (this.force_disabled || !this.view.is_interactible_record());
        this.$el.prop('disabled', disabled);
        this.$el.css('color', disabled ? 'grey' : '');
    },
    show_wow: function() {
        var class_to_add = 'o_wow_thumbs';
        if (Math.random() > 0.9) {
            var other_classes = ['o_wow_peace', 'o_wow_heart'];
            class_to_add = other_classes[Math.floor(Math.random()*other_classes.length)];
        }

        var $body = $('body');
        $body.addClass(class_to_add);
        setTimeout(function() {
            $body.removeClass(class_to_add);
        }, 1000);
    }
});

var FieldChar = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: 'FieldChar',
    events: {
        'change': 'store_dom_value',
    },
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.password = this.node.attrs.password === 'True' || this.node.attrs.password === '1';
    },
    initialize_content: function() {
        if(!this.get('effective_readonly') && !this.$input) {
            this.$input = this.$el;
        }
        this.setupFocus(this.$el);
    },
    destroy_content: function() {
        this.$input = undefined;
    },
    store_dom_value: function () {
        if (this.$input && this.is_syntax_valid()) {
            this.internal_set_value(this.parse_value(this.$input.val()));
        }
    },
    commit_value: function () {
        this.store_dom_value();
        return this._super();
    },
    render_value: function() {
        var show_value = this.format_value(this.get('value'), '');
        if (this.$input) {
            this.$input.val(show_value);
        } else {
            if (this.password) {
                show_value = new Array(show_value.length + 1).join('*');
            }
            this.$el.text(show_value);
        }
    },
    is_syntax_valid: function() {
        if (this.$input) {
            try {
                this.parse_value(this.$input.val(), '');
            } catch(e) {
                return false;
            }
        }
        return true;
    },
    parse_value: function(val, def) {
        return formats.parse_value(val, this, def);
    },
    format_value: function(val, def) {
        return formats.format_value(val, this, def);
    },
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    focus: function() {
        if (this.$input) {
            return this.$input.focus();
        }
        return false;
    },
});

var KanbanSelection = common.AbstractField.extend({
    template: "FormSelection",
    events: {
        'click a': function(e) {
            e.preventDefault();
        },
        'mouseup a': function(e) {
            e.stopPropagation();
        },
        'click li': 'set_kanban_selection'
    },
    start: function () {
        // hook on form view content changed: recompute the states, because it may be related to the current stage
        this.view.on('view_content_has_changed', this, function () {
            this.render_value();
        });
        return this._super();
    },
    prepare_dropdown_selection: function() {
        var self = this;
        var _data = [];
        var current_stage_id = self.view.datarecord.stage_id[0];
        var stage_data = {
            id: current_stage_id,
            legend_normal: self.view.datarecord.legend_normal || undefined,
            legend_blocked : self.view.datarecord.legend_blocked || undefined,
            legend_done: self.view.datarecord.legend_done || undefined,
        };
        _.map(self.field.selection || [], function(selection_item) {
            var value = {
                'name': selection_item[0],
                'tooltip': selection_item[1],
            };
            if (selection_item[0] === 'normal') {
                value.state_name = stage_data.legend_normal ? stage_data.legend_normal : selection_item[1];
            } else if (selection_item[0] === 'done') {
                value.state_class = 'oe_kanban_status_green';
                value.state_name = stage_data.legend_done ? stage_data.legend_done : selection_item[1];
            } else {
                value.state_class = 'oe_kanban_status_red';
                value.state_name = stage_data.legend_blocked ? stage_data.legend_blocked : selection_item[1];
            }
            _data.push(value);
        });
        return _data;
    },
    render_value: function() {
        this._super();
        this.states = this.prepare_dropdown_selection();
        var self = this;

        // Adapt "FormSelection"
        var current_state = _.find(this.states, function(state) {
            return state.name === self.get('value');
        });
        this.$('.oe_kanban_status')
            .removeClass('oe_kanban_status_red oe_kanban_status_green')
            .addClass(current_state.state_class);

        // Render "FormSelection.Items" and move it into "FormSelection"
        var $items = $(QWeb.render('FormSelection.items', {
            states: _.without(this.states, current_state)
        }));
        var $dropdown = this.$el.find('.dropdown-menu');
        $dropdown.children().remove(); // remove old items
        $items.appendTo($dropdown);
    },
    /* setting the value: in view mode, perform an asynchronous call and reload
    the form view; in edit mode, use set_value to save the new value that will
    be written when saving the record. */
    set_kanban_selection: function (ev) {
        var self = this;
        ev.preventDefault();
        var li = $(ev.target).closest('li');
        if (li.length) {
            var value = String(li.data('value'));
            if (this.view.get('actual_mode') === 'view') {
                var write_values = {};
                write_values[self.name] = value;
                return this.view.dataset._model.call(
                    'write', [
                        [this.view.datarecord.id],
                        write_values,
                        self.view.dataset.get_context()
                    ]).done(self.reload_record.bind(self));
            }
            else {
                return this.set_value(value);
            }
        }
    },
    reload_record: function() {
        this.view.reload();
    },
});

var FieldPriority = common.AbstractField.extend({
    events: {
        'mouseup': function(e) {
            e.stopPropagation();
        },
    },
    start: function() {
        this.priority = new Priority(this, {
            readonly: this.get('readonly'),
            value: this.get('value'),
            values: this.field.selection || [],
        });

        this.priority.on('update', this, function(update) {
            /* setting the value: in view mode, perform an asynchronous call and reload
            the form view; in edit mode, use set_value to save the new value that will
            be written when saving the record. */
            var view = this.view;
            if(view.get('actual_mode') === 'view') {
                var write_values = {};
                write_values[this.name] = update.value;
                view.dataset._model.call('write', [
                    [view.datarecord.id],
                    write_values,
                    view.dataset.get_context()
                ]).done(function() {
                    view.reload();
                });
            } else {
                this.set_value(update.value);
            }
        });

        this.on('change:readonly', this, function() {
            this.priority.readonly = this.get('readonly');
            var $div = $('<div/>').insertAfter(this.$el);
            this.priority.replace($div);
            this.setElement(this.priority.$el);
        });

        var self = this;
        return $.when(this._super(), this.priority.appendTo('<div>').then(function() {
            self.priority.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.priority.$el);
        }));
    },
    render_value: function() {
        this.priority.set_value(this.get('value'));
    },
});

var FieldID = FieldChar.extend({
    process_modifiers: function () {
        this._super();
        this.set({ readonly: true });
    },
});

var FieldEmail = FieldChar.extend({
    template: 'FieldEmail',
    prefix: 'mailto',
    init: function() {
        this._super.apply(this, arguments);
        this.clickable = true;
    },
    render_value: function() {
        this._super();
        if (this.get("effective_readonly") && this.clickable) {
            this.$el.attr('href', this.prefix + ':' + this.get('value'));
        }
    }
});

var FieldUrl = FieldEmail.extend({
    render_value: function() {
        this._super();
        if(this.get("effective_readonly")) {
            var tmp = this.get('value');
            var s = /(\w+):(.+)|^\.{0,2}\//.exec(tmp);
            if (!s) {
                tmp = "http://" + this.get('value');
            }
            var text = this.get('value') ? this.node.attrs.text || tmp : '';
            this.$el.attr('href', tmp).text(text);
        }
    }
});

var FieldFloat = FieldChar.extend({
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.internal_set_value(0);
        if (this.node.attrs.digits) {
            this.digits = this.node.attrs.digits;
        } else {
            this.digits = this.field.digits;
        }
    },
    initialize_content: function() {
        this._super();
        this.$el.addClass('o_form_field_number');
    },
    set_value: function(value_) {
        if (value_ === false || value_ === undefined) {
            value_ = 0; // As in GTK client, floats default to 0
        }
        if (this.digits !== undefined && this.digits.length === 2) {
            value_ = utils.round_decimals(value_, this.digits[1]);
        }
        this._super(value_);
    }
});

/// The "Domain" field allows the user to construct a technical-prefix domain thanks to
/// a tree-like interface and see the selected records in real time.
/// In debug mode, an input is also there to be able to enter the prefix char domain
/// directly (or to build advanced domains the tree-like interface does not allow to).
var FieldDomain = common.AbstractField.extend(common.ReinitializeFieldMixin).extend({
    template: "FieldDomain",
    events: {
        "click .o_domain_show_selection_button": function (e) {
            e.preventDefault();
            this._showSelection();
        },
        "click .o_form_field_domain_dialog_button": function (e) {
            e.preventDefault();
            this.openDomainDialog();
        },
    },
    custom_events: {
        "domain_changed": function (e) {
            if (this.options.in_dialog) return;
            this.set_value(this.domainSelector.getDomain(), true);
        },
        "domain_selected": function (e) {
            this.set_value(e.data.domain);
        },
    },
    init: function () {
        this._super.apply(this, arguments);

        this.valid = true;
        this.debug = session.debug;
        this.options = _.defaults(this.options || {}, {
            in_dialog: false,
            model: undefined, // this option is mandatory !
            fs_filters: {}, // Field selector filters (to only show a subset of available fields @see FieldSelector)
        });
    },
    start: function() {
        this.model = _get_model.call(this); // TODO get the model another way ?
        this.field_manager.on("view_content_has_changed", this, function () {
            var currentModel = this.model;
            this.model = _get_model.call(this);
            if (currentModel !== this.model) {
                this.render_value();
            }
        });

        return this._super.apply(this, arguments);

        function _get_model() {
            if (this.field_manager.fields[this.options.model]) {
                return this.field_manager.get_field_value(this.options.model);
            }
            return this.options.model;
        }
    },
    initialize_content: function () {
        this._super.apply(this, arguments);
        this.$panel = this.$(".o_form_field_domain_panel");
        this.$showSelectionButton = this.$panel.find(".o_domain_show_selection_button");
        this.$recordsCountDisplay = this.$showSelectionButton.find(".o_domain_records_count");
        this.$errorMessage = this.$panel.find(".o_domain_error_message");
        this.$modelMissing = this.$(".o_domain_model_missing");
    },
    set_value: function (value, noDomainSelectorRender) {
        this._noDomainSelectorRender = !!noDomainSelectorRender;
        this._super.apply(this, arguments);
        this._noDomainSelectorRender = false;
    },
    render_value: function() {
        this._super.apply(this, arguments);

        // If there is no set model, the field should only display the corresponding error message
        this.$panel.toggleClass("o_hidden", !this.model);
        this.$modelMissing.toggleClass("o_hidden", !!this.model);
        if (!this.model) {
            if (this.domainSelector) {
                this.domainSelector.destroy();
                this.domainSelector = undefined;
            }
            return;
        }

        var domain = pyeval.eval("domain", this.get("value") || "[]");

        // Recreate domain widget with new domain value
        if (!this._noDomainSelectorRender) {
            if (this.domainSelector) {
                this.domainSelector.destroy();
            }
            this.domainSelector = new DomainSelector(this, this.model, domain, {
                readonly: this.get("effective_readonly") || this.options.in_dialog,
                fs_filters: this.options.fs_filters,
                debugMode: session.debug,
            });
            this.domainSelector.prependTo(this.$el);
        }

        // Show number of selected records
        new Model(this.model).call("search_count", [domain], {
            context: this.build_context(),
        }).then((function (data) {
            this.valid = true;
            return data;
        }).bind(this), (function (error, e) {
            e.preventDefault();
            this.valid = false;
        }).bind(this)).always((function (data) {
            this.$recordsCountDisplay.text(data || 0);
            this.$showSelectionButton.toggleClass("hidden", !this.valid);
            this.$errorMessage.toggleClass("hidden", this.valid);
        }).bind(this));
    },
    is_syntax_valid: function() {
        return this.field_manager.get("actual_mode") === "view" || this.valid;
    },
    _showSelection: function() {
        return new common.SelectCreateDialog(this, {
            title: _t("Selected records"),
            res_model: this.model,
            domain: this.get("value") || "[]",
            no_create: true,
            readonly: true,
            disable_multiple_selection: true,
        }).open();
    },
    openDomainDialog: function () {
        new DomainSelectorDialog(this, this.model, this.get("value") || "[]", {
            readonly: this.get("effective_readonly"),
            fs_filters: this.options.fs_filters,
            debugMode: session.debug,
        }).open();
    },
});

var FieldDate = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    tagName: "span",
    className: "o_form_field_date",
    build_widget: function() {
        return new datepicker.DateWidget(this);
    },
    initialize_content: function() {
        if (this.datewidget) {
            this.datewidget.destroy();
            this.datewidget = undefined;
        }

        if (!this.get("effective_readonly")) {
            this.datewidget = this.build_widget();
            this.datewidget.on('datetime_changed', this, function() {
                this.internal_set_value(this.datewidget.get_value());
            });

            var self = this;
            this.datewidget.appendTo('<div>').done(function() {
                self.datewidget.$el.addClass(self.$el.attr('class'));
                self.replaceElement(self.datewidget.$el);
                self.datewidget.$input.addClass('o_form_input');
                self.setupFocus(self.datewidget.$input);
            });
        }
    },
    render_value: function() {
        if (this.get("effective_readonly")) {
            this.$el.text(formats.format_value(this.get('value'), this, ''));
        } else {
            this.datewidget.set_value(this.get('value'));
        }
    },
    is_syntax_valid: function() {
        return this.get("effective_readonly") || !this.datewidget || this.datewidget.is_valid();
    },
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    focus: function() {
        if (!this.get("effective_readonly")) {
            return this.datewidget.$input.focus();
        }
        return false;
    },
});

var FieldDatetime = FieldDate.extend({
    build_widget: function() {
        return new datepicker.DateTimeWidget(this);
    },
});

var FieldText = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: 'FieldText',
    events: {
        'keyup': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                e.stopPropagation();
            }
        },
        'keypress': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                e.stopPropagation();
            }
        },
        'change': 'store_dom_value',
    },
    initialize_content: function() {
        if (!this.get("effective_readonly")) {
            this.auto_sized = false;
            this.setupFocus(this.$el);
        }
    },
    commit_value: function () {
        if (!this.get("effective_readonly")) {
            this.store_dom_value();
        }
        return this._super();
    },
    store_dom_value: function () {
        this.internal_set_value(formats.parse_value(this.$el.val(), this));
    },
    render_value: function() {
        if (this.get("effective_readonly")) {
            var txt = this.get("value") || '';
            this.$el.text(txt);
        } else {
            var show_value = formats.format_value(this.get('value'), this, '');
            this.$el.val(show_value);
            dom_utils.autoresize(this.$el, {parent: this});
        }
    },
    is_syntax_valid: function() {
        if (!this.get("effective_readonly")) {
            try {
                formats.parse_value(this.$el.val(), this, '');
            } catch(e) {
                return false;
            }
        }
        return true;
    },
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    focus: function($el) {
        if(!this.get("effective_readonly")) {
            return this.$el.focus();
        }
        return false;
    },
    set_dimensions: function(height, width) {
        this.$el.css({
            width: width,
            minHeight: height,
        });
    },
});

var FieldBoolean = common.AbstractField.extend({
    template: 'FieldBoolean',
    events: {
        'click': function() {
            this.internal_set_value(this.$checkbox.prop('checked'));
        }
    },
    start: function() {
        this.$checkbox = this.$('input');

        this.$checkbox.prop('disabled', this.get("effective_readonly"));
        this.on("change:effective_readonly", this, function() {
            this.$checkbox.prop('disabled', this.get("effective_readonly"));
        });

        this.setupFocus(this.$checkbox);

        return this._super();
    },
    render_value: function() {
        this.$checkbox.prop('checked', this.get('value'));
    },
    focus: function() {
        return this.$checkbox.focus();
    },
    set_dimensions: function(height, width) {}, // Checkboxes have a fixed height and width (even in list editable)
    is_false: function() {
        return false;
    },
});

/**
    This widget is intended to be used on stat button boolean fields.
    It is a read-only field that will display a simple string "<label of value>".
*/
var FieldBooleanButton = common.AbstractField.extend({
    className: 'o_stat_info',
    init: function() {
        this._super.apply(this, arguments);
        switch (this.options["terminology"]) {
            case "active":
                this.string_true = _t("Active");
                this.hover_true = _t("Deactivate");
                this.string_false = _t("Inactive");
                this.hover_false = _t("Activate");
                break;
            case "archive":
                this.string_true = _t("Active");
                this.hover_true = _t("Archive");
                this.string_false = _t("Archived");
                this.hover_false = _t("Restore");
                break;
            default:
                var terms = typeof this.options["terminology"] === 'string' ? {} : this.options["terminology"];
                this.string_true = _t(terms.string_true || "On");
                this.hover_true = _t(terms.hover_true || terms.string_false || "Switch Off");
                this.string_false = _t(terms.string_false || "Off");
                this.hover_false = _t(terms.hover_false || terms.string_true || "Switch On");
        }
    },
    render_value: function() {
        this._super();
        this.$el.html(QWeb.render("BooleanButton", {widget: this}));
    },
    is_false: function() {
        return false;
    },
});

// The progressbar field expects a float from 0 to 100.
var FieldProgressBar = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    initialize_content: function() {
        if(this.progressbar) {
            this.progressbar.destroy();
        }

        this.progressbar = new ProgressBar(this, {
            readonly: this.get('effective_readonly'),
            edit_on_click: true,
            value: this.get('value') || 0,
        });

        var self = this;
        this.progressbar.appendTo('<div>').done(function() {
            self.progressbar.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.progressbar.$el);

            self.progressbar.on('update', self, function(update) {
                self.set('value', update.changed_value);
            });
        });
    },
    render_value: function() {
        this.progressbar.set_value(this.get('value'));
    },
    is_false: function() {
        return false;
    },
});

// The PercentPie field expects a float from 0 to 100.
var FieldPercentPie = common.AbstractField.extend({
    template: 'FieldPercentPie',
    start: function() {
        this.$left_mask = this.$('.o_mask').first();
        this.$right_mask = this.$('.o_mask').last();
        this.$pie_value = this.$('.o_pie_value');
        return this._super();
    },
    render_value: function() {
        var value = this.get('value') || 0, degValue = 360*value/100;

        this.$right_mask.toggleClass('o_full', degValue >= 180);

        var leftDeg = 'rotate(' + ((degValue < 180)? 180 : degValue) + 'deg)';
        var rightDeg = 'rotate(' + ((degValue < 180)? degValue : 0) + 'deg)';
        this.$left_mask.css({transform: leftDeg, msTransform: leftDeg, mozTransform: leftDeg, webkitTransform: leftDeg});
        this.$right_mask.css({transform: rightDeg, msTransform: rightDeg, mozTransform: rightDeg, webkitTransform: rightDeg});

        this.$pie_value.html(Math.round(value) + '%');
    },
    is_false: function() {
        return false;
    }
});

var FieldSelection = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: 'FieldSelection',
    events: {
        'change': 'store_dom_value',
    },
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.set("value", false);
        this.set("values", []);
        this.records_orderer = new utils.DropMisordered();
        this.field_manager.on("view_content_has_changed", this, function() {
            var domain = new data.CompoundDomain(this.build_domain()).eval();
            if (!_.isEqual(domain, this.get("domain"))) {
                this.set("domain", domain);
            }
        });
    },
    initialize_field: function() {
        common.ReinitializeFieldMixin.initialize_field.call(this);
        this.on("change:domain", this, this.query_values);
        this.set("domain", new data.CompoundDomain(this.build_domain()).eval());
        this.on("change:values", this, this.render_value);
    },
    query_values: function() {
        var self = this;
        var def;
        if (this.field.type === "many2one") {
            var model = new Model(this.field.relation);
            def = model.call("name_search", ['', this.get("domain")], {"context": this.build_context()});
        } else {
            var values = _.reject(this.field.selection, function (v) { return v[0] === false && v[1] === ''; });
            def = $.when(values);
        }
        this.records_orderer.add(def).then(function(values) {
            if (! _.isEqual(values, self.get("values"))) {
                self.set("values", values);
            }
        });
    },
    initialize_content: function() {
        // Flag indicating whether we're in an event chain containing a change
        // event on the select, in order to know what to do on keyup[RETURN]:
        // * If the user presses [RETURN] as part of changing the value of a
        //   selection, we should just let the value change and not let the
        //   event broadcast further (e.g. to validating the current state of
        //   the form in editable list view, which would lead to saving the
        //   current row or switching to the next one)
        // * If the user presses [RETURN] with a select closed (side-effect:
        //   also if the user opened the select and pressed [RETURN] without
        //   changing the selected value), takes the action as validating the row
        if(!this.get('effective_readonly')) {
            var ischanging = false;
            this.$el
                .change(function () { ischanging = true; })
                .click(function () { ischanging = false; })
                .keyup(function (e) {
                    if (e.which !== 13 || !ischanging) { return; }
                    e.stopPropagation();
                    ischanging = false;
                });
            this.setupFocus(this.$el);
        }
    },
    commit_value: function () {
        this.store_dom_value();
        return this._super();
    },
    store_dom_value: function () {
        if (!this.get('effective_readonly')) {
            this.internal_set_value(JSON.parse(this.$el.val()));
        }
    },
    set_value: function(value_) {
        value_ = value_ === null ? false : value_;
        value_ = value_ instanceof Array ? value_[0] : value_;
        this._super(value_);
    },
    render_value: function() {
        var values = this.get("values");
        values =  [[false, this.node.attrs.placeholder || '']].concat(values);
        var found = _.find(values, function(el) { return el[0] === this.get("value"); }, this);
        if (!found) {
            found = [this.get("value"), _t('Unknown')];
            values = [found].concat(values);
        }
        if (!this.get("effective_readonly")) {
            this.$el.empty();
            for(var i = 0 ; i < values.length ; i++) {
                this.$el.append($('<option/>', {
                    value: JSON.stringify(values[i][0]),
                    html: values[i][1]
                }))
            }
            this.$el.val(JSON.stringify(found[0]));
        } else {
            this.$el.text(found[1]);
        }
    },
    focus: function() {
        if (!this.get("effective_readonly")) {
            return this.$el.focus();
        }
        return false;
    },
});

/**
    This widget is intended to display a warning near a label of a 'timezone' field
    indicating if the browser timezone is identical (or not) to the selected timezone.
    This widget depends on a field given with the param 'tz_offset_field', which contains
    the time difference between UTC time and local time, in minutes.
*/
var TimezoneMismatch = FieldSelection.extend({
    initialize_content: function() {
        this._super.apply(this, arguments);
        this.tz_offset_field = (this.options && this.options.tz_offset_field) || this.tz_offset_field || 'tz_offset';
        this.set({"tz_offset": this.field_manager.get_field_value(this.tz_offset_field)});
        this.on("change:tz_offset", this, this.render_value);
    },
    start: function() {
        this._super.apply(this, arguments);
        // trigger a render_value when tz_offset field change
        this.field_manager.on("field_changed:" + this.tz_offset_field, this, function() {
            this.set({"tz_offset": this.field_manager.get_field_value(this.tz_offset_field)});
        });
    },
    check_timezone: function() {
        var user_offset = this.get('tz_offset');
        if (user_offset) {
            var offset = -(new Date().getTimezoneOffset());
            var browser_offset = (offset < 0) ? "-" : "+";
            browser_offset += _.str.sprintf("%02d", Math.abs(offset / 60));
            browser_offset += _.str.sprintf("%02d", Math.abs(offset % 60));
            return (browser_offset !== user_offset);
        }
        return false;
    },
    render_value: function() {
        this._super.apply(this, arguments);
        this.$label.next('.o_tz_warning').remove();
        if(this.check_timezone()){
            var options = _.extend({
                delay: { show: 501, hide: 0 },
                title: _t("Timezone Mismatch : The timezone of your browser doesn't match the selected one. The time in Odoo is displayed according to your field timezone."),
            });
            $('<span/>').addClass('fa fa-exclamation-triangle o_tz_warning').insertAfter(this.$label).tooltip(options);
        }
    }
});

var LabelSelection = FieldSelection.extend({
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.classes = this.options && this.options.classes || {};
    },
    render_value: function() {
        this._super.apply(this, arguments);
        if (this.get("effective_readonly")) {
            var bt_class = this.classes[this.get('value')] || 'default';
            this.$el.html($('<span/>', {html: this.$el.html()}).addClass('label label-' + bt_class));
        }
    },
});

var FieldRadio = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: 'FieldRadio',
    events: {
        'click input': 'click_change_value'
    },
    init: function(field_manager, node) {
        /* Radio button widget: Attributes options:
        * - "horizontal" to display in column
        * - "no_radiolabel" don't display text values
        */
        this._super(field_manager, node);
        this.selection = _.clone(this.field.selection) || [];
        this.domain = false;
        this.uniqueId = _.uniqueId("radio");
    },
    initialize_content: function () {
        this.field_manager.on("view_content_has_changed", this, this.get_selection);
        this.get_selection();
    },
    click_change_value: function (event) {
        var val = $(event.target).val();
        val = this.field.type == "selection" ? val : +val;
        if (val !== this.get_value()) {
            this.set_value(val);
        }
    },
    /** Get the selection and render it
     *  selection: [[identifier, value_to_display], ...]
     *  For selection fields: this is directly given by this.field.selection
     *  For many2one fields:  perform a search on the relation of the many2one field
     */
    get_selection: function() {
        var self = this;
        var selection = [];
        var def = $.Deferred();
        if (self.field.type == "many2one") {
            var domain = pyeval.eval('domain', this.build_domain()) || [];
            if (! _.isEqual(self.domain, domain)) {
                self.domain = domain;
                var ds = new data.DataSetStatic(self, self.field.relation, self.build_context());
                ds.call('search', [self.domain])
                    .then(function (records) {
                        ds.name_get(records).then(function (records) {
                            selection = records;
                            def.resolve();
                        });
                    });
            } else {
                selection = self.selection;
                def.resolve();
            }
        }
        else if (self.field.type == "selection") {
            selection = self.field.selection || [];
            def.resolve();
        }
        return def.then(function () {
            if (!_.isEqual(selection, self.selection)) {
                self.selection = _.clone(selection);
                self.renderElement();
                self.render_value();
            }
        });
    },
    set_value: function (value_) {
        if (this.field.type == "selection") {
            value_ = _.find(this.field.selection, function (sel) { return sel[0] == value_;});
        }
        else if (!this.selection.length) {
            this.selection = [value_];
        }

        this._super(value_);
    },
    get_value: function () {
        var value = this.get('value');
        value = ((value instanceof Array)? value[0] : value);
        return  _.isUndefined(value) ? false : value;
    },
    render_value: function () {
        var self = this;
        if(this.get('effective_readonly')) {
            this.$el.html(this.get('value')? this.get('value')[1] : "");
        } else {
            this.$("input").prop("checked", false).filter(function () {return this.value == self.get_value();}).prop("checked", true);
        }
    }
});

var FieldReference = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    className: 'o_row',
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.reference_ready = true;
    },
    destroy_content: function() {
        if (this.fm) {
            this.fm.destroy();
            this.fm = undefined;
        }
    },
    initialize_content: function() {
        var self = this;
        this.fm = new common.DefaultFieldManager(this);
        this.fm.extend_field_desc({
            "selection": {
                selection: this.field_manager.get_field_desc(this.name).selection,
                type: "selection",
            },
            "m2o": {
                relation: null,
                type: "many2one",
            },
        });
        this.selection = new FieldSelection(this.fm, { attrs: {
            name: 'selection',
            modifiers: JSON.stringify({readonly: this.get('effective_readonly')}),
        }});
        this.selection.on("change:value", this, this.on_selection_changed);
        this.selection.appendTo(this.$el);
        this.selection
            .on('focused', null, function () {self.trigger('focused');})
            .on('blurred', null, function () {self.trigger('blurred');});

        var FieldMany2One = core.form_widget_registry.get('many2one');
        this.m2o = new FieldMany2One(this.fm, { attrs: {
            name: 'Referenced Document',
            modifiers: JSON.stringify({readonly: this.get('effective_readonly')}),
            context: this.build_context().eval(),
        }});
        this.m2o.on("change:value", this, this.data_changed);
        this.m2o.appendTo(this.$el);
        this.m2o
            .on('focused', null, function () {self.trigger('focused');})
            .on('blurred', null, function () {self.trigger('blurred');});
    },
    on_selection_changed: function() {
        if (this.reference_ready) {
            this.internal_set_value([this.selection.get_value(), false]);
            this.render_value();
        }
    },
    data_changed: function() {
        if (this.reference_ready) {
            this.internal_set_value([this.selection.get_value(), this.m2o.get_value()]);
        }
    },
    set_value: function(val) {
        if (val) {
            val = val.split(',');
            val[0] = val[0] || false;
            val[1] = val[0] ? (val[1] ? parseInt(val[1], 10) : val[1]) : false;
        }
        this._super(val || [false, false]);
    },
    get_value: function() {
        return this.get('value')[0] && this.get('value')[1] ? (this.get('value')[0] + ',' + this.get('value')[1]) : false;
    },
    render_value: function() {
        this.reference_ready = false;
        if (!this.get("effective_readonly")) {
            this.selection.set_value(this.get('value')[0]);
        }
        this.m2o.field.relation = this.get('value')[0];
        this.m2o.set_value(this.get('value')[1]);
        this.m2o.do_toggle(!!this.get('value')[0]);
        this.reference_ready = true;
    },
    is_false: function() {
        return !this.get_value();
    },
});

var FieldBinary = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.binary_value = false;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = 25 * 1024 * 1024; // 25Mo
        if (!this.useFileAPI) {
            this.fileupload_id = _.uniqueId('o_fileupload');
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                self.on_file_uploaded.apply(self, args);
            });
        }
    },
    stop: function() {
        if (!this.useFileAPI) {
            $(window).off(this.fileupload_id);
        }
        this._super.apply(this, arguments);
    },
    initialize_content: function() {
        this.$inputFile = this.$('.o_form_input_file');
        this.$inputFile.change(this.on_file_change);
        var self = this;
        this.$('.o_select_file_button').click(function() {
            self.$inputFile.click();
        });
        this.$('.o_clear_file_button').click(this.on_clear);
    },
    on_file_change: function(e) {
        var self = this;
        var file_node = e.target;
        if ((this.useFileAPI && file_node.files.length) || (!this.useFileAPI && $(file_node).val() !== '')) {
            if (this.useFileAPI) {
                var file = file_node.files[0];
                if (file.size > this.max_upload_size) {
                    var msg = _t("The selected file exceed the maximum file size of %s.");
                    this.do_warn(_t("File upload"), _.str.sprintf(msg, utils.human_size(this.max_upload_size)));
                    return false;
                }
                var filereader = new FileReader();
                filereader.readAsDataURL(file);
                filereader.onloadend = function(upload) {
                    var data = upload.target.result;
                    data = data.split(',')[1];
                    self.on_file_uploaded(file.size, file.name, file.type, data);
                };
            } else {
                this.$('form.o_form_binary_form input[name=session_id]').val(this.session.session_id);
                this.$('form.o_form_binary_form').submit();
            }
            this.$('.o_form_binary_progress').show();
            this.$('button').hide();
        }
    },
    on_file_uploaded: function(size, name) {
        if (size === false) {
            this.do_warn(_t("File Upload"), _t("There was a problem while uploading your file"));
            // TODO: use openerp web crashmanager
            console.warn("Error while uploading file : ", name);
        } else {
            this.on_file_uploaded_and_valid.apply(this, arguments);
        }
        this.$('.o_form_binary_progress').hide();
        this.$('button').show();
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
        this.binary_value = true;
        this.set_filename(name);
        this.set_value(file_base64);
    },
    on_save_as: function(ev) {
        var value = this.get('value');
        if (!value) {
            this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
            ev.stopPropagation();
        } else {
            framework.blockUI();
            var c = crash_manager;
            var filename_fieldname = this.node.attrs.filename;
            var filename_field = this.view.fields && this.view.fields[filename_fieldname];
            this.session.get_file({
                'url': '/web/content',
                'data': {
                    'model': this.view.dataset.model,
                    'id': this.view.datarecord.id,
                    'field': this.name,
                    'filename_field': filename_fieldname,
                    'filename': filename_field ? filename_field.get('value') : null,
                    'download': true,
                    'data': utils.is_bin_size(value) ? null : value,
                },
                'complete': framework.unblockUI,
                'error': c.rpc_error.bind(c)
            });
            ev.stopPropagation();
        }
    },
    set_filename: function(value) {
        var filename = this.node.attrs.filename;
        if (filename) {
            var field = this.field_manager.fields[filename];
            if (field) {
                field.set_value(value);
                field._dirty_flag = true;
            }
        }
    },
    on_clear: function() {
        this.binary_value = false;
        this.set_filename('');
        this.set_value(false); // FIXME do not really remove the value
    }
});

var FieldBinaryFile = FieldBinary.extend({
    template: 'FieldBinaryFile',
    initialize_content: function() {
        var self = this;
        this._super();
        if (this.get("effective_readonly")) {
            this.$el.click(function(ev) {
                if (self.get('value')) {
                    self.on_save_as(ev);
                }
                return false;
            });
        } else {
            this.$input = this.$('.o_form_input').eq(0);
            this.$input.on('click', function() {
                self.$inputFile.click();
            });
        }
    },
    render_value: function() {
        var filename = this.view.datarecord[this.node.attrs.filename];
        if (this.get("effective_readonly")) {
            this.do_toggle(!!this.get('value'));
            if (this.get('value')) {
                this.$el.empty().append($("<span/>").addClass('fa fa-download'));
                if (filename) {
                    this.$el.append(" " + filename);
                }
            }
        } else {
            if(this.get('value')) {
                this.$el.children().removeClass('o_hidden');
                this.$('.o_select_file_button').first().addClass('o_hidden');
                this.$input.val(filename || this.get('value'));
            } else {
                this.$el.children().addClass('o_hidden');
                this.$('.o_select_file_button').first().removeClass('o_hidden');
            }
        }
    }
});

var FieldBinaryImage = FieldBinary.extend({
    template: 'FieldBinaryImage',
    placeholder: "/web/static/src/img/placeholder.png",
    render_value: function() {
        var url = this.placeholder;
        if(this.get('value')) {
            if(!utils.is_bin_size(this.get('value'))) {
                url = 'data:image/png;base64,' + this.get('value');
            } else {
                url = session.url('/web/image', {
                    model: this.view.dataset.model,
                    id: JSON.stringify(this.view.datarecord.id || null),
                    field: (this.options.preview_image)? this.options.preview_image : this.name,
                    unique: (this.view.datarecord.__last_update || '').replace(/[^0-9]/g, ''),
                });
            }
        }

        var $img = $(QWeb.render("FieldBinaryImage-img", {widget: this, url: url}));

        var self = this;
        $img.click(function(e) {
            if(self.view.get("actual_mode") == "view") {
                var $button = $(".o_form_button_edit");
                $button.openerpBounce();
                e.stopPropagation();
            }
        });
        this.$('> img').remove();
        if (self.options.size) {
            $img.css("width", "" + self.options.size[0] + "px");
            $img.css("height", "" + self.options.size[1] + "px");
        }
        this.$el.prepend($img);
        $img.on('error', function() {
            self.on_clear();
            $img.attr('src', self.placeholder);
            self.do_warn(_t("Image"), _t("Could not display the selected image."));
        });
    },
    set_value: function(value_) {
        var changed = value_ !== this.get_value();
        this._super.apply(this, arguments);
        // By default, on binary images read, the server returns the binary size
        // This is possible that two images have the exact same size
        // Therefore we trigger the change in case the image value hasn't changed
        // So the image is re-rendered correctly
        if (!changed){
            this.trigger("change:value", this, {
                oldValue: value_,
                newValue: value_
            });
        }
    },
    is_false: function() {
        return false;
    },
    set_dimensions: function(height, width) {
        this.$el.css({
            maxWidth: width,
            minHeight: height,
        });
    },
});

var FieldStatus = common.AbstractField.extend({
    template: "FieldStatus",
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.options.clickable = this.options.clickable || (this.node.attrs || {}).clickable || false;
        this.options.visible = this.options.visible || (this.node.attrs || {}).statusbar_visible || false;
        this.set({value: false});
        this.selection = {'unfolded': [], 'folded': []};
        this.set("selection", {'unfolded': [], 'folded': []});
        this.selection_dm = new utils.DropMisordered();
        this.dataset = new data.DataSetStatic(this, this.field.relation, this.build_context());
    },
    start: function() {
        this.field_manager.on("view_content_has_changed", this, this.calc_domain);
        this.calc_domain();
        this.on("change:value", this, this.get_selection);
        this.on("change:evaluated_selection_domain", this, this.get_selection);
        this.on("change:selection", this, function() {
            this.selection = this.get("selection");
            this.render_value();
        });
        this.get_selection();
        if (this.options.clickable) {
            this.bind_stage_click();
        }
        this._super();
    },
    bind_stage_click: function () {
        // This function is overriden in the enterprise webclient
        this.$el.on('click','li[data-id]',this.on_click_stage);
    },
    set_value: function(value_) {
        if (value_ instanceof Array) {
            value_ = value_[0];
        }
        this._super(value_);
    },
    render_value: function() {
        var self = this;
        var content = QWeb.render("FieldStatus.content", {
            'widget': self,
            'value_folded': _.find(self.selection.folded, function(i){return i[0] === self.get('value');})
        });
        self.$el.html(content);
    },
    calc_domain: function() {
        var d = pyeval.eval('domain', this.build_domain());
        var domain = []; //if there is no domain defined, fetch all the records

        if (d.length) {
            domain = ['|',['id', '=', this.get('value')]].concat(d);
        }

        if (! _.isEqual(domain, this.get("evaluated_selection_domain"))) {
            this.set("evaluated_selection_domain", domain);
        }
    },
    /** Get the selection and render it
     *  selection: [[identifier, value_to_display], ...]
     *  For selection fields: this is directly given by this.field.selection
     *  For many2one fields:  perform a search on the relation of the many2one field
     */
    get_selection: function() {
        var self = this;
        var selection_unfolded = [];
        var selection_folded = [];
        var fold_field = this.options.fold_field;

        var calculation = _.bind(function() {
            if (this.field.type === "many2one") {
                return self.get_distant_fields().then(function () {
                    return new data.DataSetSearch(self, self.field.relation, self.build_context(), self.get("evaluated_selection_domain"))
                        .read_slice(_.union(_.keys(self.distant_fields), ['id']), {}).then(function (records) {
                            var ids = _.pluck(records, 'id');
                            return self.dataset.name_get(ids).then(function (records_name) {
                                _.each(records, function (record) {
                                    var name = _.find(records_name, function (val) {return val[0] === record.id;})[1];
                                    if (fold_field && record[fold_field] && record.id !== self.get('value')) {
                                        selection_folded.push([record.id, name]);
                                    } else {
                                        selection_unfolded.push([record.id, name]);
                                    }
                                });
                            });
                        });
                    });
            } else {
                // For field type selection filter values according to
                // statusbar_visible attribute of the field. For example:
                // statusbar_visible="draft,open".
                var select = this.field.selection;
                for(var i=0; i < select.length; i++) {
                    var key = select[i][0];
                    if(key === this.get('value') || !this.options.visible || this.options.visible.indexOf(key) !== -1) {
                        selection_unfolded.push(select[i]);
                    }
                }
                return $.when();
            }
        }, this);
        this.selection_dm.add(calculation()).then(function () {
            var selection = {'unfolded': selection_unfolded, 'folded': selection_folded};
            if (! _.isEqual(selection, self.get("selection"))) {
                self.set("selection", selection);
            }
        });
    },
    /*
     * :deprecated: this feature will probably be removed with OpenERP v8
     */
    get_distant_fields: function() {
        var self = this;
        if (! this.options.fold_field) {
            this.distant_fields = {};
        }
        if (this.distant_fields) {
            return $.when(this.distant_fields);
        }
        return new Model(self.field.relation).call("fields_get", [[this.options.fold_field]]).then(function(fields) {
            self.distant_fields = fields;
            return fields;
        });
    },
    on_click_stage: _.debounce(function (ev) {
        var self = this;
        var $li = $(ev.currentTarget);
        var ul = $li.closest('.oe_form_field_status');
        if (this.view.is_disabled) {
            return;
        }
        var val;
        if (ul.attr('disabled')) {
            return;
        }
        if (this.field.type === "many2one") {
            val = parseInt($li.data("id"), 10);
        } else {
            val = $li.data("id");
        }
        if (val !== self.get('value')) {
            if (!this.view.datarecord.id ||
                    this.view.datarecord.id.toString().match(data.BufferedDataSet.virtual_id_regex)) {
                // don't save, only set value for not-yet-saved many2ones
                self.set_value(val);
            }
            else {
                this.view.recursive_save().done(function() {
                    var change = {};
                    change[self.name] = val;
                    ul.attr('disabled', true);
                    self.view.dataset.write(self.view.datarecord.id, change).done(function() {
                        self.view.reload();
                    }).always(function() {
                        ul.removeAttr('disabled');
                    });
                });
            }
        }
    }, 300, true),
});

var FieldMonetary = FieldFloat.extend({
    template: 'FieldMonetary',
    init: function() {
        this._super.apply(this, arguments);
        this.set({"currency": false});
        var currency_field = (this.options && this.options.currency_field) || this.field.currency_field || 'currency_id';
        if (currency_field) {
            this.field_manager.on("field_changed:" + currency_field, this, function() {
                this.set({"currency": this.field_manager.get_field_value(currency_field)});
            });
        }
        this.on("change:currency", this, this.get_currency_info);
        this.get_currency_info();
    },
    start: function() {
        var tmp = this._super();
        this.on("change:currency_info", this, this.update);
        return tmp;
    },
    initialize_content: function() {
        if(!this.get('effective_readonly')) {
            this.$input = this.$('input');
            this.add_symbol();
        } else {
            this.$input = undefined;
        }

        this._super();
    },
    add_symbol: function() {
        var currency = this.get('currency_info');
        if(currency) {
            var before = (currency.position === 'before');
            this.$el[(before)? 'prepend' : 'append']($('<span/>', {html: currency.symbol}));
        }
    },
    get_currency_info: function() {
        var self = this;
        if (this.get("currency") === false) {
            this.set({"currency_info": null});
            return;
        }
        return self.set({"currency_info": session.get_currency(self.get("currency"))});
    },
    update: function() {
        if (this.view.options.is_list_editable) {
            return;
        } else {
            return this.reinitialize();
        }
    },
    render_value: function() {
        this._super();
        if(this.get('effective_readonly')) {
            this.add_symbol();
        }
    },
    get_digits_precision: function() {
        return this.node.attrs.digits || this.field.digits || (this.get('currency_info') && this.get('currency_info').digits);
    },
    parse_value: function(val, def) {
        return formats.parse_value(val, {type: "float", digits: this.get_digits_precision()}, def);
    },
    format_value: function(val, def) {
        return formats.format_value(val, {type: "float", digits: this.get_digits_precision()}, def);
    },
});

/**
    This widget is intended to be used on stat button numeric fields.  It will display
    the value   many2many and one2many. It is a read-only field that will
    display a simple string "<value of field> <label of the field>"
*/
var StatInfo = common.AbstractField.extend({
    is_field_number: true,
    init: function() {
        this._super.apply(this, arguments);
        this.internal_set_value(0);
    },
    set_value: function(value_) {
        if (value_ === false || value_ === undefined) {
            value_ = 0;
        }
        this._super.apply(this, [value_]);
    },
    render_value: function() {
        var options = {
            value: this.get("value") || 0,
        };
        if (! this.node.attrs.nolabel) {
            if(this.options.label_field && this.view.datarecord[this.options.label_field]) {
                options.text = this.view.datarecord[this.options.label_field];
            }
            else {
                options.text = this.string;
            }
        }
        this.$el.html(QWeb.render("StatInfo", options));
        this.$el.addClass('o_stat_info');
    },
});

/**
    This widget is intended to be used on boolean fields. It toggles a button
    switching between a green bullet / gray bullet.
*/
var FieldToggleBoolean = common.AbstractField.extend({
    template: "toggle_button",
    events: {
        'click': 'set_toggle_button'
    },
    render_value: function () {
        var class_name = this.get_value() ? 'o_toggle_button_success' : 'text-muted';
        this.$('i').attr('class', ('fa fa-circle ' + class_name));
    },
    set_toggle_button: function () {
        var self = this;
        var toggle_value = !this.get_value();
        if (this.view.get('actual_mode') == 'view') {
            var rec_values = {};
            rec_values[self.node.attrs.name] = toggle_value;
            return this.view.dataset._model.call(
                    'write', [
                        [this.view.datarecord.id],
                        rec_values,
                        self.view.dataset.get_context()
                    ]).done(function () { self.reload_record(); });
        }
        else {
            this.set_value(toggle_value);
        }
    },
    reload_record: function () {
        this.view.reload();
    },
    is_false: function() {
        return false;
    },
});

/**
    This widget is intended to be used on Text fields. It will provide Ace Editor for editing XML and Python.
*/

var AceEditor = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: "AceEditor",
    willStart: function() {
        if (!window.ace && !this.loadJS_def) {
            this.loadJS_def = ajax.loadJS('/web/static/lib/ace/ace.odoo-custom.js').then(function () {
                return $.when(ajax.loadJS('/web/static/lib/ace/mode-python.js'),
                    ajax.loadJS('/web/static/lib/ace/mode-xml.js')
                );
            });
        }
        return $.when(this._super(), this.loadJS_def);
    },
    initialize_content: function () {
        if (! this.get("effective_readonly")) {
            var self = this;

            this.aceEditor = ace.edit(this.$('.ace-view-editor')[0]);
            this.aceEditor.setOptions({"maxLines": Infinity});
            this.aceEditor.$blockScrolling = true;

            var scrollIntoViewIfNeeded = _.throttle(function () {
                var node = self.aceEditor.renderer.textarea;
                if (node.scrollIntoViewIfNeeded) {
                    node.scrollIntoViewIfNeeded(false);
                } else {
                    var offsetParent = node.offsetParent;
                    while (offsetParent) {
                        var elY = 0;
                        var elH = node.offsetHeight+20;
                        var parent = node;
                        while (offsetParent && parent) {
                            elY += node.offsetTop;
                            // get if a parent have a scrollbar
                            parent = node.parentNode;
                            while (parent != offsetParent &&
                                (parent.tagName === "BODY" || ["auto", "scroll"].indexOf(window.getComputedStyle(parent).overflowY) === -1)) {
                                parent = parent.parentNode;
                            }
                            node = parent;
                            if (parent !== offsetParent) {
                                elY -= parent.offsetTop;
                                parent = null;
                            }
                            offsetParent = node.offsetParent;
                        }

                        if ((node.tagName === "BODY" || ["auto", "scroll"].indexOf(window.getComputedStyle(node).overflowY) !== -1) &&
                            (node.scrollTop + node.clientHeight) < (elY + elH)) {
                            node.scrollTop = (elY + elH) - node.clientHeight;
                        }
                    }
                }
            });
            var $moveTextAreaToCursor = this.aceEditor.renderer.$moveTextAreaToCursor;
            self.aceEditor.renderer.$moveTextAreaToCursor = function() {
                $moveTextAreaToCursor.call(this);
                if (parseInt($(self.aceEditor.renderer.textarea).css('top'), 10) >= 0) {
                    scrollIntoViewIfNeeded();
                }
            };

            this.aceSession = this.aceEditor.getSession();
            this.aceSession.setUseWorker(false);
            this.aceSession.setMode("ace/mode/"+(this.options.mode || 'xml'));

            this.aceEditor.on("blur", function() {
                if (self.aceSession.getUndoManager().hasUndo()) {
                    self.set_value(self.aceSession.getValue());
                }
            });
        }
    },
    destroy_content: function() {
        if (this.aceEditor) {
            this.aceEditor.destroy();
        }
    },
    render_value: function() {
        if (! this.get("effective_readonly")) {
            var value = formats.format_value(this.get('value'), this);
            this.aceSession.setValue(value);

        } else {
            var txt = this.get("value") || '';
            this.$(".oe_form_text_content").text(txt);
        }
    },
    focus: function() {
        return this.aceEditor.focus();
    },
});

/**
 * Registry of form fields, called by :js:`instance.web.FormView`.
 *
 * All referenced classes must implement FieldInterface. Those represent the classes whose instances
 * will substitute to the <field> tags as defined in OpenERP's views.
 */
core.form_widget_registry
    .add('char', FieldChar)
    .add('id', FieldID)
    .add('email', FieldEmail)
    .add('url', FieldUrl)
    .add('text',FieldText)
    .add('domain', FieldDomain)
    .add('date', FieldDate)
    .add('datetime', FieldDatetime)
    .add('selection', FieldSelection)
    .add('radio', FieldRadio)
    .add('reference', FieldReference)
    .add('boolean', FieldBoolean)
    .add('boolean_button', FieldBooleanButton)
    .add('toggle_button', FieldToggleBoolean)
    .add('float', FieldFloat)
    .add('percentpie', FieldPercentPie)
    .add('integer', FieldFloat)
    .add('float_time', FieldFloat)
    .add('progressbar', FieldProgressBar)
    .add('image', FieldBinaryImage)
    .add('binary', FieldBinaryFile)
    .add('statusbar', FieldStatus)
    .add('monetary', FieldMonetary)
    .add('priority', FieldPriority)
    .add('kanban_state_selection', KanbanSelection)
    .add('statinfo', StatInfo)
    .add('timezone_mismatch', TimezoneMismatch)
    .add('label_selection', LabelSelection)
    .add('ace', AceEditor);

/**
 * Registry of widgets usable in the form view that can substitute to any possible
 * tags defined in OpenERP's form views.
 *
 * Every referenced class should extend FormWidget.
 */
core.form_tag_registry.add('button', WidgetButton);

return {
    FieldBoolean: FieldBoolean,
    FieldChar: FieldChar,
    FieldEmail: FieldEmail,
    FieldFloat: FieldFloat,
    FieldRadio: FieldRadio,
    FieldStatus: FieldStatus,
    FieldMonetary: FieldMonetary,
    WidgetButton: WidgetButton
};

});
