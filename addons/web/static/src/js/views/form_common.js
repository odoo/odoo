odoo.define('web.form_common', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var ListView = require('web.ListView');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Interface implemented by the form view or any other object
 * able to provide the features necessary for the fields to work.
 *
 * Properties:
 *     - display_invalid_fields : if true, all fields where is_valid() return true should
 *     be displayed as invalid.
 *     - actual_mode : the current mode of the field manager. Can be "view", "edit" or "create".
 * Events:
 *     - view_content_has_changed : when the values of the fields have changed. When
 *     this event is triggered all fields should reprocess their modifiers.
 *     - field_changed:<field_name> : when the value of a field change, an event is triggered
 *     named "field_changed:<field_name>" with <field_name> replaced by the name of the field.
 *     This event is not related to the on_change mechanism of OpenERP and is always called
 *     when the value of a field is setted or changed. This event is only triggered when the
 *     value of the field is syntactically valid, but it can be triggered when the value
 *     is sematically invalid (ie, when a required field is false). It is possible that an event
 *     about a precise field is never triggered even if that field exists in the view, in that
 *     case the value of the field is assumed to be false.
 */
var FieldManagerMixin = {
    /**
     * Must return the asked field as in fields_get.
     */
    get_field_desc: function(field_name) {},
    /**
     * Returns the current value of a field present in the view. See the get_value() method
     * method in FieldInterface for further information.
     */
    get_field_value: function(field_name) {},
    /**
    Gives new values for the fields contained in the view. The new values could not be setted
    right after the call to this method. Setting new values can trigger on_changes.

    @param {Object} values A dictonary with key = field name and value = new value.
    @return {$.Deferred} Is resolved after all the values are setted.
    */
    set_values: function(values) {},
    /**
    Computes an OpenERP domain.

    @param {Array} expression An OpenERP domain.
    @return {boolean} The computed value of the domain.
    */
    compute_domain: function(expression) {},
    /**
    Builds an evaluation context for the resolution of the fields' contexts. Please note
    the field are only supposed to use this context to evualuate their own, they should not
    extend it.

    @return {CompoundContext} An OpenERP context.
    */
    build_eval_context: function() {},
};

/**
    Welcome.

    If you read this documentation, it probably means that you were asked to use a form view widget outside of
    a form view. Before going further, you must understand that those fields were never really created for
    that usage. Don't think that this class will hold the answer to all your problems, at best it will allow
    you to hack the system with more style.
*/
var DefaultFieldManager = Widget.extend({
    init: function(parent, eval_context) {
        this._super(parent);
        this.field_descs = {};
        this.eval_context = eval_context || {};
        this.set({
            display_invalid_fields: false,
            actual_mode: 'create',
        });
    },
    get_field_desc: function(field_name) {
        if (this.field_descs[field_name] === undefined) {
            this.field_descs[field_name] = {
                string: field_name,
            };
        }
        return this.field_descs[field_name];
    },
    extend_field_desc: function(fields) {
        var self = this;
        _.each(fields, function(v, k) {
            _.extend(self.get_field_desc(k), v);
        });
    },
    get_field_value: function(field_name) {
        return false;
    },
    set_values: function(values) {
        // nothing
    },
    compute_domain: function(expression) {
        return data.compute_domain(expression, {});
    },
    build_eval_context: function() {
        return new data.CompoundContext(this.eval_context);
    },
});


/**
 * A mixin to apply on any FormWidget that has to completely re-render when its readonly state
 * switch.
 */
var ReinitializeWidgetMixin =  {
    /**
     * Default implementation of, you should not override it, use initialize_field() instead.
     */
    start: function() {
        this.initialize_field();
        this._super();
    },
    initialize_field: function() {
        this.on("change:effective_readonly", this, this.reinitialize);
        this.initialize_content();
    },
    reinitialize: function() {
        this.destroy_content();
        this.renderElement();
        this.initialize_content();
    },
    /**
     * Called to destroy anything that could have been created previously, called before a
     * re-initialization.
     */
    destroy_content: function() {},
    /**
     * Called to initialize the content.
     */
    initialize_content: function() {},
};

/**
 * A mixin to apply on any field that has to completely re-render when its readonly state
 * switch.
 */
var ReinitializeFieldMixin =  _.extend({}, ReinitializeWidgetMixin, {
    reinitialize: function() {
        ReinitializeWidgetMixin.reinitialize.call(this);
        var res = this.render_value();
        if (this.view && this.view.render_value_defs){
            this.view.render_value_defs.push(res);
        }
    },
});

/**
    A mixin containing some useful methods to handle completion inputs.
    
    The widget containing this option can have these arguments in its widget options:
    - no_quick_create: if true, it will disable the quick create
*/
var CompletionFieldMixin = {
    init: function() {
        this.limit = 7;
        this.orderer = new utils.DropMisordered();
        this.can_create = this.node.attrs.can_create || true;
        this.can_write = this.node.attrs.can_write || true;
    },
    /**
     * Call this method to search using a string.
     */
    get_search_result: function(search_val) {
        var self = this;

        var dataset = new data.DataSet(this, this.field.relation, self.build_context());
        this.last_query = search_val;
        var exclusion_domain = [], ids_blacklist = this.get_search_blacklist();
        if (!_(ids_blacklist).isEmpty()) {
            exclusion_domain.push(['id', 'not in', ids_blacklist]);
        }

        return this.orderer.add(dataset.name_search(
                search_val, new data.CompoundDomain(self.build_domain(), exclusion_domain),
                'ilike', this.limit + 1, self.build_context())).then(function(data) {
            self.last_search = data;
            // possible selections for the m2o
            var values = _.map(data, function(x) {
                x[1] = x[1].split("\n")[0];
                return {
                    label: _.str.escapeHTML(x[1]),
                    value: x[1],
                    name: x[1],
                    id: x[0],
                };
            });

            // search more... if more results that max
            if (values.length > self.limit) {
                values = values.slice(0, self.limit);
                values.push({
                    label: _t("Search More..."),
                    action: function() {
                        dataset.name_search(search_val, self.build_domain(), 'ilike', 160).done(function(data) {
                            self._search_create_popup("search", data);
                        });
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            // quick create
            var raw_result = _(data.result).map(function(x) {return x[1];});
            if (search_val.length > 0 && !_.include(raw_result, search_val) &&
                ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                self.can_create && values.push({
                    label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                        $('<span />').text(search_val).html()),
                    action: function() {
                        self._quick_create(search_val);
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            // create...
            if (!(self.options && (self.options.no_create || self.options.no_create_edit)) && self.can_create){
                values.push({
                    label: _t("Create and Edit..."),
                    action: function() {
                        self._search_create_popup("form", undefined, self._create_context(search_val));
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            else if (values.length === 0) {
                values.push({
                    label: _t("No results to show..."),
                    action: function() {},
                    classname: 'oe_m2o_dropdown_option'
                });
            }

            return values;
        });
    },
    get_search_blacklist: function() {
        return [];
    },
    _quick_create: function(name) {
        var self = this;
        var slow_create = function () {
            self._search_create_popup("form", undefined, self._create_context(name));
        };
        if (self.options.quick_create === undefined || self.options.quick_create) {
            new data.DataSet(this, this.field.relation, self.build_context())
                .name_create(name).done(function(data) {
                    if (!self.get('effective_readonly'))
                        self.add_id(data[0]);
                }).fail(function(error, event) {
                    event.preventDefault();
                    slow_create();
                });
        } else
            slow_create();
    },
    // all search/create popup handling
    _search_create_popup: function(view, ids, context) {
        var self = this;
        var pop = new SelectCreatePopup(this);
        pop.select_element(
            self.field.relation,
            {
                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
                initial_ids: ids ? _.map(ids, function(x) {return x[0];}) : undefined,
                initial_view: view,
                disable_multiple_selection: true
            },
            self.build_domain(),
            new data.CompoundContext(self.build_context(), context || {})
        );
        pop.on("elements_selected", self, function(element_ids) {
            self.add_id(element_ids[0]);
            self.focus();
        });
    },
    /**
     * To implement.
     */
    add_id: function(id) {},
    _create_context: function(name) {
        var tmp = {};
        var field = (this.options || {}).create_name_field;
        if (field === undefined)
            field = "name";
        if (field !== false && name && (this.options || {}).quick_create !== false)
            tmp["default_" + field] = name;
        return tmp;
    },
};



/**
 * Must be applied over an class already possessing the PropertiesMixin.
 *
 * Apply the result of the "invisible" domain to this.$el.
 */
var InvisibilityChangerMixin = {
    init: function(field_manager, invisible_domain) {
        var self = this;
        this._ic_field_manager = field_manager;
        this._ic_invisible_modifier = invisible_domain;
        this._ic_field_manager.on("view_content_has_changed", this, function() {
            var result = self._ic_invisible_modifier === undefined ? false :
                self._ic_field_manager.compute_domain(self._ic_invisible_modifier);
            self.set({"invisible": result});
        });
        this.set({invisible: this._ic_invisible_modifier === true, force_invisible: false});
        var check = function() {
            if (self.get("invisible") || self.get('force_invisible')) {
                self.set({"effective_invisible": true});
            } else {
                self.set({"effective_invisible": false});
            }
        };
        this.on('change:invisible', this, check);
        this.on('change:force_invisible', this, check);
        check.call(this);
    },
    start: function() {
        this.on("change:effective_invisible", this, this._check_visibility);
        this._check_visibility();
    },
    _check_visibility: function() {
        this.$el.toggleClass('oe_form_invisible', this.get("effective_invisible"));
    },
};

var InvisibilityChanger = core.Class.extend(core.mixins.PropertiesMixin, InvisibilityChangerMixin, {
    init: function(parent, field_manager, invisible_domain, $el) {
        this.setParent(parent);
        core.mixins.PropertiesMixin.init.call(this);
        InvisibilityChangerMixin.init.call(this, field_manager, invisible_domain);
        this.$el = $el;
        this.start();
    },
});

// Specialization of InvisibilityChanger for the `notebook` form element to handle more
// elegantly its special cases (i.e. activate the closest visible sibling)
var NotebookInvisibilityChanger = InvisibilityChanger.extend({
    // Override start so that it does not call _check_visibility since it will be
    // called again when view content will be loaded (event view_content_has_changed)
    start: function() {
        this.on("change:effective_invisible", this, this._check_visibility);
    },
    _check_visibility: function() {
        this._super();
        if (this.get("effective_invisible") === true) {
            // Switch to invisible
            // Remove this element as active and set a visible sibling active (if there is one)
            if (this.$el.hasClass('active')) {
                this.$el.removeClass('active');
                var visible_siblings = this.$el.siblings(':not(.oe_form_invisible)');
                if (visible_siblings.length) {
                    $(visible_siblings[0]).addClass('active');
                }
            }
        } else {
            // Switch to visible
            // If there is no visible active sibling, set this element as active,
            // otherwise if that sibling hasn't autofocus and if we are in edit mode,
            //    remove that sibling as active and set this element as active
            var visible_active_sibling = this.$el.siblings(':not(.oe_form_invisible).active');
            if (!(visible_active_sibling.length)) {
                this.$el.addClass('active');
            } else if (!$(visible_active_sibling[0]).data('autofocus') && this._ic_field_manager.get('actual_mode') === "edit") {
                this.$el.addClass('active');
                $(visible_active_sibling[0]).removeClass('active');
            }
        }
    },
});


/**
    Base class for all fields, custom widgets and buttons to be displayed in the form view.

    Properties:
        - effective_readonly: when it is true, the widget is displayed as readonly. Vary depending
        the values of the "readonly" property and the "mode" property on the field manager.
*/
var FormWidget = Widget.extend(InvisibilityChangerMixin, {
    /**
     * @constructs instance.web.form.FormWidget
     * @extends instance.web.Widget
     *
     * @param field_manager
     * @param node
     */
    init: function(field_manager, node) {
        this._super(field_manager);
        this.field_manager = field_manager;
        this.view = this.field_manager;
        this.node = node;
        this.session = session;
        this.modifiers = JSON.parse(this.node.attrs.modifiers || '{}');
        InvisibilityChangerMixin.init.call(this, this.field_manager, this.modifiers.invisible);

        this.field_manager.on("view_content_has_changed", this, this.process_modifiers);

        this.set({
            required: false,
            readonly: false,
        });
        // some events to make the property "effective_readonly" sync automatically with "readonly" and
        // "mode" on field_manager
        var self = this;
        var test_effective_readonly = function() {
            self.set({"effective_readonly": self.get("readonly") || self.field_manager.get("actual_mode") === "view"});
        };
        this.on("change:readonly", this, test_effective_readonly);
        this.field_manager.on("change:actual_mode", this, test_effective_readonly);
        test_effective_readonly.call(this);
    },
    renderElement: function() {
        this.process_modifiers();
        this._super();
        this.$el.addClass(this.node.attrs["class"] || "");
    },
    destroy: function() {
        $.fn.tooltip('destroy');
        this._super.apply(this, arguments);
    },
    /**
     * Sets up blur/focus forwarding from DOM elements to a widget (`this`).
     *
     * This method is an utility method that is meant to be called by child classes.
     *
     * @param {jQuery} $e jQuery object of elements to bind focus/blur on
     */
    setupFocus: function ($e) {
        var self = this;
        $e.on({
            focus: function () { self.trigger('focused'); },
            blur: function () { self.trigger('blurred'); }
        });
    },
    process_modifiers: function() {
        var to_set = {};
        for (var a in this.modifiers) {
            if (!this.modifiers.hasOwnProperty(a)) { continue; }
            if (!_.include(["invisible"], a)) {
                var val = this.field_manager.compute_domain(this.modifiers[a]);
                to_set[a] = val;
            }
        }
        this.set(to_set);
    },
    do_attach_tooltip: function(widget, trigger, options) {
        widget = widget || this;
        trigger = trigger || this.$el;
        options = _.extend({
                delay: { show: 500, hide: 0 },
                title: function() {
                    var template = widget.template + '.tooltip';
                    if (!QWeb.has_template(template)) {
                        template = 'WidgetLabel.tooltip';
                    }
                    return QWeb.render(template, {
                        debug: session.debug,
                        widget: widget
                    });
                },
            }, options || {});
        //only show tooltip if we are in debug or if we have a help to show, otherwise it will display
        //as empty
        if (session.debug || widget.node.attrs.help || (widget.field && widget.field.help)){
            $(trigger).tooltip(options);
        }
    },
    /**
     * Builds a new context usable for operations related to fields by merging
     * the fields'context with the action's context.
     */
    build_context: function() {
        // only use the model's context if there is not context on the node
        var v_context = this.node.attrs.context;
        if (! v_context) {
            v_context = (this.field || {}).context || {};
        }

        if (v_context.__ref || true) { //TODO: remove true
            var fields_values = this.field_manager.build_eval_context();
            v_context = new data.CompoundContext(v_context).set_eval_context(fields_values);
        }
        return v_context;
    },
    build_domain: function() {
        var f_domain = this.field.domain || [];
        var n_domain = this.node.attrs.domain || null;
        // if there is a domain on the node, overrides the model's domain
        var final_domain = n_domain !== null ? n_domain : f_domain;
        if (!(final_domain instanceof Array) || true) { //TODO: remove true
            var fields_values = this.field_manager.build_eval_context();
            final_domain = new data.CompoundDomain(final_domain).set_eval_context(fields_values);
        }
        return final_domain;
    }
});

/*
# Values: (0, 0,  { fields })    create
#         (1, ID, { fields })    update
#         (2, ID)                remove (delete)
#         (3, ID)                unlink one (target id or target of relation)
#         (4, ID)                link
#         (5)                    unlink all (only valid for one2many)
*/
var commands = {
    // (0, _, {values})
    CREATE: 0,
    'create': function (values) {
        return [commands.CREATE, false, values];
    },
    // (1, id, {values})
    UPDATE: 1,
    'update': function (id, values) {
        return [commands.UPDATE, id, values];
    },
    // (2, id[, _])
    DELETE: 2,
    'delete': function (id) {
        return [commands.DELETE, id, false];
    },
    // (3, id[, _]) removes relation, but not linked record itself
    FORGET: 3,
    'forget': function (id) {
        return [commands.FORGET, id, false];
    },
    // (4, id[, _])
    LINK_TO: 4,
    'link_to': function (id) {
        return [commands.LINK_TO, id, false];
    },
    // (5[, _[, _]])
    DELETE_ALL: 5,
    'delete_all': function () {
        return [5, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    REPLACE_WITH: 6,
    'replace_with': function (ids) {
        return [6, false, ids];
    }
};

/**
 * Interface to be implemented by fields.
 *
 * Events:
 *     - changed_value: triggered when the value of the field has changed. This can be due
 *      to a user interaction or a call to set_value().
 *
 */
var FieldInterface = {
    /**
     * Constructor takes 2 arguments:
     * - field_manager: Implements FieldManagerMixin
     * - node: the "<field>" node in json form
     */
    init: function(field_manager, node) {},
    /**
     * Called by the form view to indicate the value of the field.
     *
     * Multiple calls to set_value() can occur at any time and must be handled correctly by the implementation,
     * regardless of any asynchronous operation currently running. Calls to set_value() can and will also occur
     * before the widget is inserted into the DOM.
     *
     * set_value() must be able, at any moment, to handle the syntax returned by the "read" method of the
     * osv class in the OpenERP server as well as the syntax used by the set_value() (see below). It must
     * also be able to handle any other format commonly used in the _defaults key on the models in the addons
     * as well as any format commonly returned in a on_change. It must be able to autodetect those formats as
     * no information is ever given to know which format is used.
     */
    set_value: function(value_) {},
    /**
     * Get the current value of the widget.
     *
     * Must always return a syntactically correct value to be passed to the "write" method of the osv class in
     * the OpenERP server, although it is not assumed to respect the constraints applied to the field.
     * For example if the field is marked as "required", a call to get_value() can return false.
     *
     * get_value() can also be called *before* a call to set_value() and, in that case, is supposed to
     * return a default value according to the type of field.
     *
     * This method is always assumed to perform synchronously, it can not return a promise.
     *
     * If there was no user interaction to modify the value of the field, it is always assumed that
     * get_value() return the same semantic value than the one passed in the last call to set_value(),
     * although the syntax can be different. This can be the case for type of fields that have a different
     * syntax for "read" and "write" (example: m2o: set_value([0, "Administrator"]), get_value() => 0).
     */
    get_value: function() {},
    /**
     * Inform the current object of the id it should use to match a html <label> that exists somewhere in the
     * view.
     */
    set_input_id: function(id) {},
    /**
     * Returns true if is_syntax_valid() returns true and the value is semantically
     * valid too according to the semantic restrictions applied to the field.
     */
    is_valid: function() {},
    /**
     * Returns true if the field holds a value which is syntactically correct, ignoring
     * the potential semantic restrictions applied to the field.
     */
    is_syntax_valid: function() {},
    /**
     * Must set the focus on the field. Return false if field is not focusable.
     */
    focus: function() {},
    /**
     * Called when the translate button is clicked.
     */
    on_translate: function() {},
    /**
        This method is called by the form view before reading on_change values and before saving. It tells
        the field to save its value before reading it using get_value(). Must return a promise.
    */
    commit_value: function() {},
};

/**
 * Abstract class for classes implementing FieldInterface.
 *
 * Properties:
 *     - value: useful property to hold the value of the field. By default, set_value() and get_value()
 *     set and retrieve the value property. Changing the value property also triggers automatically
 *     a 'changed_value' event that inform the view to trigger on_changes.
 *
 */
var AbstractField = FormWidget.extend(FieldInterface, {
    /**
     * @constructs instance.web.form.AbstractField
     * @extends instance.web.form.FormWidget
     *
     * @param field_manager
     * @param node
     */
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.name = this.node.attrs.name;
        this.field = this.field_manager.get_field_desc(this.name);
        this.widget = this.node.attrs.widget;
        this.string = this.node.attrs.string || this.field.string || this.name;
        this.options = pyeval.py_eval(this.node.attrs.options || '{}');
        this.set({'value': false});

        this.on("change:value", this, function() {
            this.trigger('changed_value');
            this._check_css_flags();
        });
    },
    renderElement: function() {
        var self = this;
        this._super();
        if (this.field.translate && this.view) {
            this.$el.addClass('oe_form_field_translatable');
            this.$el.find('.oe_field_translate').click(this.on_translate);
        }
        this.$label = this.view ? this.view.$el.find('label[for=' + this.id_for_label + ']') : $();
        this.do_attach_tooltip(this, this.$label[0] || this.$el);
        if (session.debug) {
            this.$label.off('dblclick').on('dblclick', function() {
                console.log("Field '%s' of type '%s' in View: %o", self.name, (self.node.attrs.widget || self.field.type), self.view);
                window.w = self;
                console.log("window.w =", window.w);
            });
        }
        if (!this.disable_utility_classes) {
            this.off("change:required", this, this._set_required);
            this.on("change:required", this, this._set_required);
            this._set_required();
        }
        this._check_visibility();
        this.field_manager.off("change:display_invalid_fields", this, this._check_css_flags);
        this.field_manager.on("change:display_invalid_fields", this, this._check_css_flags);
        this._check_css_flags();
    },
    start: function() {
        this._super();
        this.on("change:value", this, function() {
            if (! this.no_rerender)
                this.render_value();
        });
        this.render_value();
    },
    /**
     * Private. Do not use.
     */
    _set_required: function() {
        this.$el.toggleClass('oe_form_required', this.get("required"));
    },
    set_value: function(value_) {
        this.set({'value': value_});
    },
    get_value: function() {
        return this.get('value');
    },
    /**
        Utility method that all implementations should use to change the
        value without triggering a re-rendering.
    */
    internal_set_value: function(value_) {
        var tmp = this.no_rerender;
        this.no_rerender = true;
        this.set({'value': value_});
        this.no_rerender = tmp;
    },
    /**
        This method is called each time the value is modified.
    */
    render_value: function() {},
    is_valid: function() {
        return this.is_syntax_valid() && !(this.get('required') && this.is_false());
    },
    is_syntax_valid: function() {
        return true;
    },
    /**
     * Method useful to implement to ease validity testing. Must return true if the current
     * value is similar to false in OpenERP.
     */
    is_false: function() {
        return this.get('value') === false;
    },
    _check_css_flags: function() {
        if (this.field.translate) {
            this.$el.find('.oe_field_translate').toggle(this.field_manager.get('actual_mode') !== "create");
        }
        if (!this.disable_utility_classes) {
            if (this.field_manager.get('display_invalid_fields')) {
                this.$el.toggleClass('oe_form_invalid', !this.is_valid());
            }
        }
    },
    focus: function() {
        return false;
    },
    set_input_id: function(id) {
        this.id_for_label = id;
    },
    on_translate: function() {
        var self = this;
        var trans = new data.DataSet(this, 'ir.translation');
        return trans.call_button('translate_fields', [this.view.dataset.model, this.view.datarecord.id, this.name, this.view.dataset.get_context()]).done(function(r) {
            self.do_action(r);
        });
    },

    set_dimensions: function (height, width) {
        this.$el.css({
            width: width,
            minHeight: height
        });
    },
    commit_value: function() {
        return $.when();
    },
});

/**
 * Class with everything which is common between FormOpenPopup and SelectCreatePopup.
 */
var AbstractFormPopup = Widget.extend({
    template: "AbstractFormPopup.render",
    /**
     *  options:
     *  -readonly: only applicable when not in creation mode, default to false
     * - alternative_form_view
     * - view_id
     * - write_function
     * - read_function
     * - create_function
     * - parent_view
     * - child_name
     * - form_view_options
     */
    init_popup: function(model, row_id, domain, context, options) {
        this.row_id = row_id;
        this.model = model;
        this.domain = domain || [];
        this.context = context || {};
        this.options = options;
        _.defaults(this.options, {});
    },
    init_dataset: function() {
        var self = this;
        this.created_elements = [];
        this.dataset = new data.ProxyDataSet(this, this.model, this.context);
        this.dataset.read_function = this.options.read_function;
        this.dataset.create_function = function(data, options, sup) {
            var fct = self.options.create_function || sup;
            return fct.call(this, data, options).done(function(r) {
                self.trigger('create_completed saved', r);
                self.created_elements.push(r);
            });
        };
        this.dataset.write_function = function(id, data, options, sup) {
            var fct = self.options.write_function || sup;
            return fct.call(this, id, data, options).done(function(r) {
                self.trigger('write_completed saved', r);
            });
        };
        this.dataset.parent_view = this.options.parent_view;
        this.dataset.child_name = this.options.child_name;
    },
    display_popup: function() {
        var self = this;
        this.renderElement();
        var dialog = new Dialog(this, {
            dialogClass: 'oe_act_window',
            title: this.options.title || "",
        }, this.$el).open();
        dialog.on('closing', this, function (e){
            self.check_exit(true);
        });
        this.$buttonpane = dialog.$buttons;
        this.start();
    },
    setup_form_view: function() {
        var self = this;
        if (this.row_id) {
            this.dataset.ids = [this.row_id];
            this.dataset.index = 0;
        } else {
            this.dataset.index = null;
        }
        var options = _.clone(self.options.form_view_options) || {};
        if (this.row_id !== null) {
            options.initial_mode = this.options.readonly ? "view" : "edit";
        }
        _.extend(options, {
            $buttons: this.$buttonpane,
        });
        var FormView = core.view_registry.get('form');
        this.view_form = new FormView(this, this.dataset, this.options.view_id || false, options);
        if (this.options.alternative_form_view) {
            this.view_form.set_embedded_view(this.options.alternative_form_view);
        }
        this.view_form.appendTo(this.$(".oe_popup_form").show());
        this.view_form.on("form_view_loaded", self, function() {
            var multi_select = self.row_id === null && ! self.options.disable_multiple_selection;
            self.$buttonpane.html(QWeb.render("AbstractFormPopup.buttons", {
                multi_select: multi_select,
                readonly: self.row_id !== null && self.options.readonly,
            }));
            var $snbutton = self.$buttonpane.find(".oe_abstractformpopup-form-save-new");
            $snbutton.click(function() {
                $.when(self.view_form.save()).done(function() {
                    self.view_form.reload_mutex.exec(function() {
                        self.view_form.on_button_new();
                    });
                });
            });
            var $sbutton = self.$buttonpane.find(".oe_abstractformpopup-form-save");
            $sbutton.click(function() {
                $.when(self.view_form.save()).done(function() {
                    self.view_form.reload_mutex.exec(function() {
                        self.check_exit();
                    });
                });
            });
            var $cbutton = self.$buttonpane.find(".oe_abstractformpopup-form-close");
            $cbutton.click(function() {
                self.view_form.trigger('on_button_cancel');
                self.check_exit();
            });
            self.view_form.do_show();
        });
    },
    select_elements: function(element_ids) {
        this.trigger("elements_selected", element_ids);
    },
    check_exit: function(no_destroy) {
        if (this.created_elements.length > 0) {
            this.select_elements(this.created_elements);
            this.created_elements = [];
        }
        this.trigger('closed');
        this.destroy();
    },
    destroy: function () {
        this.trigger('closed');
        if (this.$el.is(":data(bs.modal)")) {
            this.$el.parents('.modal').modal('hide');
        }
        this._super();
    },
});

/**
 * Class to display a popup containing a form view.
 */
var FormOpenPopup = AbstractFormPopup.extend({
    show_element: function(model, row_id, context, options) {
        this.init_popup(model, row_id, [], context,  options);
        _.defaults(this.options, {
        });
        this.display_popup();
    },
    start: function() {
        this._super();
        this.init_dataset();
        this.setup_form_view();
    },
});

var SelectCreateListView = ListView.extend({
    do_add_record: function () {
        this.popup.new_object();
    },
    select_record: function(index) {
        this.popup.select_elements([this.dataset.ids[index]]);
        this.popup.destroy();
    },
    do_select: function(ids, records) {
        this._super(ids, records);
        this.popup.on_click_element(ids);
    }
});

/**
 * Class to display a popup to display a list to search a row. It also allows
 * to switch to a form view to create a new row.
 */
var SelectCreatePopup = AbstractFormPopup.extend({
    /**
     * options:
     * - initial_ids
     * - initial_view: form or search (default search)
     * - disable_multiple_selection
     * - list_view_options
     */
    select_element: function(model, options, domain, context) {
        this.init_popup(model, null, domain, context, options);
        _.defaults(this.options, {
            initial_view: "search",
        });
        this.initial_ids = this.options.initial_ids;
        this.display_popup();
    },
    start: function() {
        this.init_dataset();
        if (this.options.initial_view == "search") {
            var context = pyeval.sync_eval_domains_and_contexts({
                domains: [],
                contexts: [this.context]
            }).context;
            var search_defaults = {};
            _.each(context, function (value_, key) {
                var match = /^search_default_(.*)$/.exec(key);
                if (match) {
                    search_defaults[match[1]] = value_;
                }
            });
            this.setup_search_view(search_defaults);
        } else { // "form"
            this.new_object();
        }
    },
    setup_search_view: function(search_defaults) {
        var self = this;
        if (this.searchview) {
            this.searchview.destroy();
        }
        var $buttons = this.$('.o-search-options');
        this.searchview = new SearchView(this,
                this.dataset, false,  search_defaults, {$buttons: $buttons});
        this.searchview.on('search_data', self, function(domains, contexts, groupbys) {
            if (self.initial_ids) {
                self.do_search(domains.concat([[["id", "in", self.initial_ids]], self.domain]),
                    contexts.concat(self.context), groupbys);
                self.initial_ids = undefined;
            } else {
                self.do_search(domains.concat([self.domain]), contexts.concat(self.context), groupbys);
            }
        });
        this.searchview.appendTo(this.$(".o-popup-search")).done(function() {
            self.searchview.toggle_visibility(true);
            self.view_list = new SelectCreateListView(self,
                    self.dataset, false,
                    _.extend({'deletable': false,
                        'selectable': !self.options.disable_multiple_selection,
                        'import_enabled': false,
                        '$buttons': self.$buttonpane,
                        'disable_editable_mode': true,
                        '$pager': self.$('.oe_popup_list_pager'),
                    }, self.options.list_view_options || {}));
            self.view_list.on('edit:before', self, function (e) {
                e.cancel = true;
            });
            self.view_list.popup = self;
            self.view_list.appendTo(self.$(".oe_popup_list").show()).then(function() {
                self.view_list.do_show();
            }).then(function() {
                if (self.options.initial_facet) {
                    self.searchview.query.reset([self.options.initial_facet], {
                        preventSearch: true,
                    });
                }
                self.searchview.do_search();
            });
            self.view_list.on("list_view_loaded", self, function() {
                self.$buttonpane.html(QWeb.render("SelectCreatePopup.search.buttons", {widget:self}));
                var $cbutton = self.$buttonpane.find(".oe_selectcreatepopup-search-close");
                $cbutton.click(function() {
                    self.destroy();
                });
                var $sbutton = self.$buttonpane.find(".oe_selectcreatepopup-search-select");
                $sbutton.click(function() {
                    self.select_elements(self.selected_ids);
                    self.destroy();
                });
                $cbutton = self.$buttonpane.find(".oe_selectcreatepopup-search-create");
                $cbutton.click(function() {
                    self.new_object();
                });
            });
        });        
    },
    do_search: function(domains, contexts, groupbys) {
        var results = pyeval.sync_eval_domains_and_contexts({
            domains: domains || [],
            contexts: contexts || [],
            group_by_seq: groupbys || []
        });
        this.view_list.do_search(results.domain, results.context, results.group_by);
    },
    on_click_element: function(ids) {
        var self = this;
        this.selected_ids = ids || [];
        if(this.selected_ids.length > 0) {
            self.$buttonpane.find(".oe_selectcreatepopup-search-select").removeAttr('disabled');
        } else {
            self.$buttonpane.find(".oe_selectcreatepopup-search-select").attr('disabled', "disabled");
        }
    },
    new_object: function() {
        if (this.searchview) {
            this.searchview.toggle_visibility(false);
        }
        if (this.view_list) {
            this.view_list.do_hide();
            this.view_list.$el.parent().hide();
        }
        this.setup_form_view();
    },
});

var DomainEditorPopup = SelectCreatePopup.extend({
    select_element: function (model, options, domain, context) {
        if (options.readonly) {
            return this._super(model, options, domain, context);
        }
        options.initial_facet = {
            category: _t("Custom Filter"),
            icon: 'fa-star',
            field: {
                get_context: function () { return context; },
                get_groupby: function () { return []; },
                get_domain: function () { return domain; },
            },
            values: [{label: _t("Selected domain"), value: null}],            
        };
        this._super(model, options, [], context);
    },
    get_domain: function (selected_ids) {
        var group_domain = [],
            domain;
        if (this.$('input.oe_list_record_selector').prop('checked')) {
            if (this.view_list.grouped) {
                var group_domain = _.chain(_.values(this.view_list.groups.children))
                                        .filter(function (child) { return child.records.length; })
                                        .map(function (c) { return c.datagroup.domain;})
                                        .value();
                group_domain = _.flatten(group_domain, true);
                group_domain = _.times(group_domain.length - 1, _.constant('|')).concat(group_domain);
            }
            var search_data = this.searchview.build_search_data();
            domain = pyeval.sync_eval_domains_and_contexts({
                domains: search_data.domains,
                contexts: search_data.contexts,
                group_by_seq: search_data.groupbys || []
            }).domain;
        }
        else {
            domain = [["id", "in", selected_ids]];
        }
        return this.dataset.domain.concat(group_domain).concat(domain || []);
    },
});

return {
    // mixins
    FieldManagerMixin: FieldManagerMixin,
    ReinitializeWidgetMixin: ReinitializeWidgetMixin,
    ReinitializeFieldMixin: ReinitializeFieldMixin,
    CompletionFieldMixin: CompletionFieldMixin,

    // misc
    FormWidget: FormWidget,
    DefaultFieldManager: DefaultFieldManager,
    InvisibilityChanger: InvisibilityChanger,
    NotebookInvisibilityChanger: NotebookInvisibilityChanger,
    commands: commands,
    AbstractField: AbstractField,

    // popup dialogs
    AbstractFormPopup: AbstractFormPopup,
    FormOpenPopup: FormOpenPopup,
    SelectCreatePopup: SelectCreatePopup,
    DomainEditorPopup: DomainEditorPopup,
};

});