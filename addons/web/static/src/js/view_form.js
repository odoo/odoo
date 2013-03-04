openerp.web.form = function (instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;

/** @namespace */
instance.web.form = {};

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
instance.web.form.FieldManagerMixin = {
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

    @param (dict) values A dictonnary with key = field name and value = new value.
    @return (Deferred) Is resolved after all the values are setted.
    */
    set_values: function(values) {},
    /**
    Computes an OpenERP domain.

    @param (list) expression An OpenERP domain.
    @return (boolean) The computed value of the domain.
    */
    compute_domain: function(expression) {},
    /**
    Builds an evaluation context for the resolution of the fields' contexts. Please note
    the field are only supposed to use this context to evualuate their own, they should not
    extend it.

    @return (CompoundContext) An OpenERP context.
    */
    build_eval_context: function() {},
};

instance.web.views.add('form', 'instance.web.FormView');
/**
 * Properties:
 *      - actual_mode: always "view", "edit" or "create". Read-only property. Determines
 *      the mode used by the view.
 */
instance.web.FormView = instance.web.View.extend(instance.web.form.FieldManagerMixin, {
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable: false,
    template: "FormView",
    display_name: _lt('Form'),
    view_type: "form",
    /**
     * @constructs instance.web.FormView
     * @extends instance.web.View
     *
     * @param {instance.web.Session} session the current openerp session
     * @param {instance.web.DataSet} dataset the dataset this view will work with
     * @param {String} view_id the identifier of the OpenERP view object
     * @param {Object} options
     *                  - resize_textareas : [true|false|max_height]
     *
     * @property {instance.web.Registry} registry=instance.web.form.widgets widgets registry for this form view instance
     */
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id || false;
        this.fields_view = {};
        this.fields = {};
        this.fields_order = [];
        this.datarecord = {};
        this.default_focus_field = null;
        this.default_focus_button = null;
        this.fields_registry = instance.web.form.widgets;
        this.tags_registry = instance.web.form.tags;
        this.widgets_registry = instance.web.form.custom_widgets;
        this.has_been_loaded = $.Deferred();
        this.translatable_fields = [];
        _.defaults(this.options, {
            "not_interactible_on_create": false,
            "initial_mode": "view",
            "disable_autofocus": false,
            "footer_to_buttons": false,
        });
        this.is_initialized = $.Deferred();
        this.mutating_mutex = new $.Mutex();
        this.on_change_list = [];
        this.save_list = [];
        this.reload_mutex = new $.Mutex();
        this.__clicked_inside = false;
        this.__blur_timeout = null;
        this.rendering_engine = new instance.web.form.FormRenderingEngine(this);
        self.set({actual_mode: self.options.initial_mode});
        this.has_been_loaded.done(function() {
            self.on("change:actual_mode", self, self.check_actual_mode);
            self.check_actual_mode();
            self.on("change:actual_mode", self, self.init_pager);
            self.init_pager();
        });
        self.on("load_record", self, self.load_record);
        instance.web.bus.on('clear_uncommitted_changes', this, function(e) {
            if (!this.can_be_discarded()) {
                e.preventDefault();
            }
        });
    },
    view_loading: function(r) {
        return this.load_form(r);
    },
    destroy: function() {
        _.each(this.get_widgets(), function(w) {
            w.off('focused blurred');
            w.destroy();
        });
        if (this.$el) {
            this.$el.off('.formBlur');
        }
        this._super();
    },
    load_form: function(data) {
        var self = this;
        if (!data) {
            throw new Error(_t("No data provided."));
        }
        if (this.arch) {
            throw "Form view does not support multiple calls to load_form";
        }
        this.fields_order = [];
        this.fields_view = data;

        this.rendering_engine.set_fields_registry(this.fields_registry);
        this.rendering_engine.set_tags_registry(this.tags_registry);
        this.rendering_engine.set_widgets_registry(this.widgets_registry);
        this.rendering_engine.set_fields_view(data);
        var $dest = this.$el.hasClass("oe_form_container") ? this.$el : this.$el.find('.oe_form_container');
        this.rendering_engine.render_to($dest);

        this.$el.on('mousedown.formBlur', function () {
            self.__clicked_inside = true;
        });

        this.$buttons = $(QWeb.render("FormView.buttons", {'widget':self}));
        if (this.options.$buttons) {
            this.$buttons.appendTo(this.options.$buttons);
        } else {
            this.$el.find('.oe_form_buttons').replaceWith(this.$buttons);
        }
        this.$buttons.on('click', '.oe_form_button_create',
                         this.guard_active(this.on_button_create));
        this.$buttons.on('click', '.oe_form_button_edit',
                         this.guard_active(this.on_button_edit));
        this.$buttons.on('click', '.oe_form_button_save',
                         this.guard_active(this.on_button_save));
        this.$buttons.on('click', '.oe_form_button_cancel',
                         this.guard_active(this.on_button_cancel));
        if (this.options.footer_to_buttons) {
            this.$el.find('footer').appendTo(this.$buttons);
        }

        this.$sidebar = this.options.$sidebar || this.$el.find('.oe_form_sidebar');
        if (!this.sidebar && this.options.$sidebar) {
            this.sidebar = new instance.web.Sidebar(this);
            this.sidebar.appendTo(this.$sidebar);
            if (this.fields_view.toolbar) {
                this.sidebar.add_toolbar(this.fields_view.toolbar);
            }
            this.sidebar.add_items('other', _.compact([
                self.is_action_enabled('delete') && { label: _t('Delete'), callback: self.on_button_delete },
                self.is_action_enabled('create') && { label: _t('Duplicate'), callback: self.on_button_duplicate }
            ]));
        }

        this.has_been_loaded.resolve();

        // Add bounce effect on button 'Edit' when click on readonly page view.
        this.$el.find(".oe_form_group_row,.oe_form_field,label").on('click', function (e) {
            if(self.get("actual_mode") == "view") {
                var $button = self.options.$buttons.find(".oe_form_button_edit");
                $button.openerpBounce();
                e.stopPropagation();
                instance.web.bus.trigger('click', e);
            }
        });
        //bounce effect on red button when click on statusbar.
        this.$el.find(".oe_form_field_status:not(.oe_form_status_clickable)").on('click', function (e) {
            if((self.get("actual_mode") == "view")) {
                var $button = self.$el.find(".oe_highlight:not(.oe_form_invisible)").css({'float':'left','clear':'none'});
                $button.openerpBounce();
                e.stopPropagation();
            }
         });
        this.trigger('form_view_loaded', data);
        return $.when();
    },
    widgetFocused: function() {
        // Clear click flag if used to focus a widget
        this.__clicked_inside = false;
        if (this.__blur_timeout) {
            clearTimeout(this.__blur_timeout);
            this.__blur_timeout = null;
        }
    },
    widgetBlurred: function() {
        if (this.__clicked_inside) {
            // clicked in an other section of the form (than the currently
            // focused widget) => just ignore the blurring entirely?
            this.__clicked_inside = false;
            return;
        }
        var self = this;
        // clear timeout, if any
        this.widgetFocused();
        this.__blur_timeout = setTimeout(function () {
            self.trigger('blurred');
        }, 0);
    },

    do_load_state: function(state, warm) {
        if (state.id && this.datarecord.id != state.id) {
            if (this.dataset.get_id_index(state.id) === null) {
                this.dataset.ids.push(state.id);
            }
            this.dataset.select_id(state.id);
            this.do_show({ reload: warm });
        }
    },
    /**
     *
     * @param {Object} [options]
     * @param {Boolean} [mode=undefined] If specified, switch the form to specified mode. Can be "edit" or "view".
     * @param {Boolean} [reload=true] whether the form should reload its content on show, or use the currently loaded record
     * @return {$.Deferred}
     */
    do_show: function (options) {
        var self = this;
        options = options || {};
        if (this.sidebar) {
            this.sidebar.$el.show();
        }
        if (this.$buttons) {
            this.$buttons.show();
        }
        this.$el.show().css({
            opacity: '0',
            filter: 'alpha(opacity = 0)'
        });
        this.$el.add(this.$buttons).removeClass('oe_form_dirty');

        var shown = this.has_been_loaded;
        if (options.reload !== false) {
            shown = shown.then(function() {
                if (self.dataset.index === null) {
                    // null index means we should start a new record
                    return self.on_button_new();
                }
                var fields = _.keys(self.fields_view.fields);
                fields.push('display_name');
                return self.dataset.read_index(fields, {
                    context: { 'bin_size': true, 'future_display_name' : true }
                }).then(function(r) {
                    self.trigger('load_record', r);
                });
            });
        }
        return shown.then(function() {
            self._actualize_mode(options.mode || self.options.initial_mode);
            self.$el.css({
                opacity: '1',
                filter: 'alpha(opacity = 100)'
            });
        });
    },
    do_hide: function () {
        if (this.sidebar) {
            this.sidebar.$el.hide();
        }
        if (this.$buttons) {
            this.$buttons.hide();
        }
        if (this.$pager) {
            this.$pager.hide();
        }
        this._super();
    },
    load_record: function(record) {
        var self = this, set_values = [];
        if (!record) {
            this.set({ 'title' : undefined });
            this.do_warn(_t("Form"), _t("The record could not be found in the database."), true);
            return $.Deferred().reject();
        }
        this.datarecord = record;
        this._actualize_mode();
        this.set({ 'title' : record.id ? record.display_name : _t("New") });

        _(this.fields).each(function (field, f) {
            field._dirty_flag = false;
            field._inhibit_on_change_flag = true;
            var result = field.set_value(self.datarecord[f] || false);
            field._inhibit_on_change_flag = false;
            set_values.push(result);
        });
        return $.when.apply(null, set_values).then(function() {
            if (!record.id) {
                // New record: Second pass in order to trigger the onchanges
                // respecting the fields order defined in the view
                _.each(self.fields_order, function(field_name) {
                    if (record[field_name] !== undefined) {
                        var field = self.fields[field_name];
                        field._dirty_flag = true;
                        self.do_onchange(field);
                    }
                });
            }
            self.on_form_changed();
            self.rendering_engine.init_fields();
            self.is_initialized.resolve();
            self.do_update_pager(record.id == null);
            if (self.sidebar) {
               self.sidebar.do_attachement_update(self.dataset, self.datarecord.id);
            }
            if (record.id) {
                self.do_push_state({id:record.id});
            } else {
                self.do_push_state({});
            }
            self.$el.add(self.$buttons).removeClass('oe_form_dirty');
            self.autofocus();
        });
    },
    /**
     * Loads and sets up the default values for the model as the current
     * record
     *
     * @return {$.Deferred}
     */
    load_defaults: function () {
        var self = this;
        var keys = _.keys(this.fields_view.fields);
        if (keys.length) {
            return this.dataset.default_get(keys).then(function(r) {
                self.trigger('load_record', r);
            });
        }
        return self.trigger('load_record', {});
    },
    on_form_changed: function() {
        this.trigger("view_content_has_changed");
    },
    do_notify_change: function() {
        this.$el.add(this.$buttons).addClass('oe_form_dirty');
    },
    execute_pager_action: function(action) {
        if (this.can_be_discarded()) {
            switch (action) {
                case 'first':
                    this.dataset.index = 0;
                    break;
                case 'previous':
                    this.dataset.previous();
                    break;
                case 'next':
                    this.dataset.next();
                    break;
                case 'last':
                    this.dataset.index = this.dataset.ids.length - 1;
                    break;
            }
            this.reload();
            this.trigger('pager_action_executed');
        }
    },
    init_pager: function() {
        var self = this;
        if (this.$pager)
            this.$pager.remove();
        if (this.get("actual_mode") === "create")
            return;
        this.$pager = $(QWeb.render("FormView.pager", {'widget':self})).hide();
        if (this.options.$pager) {
            this.$pager.appendTo(this.options.$pager);
        } else {
            this.$el.find('.oe_form_pager').replaceWith(this.$pager);
        }
        this.$pager.on('click','a[data-pager-action]',function() {
            var action = $(this).data('pager-action');
            self.execute_pager_action(action);
        });
        this.do_update_pager();
    },
    do_update_pager: function(hide_index) {
        this.$pager.toggle(this.dataset.ids.length > 1);
        if (hide_index) {
            $(".oe_form_pager_state", this.$pager).html("");
        } else {
            $(".oe_form_pager_state", this.$pager).html(_.str.sprintf(_t("%d / %d"), this.dataset.index + 1, this.dataset.ids.length));
        }
    },
    parse_on_change: function (on_change, widget) {
        var self = this;
        var onchange = _.str.trim(on_change);
        var call = onchange.match(/^\s?(.*?)\((.*?)\)\s?$/);
        if (!call) {
            throw new Error(_.str.sprintf( _t("Wrong on change format: %s"), onchange ));
        }

        var method = call[1];
        if (!_.str.trim(call[2])) {
            return {method: method, args: []}
        }

        var argument_replacement = {
            'False': function () {return false;},
            'True': function () {return true;},
            'None': function () {return null;},
            'context': function () {
                return new instance.web.CompoundContext(
                        self.dataset.get_context(),
                        widget.build_context() ? widget.build_context() : {});
            }
        };
        var parent_fields = null;
        var args = _.map(call[2].split(','), function (a, i) {
            var field = _.str.trim(a);

            // literal constant or context
            if (field in argument_replacement) {
                return argument_replacement[field]();
            }
            // literal number
            if (/^-?\d+(\.\d+)?$/.test(field)) {
                return Number(field);
            }
            // form field
            if (self.fields[field]) {
                var value_ = self.fields[field].get_value();
                return value_ == null ? false : value_;
            }
            // parent field
            var splitted = field.split('.');
            if (splitted.length > 1 && _.str.trim(splitted[0]) === "parent" && self.dataset.parent_view) {
                if (parent_fields === null) {
                    parent_fields = self.dataset.parent_view.get_fields_values();
                }
                var p_val = parent_fields[_.str.trim(splitted[1])];
                if (p_val !== undefined) {
                    return p_val == null ? false : p_val;
                }
            }
            // string literal
            var first_char = field[0], last_char = field[field.length-1];
            if ((first_char === '"' && last_char === '"')
                || (first_char === "'" && last_char === "'")) {
                return field.slice(1, -1);
            }

            throw new Error("Could not get field with name '" + field +
                            "' for onchange '" + onchange + "'");
        });

        return {
            method: method,
            args: args
        };
    },
    do_onchange: function(widget, processed) {
        var self = this;
        this.on_change_list = [{widget: widget, processed: processed}].concat(this.on_change_list);
        return this._process_operations();
    },
    _process_onchange: function(on_change_obj) {
        var self = this;
        var widget = on_change_obj.widget;
        var processed = on_change_obj.processed;
        try {
            var def;
            processed = processed || [];
            processed.push(widget.name);
            var on_change = widget.node.attrs.on_change;
            if (on_change) {
                var change_spec = self.parse_on_change(on_change, widget);
                var ids = [];
                if (self.datarecord.id && !instance.web.BufferedDataSet.virtual_id_regex.test(self.datarecord.id)) {
                    // In case of a o2m virtual id, we should pass an empty ids list
                    ids.push(self.datarecord.id);
                }
                def = self.alive(new instance.web.Model(self.dataset.model).call(
                    change_spec.method, [ids].concat(change_spec.args)));
            } else {
                def = $.when({});
            }
            return def.then(function(response) {
                if (widget.field['change_default']) {
                    var fieldname = widget.name;
                    var value_;
                    if (response.value && (fieldname in response.value)) {
                        // Use value from onchange if onchange executed
                        value_ = response.value[fieldname];
                    } else {
                        // otherwise get form value for field
                        value_ = self.fields[fieldname].get_value();
                    }
                    var condition = fieldname + '=' + value_;

                    if (value_) {
                        return self.alive(new instance.web.Model('ir.values').call(
                            'get_defaults', [self.model, condition]
                        )).then(function (results) {
                            if (!results.length) {
                                return response;
                            }
                            if (!response.value) {
                                response.value = {};
                            }
                            for(var i=0; i<results.length; ++i) {
                                // [whatever, key, value]
                                var triplet = results[i];
                                response.value[triplet[1]] = triplet[2];
                            }
                            return response;
                        });
                    }
                }
                return response;
            }).then(function(response) {
                return self.on_processed_onchange(response, processed);
            });
        } catch(e) {
            console.error(e);
            instance.webclient.crashmanager.show_message(e);
            return $.Deferred().reject();
        }
    },
    on_processed_onchange: function(result, processed) {
        try {
        if (result.value) {
            this._internal_set_values(result.value, processed);
        }
        if (!_.isEmpty(result.warning)) {
            instance.web.dialog($(QWeb.render("CrashManager.warning", result.warning)), {
                title:result.warning.title,
                modal: true,
                buttons: [
                    {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
                ]
            });
        }

        var fields = this.fields;
        _(result.domain).each(function (domain, fieldname) {
            var field = fields[fieldname];
            if (!field) { return; }
            field.node.attrs.domain = domain;
        });

        return $.Deferred().resolve();
        } catch(e) {
            console.error(e);
            instance.webclient.crashmanager.show_message(e);
            return $.Deferred().reject();
        }
    },
    _process_operations: function() {
        var self = this;
        return this.mutating_mutex.exec(function() {
            function iterate() {
                var on_change_obj = self.on_change_list.shift();
                if (on_change_obj) {
                    return self._process_onchange(on_change_obj).then(function() {
                        return iterate();
                    });
                }
                var defs = [];
                _.each(self.fields, function(field) {
                    defs.push(field.commit_value());
                });
                var args = _.toArray(arguments);
                return $.when.apply($, defs).then(function() {
                    if (self.on_change_list.length !== 0) {
                        return iterate();
                    }
                    var save_obj = self.save_list.pop();
                    if (save_obj) {
                        return self._process_save(save_obj).then(function() {
                            save_obj.ret = _.toArray(arguments);
                            return iterate();
                        }, function() {
                            save_obj.error = true;
                        });
                    }
                    return $.when();
                });
            };
            return iterate();
        });
    },
    _internal_set_values: function(values, exclude) {
        exclude = exclude || [];
        for (var f in values) {
            if (!values.hasOwnProperty(f)) { continue; }
            var field = this.fields[f];
            // If field is not defined in the view, just ignore it
            if (field) {
                var value_ = values[f];
                if (field.get_value() != value_) {
                    field._inhibit_on_change_flag = true;
                    field.set_value(value_);
                    field._inhibit_on_change_flag = false;
                    field._dirty_flag = true;
                    if (!_.contains(exclude, field.name)) {
                        this.do_onchange(field, exclude);
                    }
                }
            }
        }
        this.on_form_changed();
    },
    set_values: function(values) {
        var self = this;
        return this.mutating_mutex.exec(function() {
            self._internal_set_values(values);
        });
    },
    /**
     * Ask the view to switch to view mode if possible. The view may not do it
     * if the current record is not yet saved. It will then stay in create mode.
     */
    to_view_mode: function() {
        this._actualize_mode("view");
    },
    /**
     * Ask the view to switch to edit mode if possible. The view may not do it
     * if the current record is not yet saved. It will then stay in create mode.
     */
    to_edit_mode: function() {
        this._actualize_mode("edit");
    },
    /**
     * Ask the view to switch to a precise mode if possible. The view is free to
     * not respect this command if the state of the dataset is not compatible with
     * the new mode. For example, it is not possible to switch to edit mode if
     * the current record is not yet saved in database.
     *
     * @param {string} [new_mode] Can be "edit", "view", "create" or undefined. If
     * undefined the view will test the actual mode to check if it is still consistent
     * with the dataset state.
     */
    _actualize_mode: function(switch_to) {
        var mode = switch_to || this.get("actual_mode");
        if (! this.datarecord.id) {
            mode = "create";
        } else if (mode === "create") {
            mode = "edit";
        }
        this.set({actual_mode: mode});
    },
    check_actual_mode: function(source, options) {
        var self = this;
        if(this.get("actual_mode") === "view") {
            self.$el.removeClass('oe_form_editable').addClass('oe_form_readonly');
            self.$buttons.find('.oe_form_buttons_edit').hide();
            self.$buttons.find('.oe_form_buttons_view').show();
            self.$sidebar.show();
        } else {
            self.$el.removeClass('oe_form_readonly').addClass('oe_form_editable');
            self.$buttons.find('.oe_form_buttons_edit').show();
            self.$buttons.find('.oe_form_buttons_view').hide();
            self.$sidebar.hide();
            this.autofocus();
        }
    },
    autofocus: function() {
        if (this.get("actual_mode") !== "view" && !this.options.disable_autofocus) {
            var fields_order = this.fields_order.slice(0);
            if (this.default_focus_field) {
                fields_order.unshift(this.default_focus_field.name);
            }
            for (var i = 0; i < fields_order.length; i += 1) {
                var field = this.fields[fields_order[i]];
                if (!field.get('effective_invisible') && !field.get('effective_readonly') && field.$label) {
                    if (field.focus() !== false) {
                        break;
                    }
                }
            }
        }
    },
    on_button_save: function() {
        var self = this;
        return this.save().done(function(result) {
            self.trigger("save", result);
            self.to_view_mode();
        });
    },
    on_button_cancel: function(event) {
        if (this.can_be_discarded()) {
            if (this.get('actual_mode') === 'create') {
                this.trigger('history_back');
            } else {
                this.to_view_mode();
                this.trigger('load_record', this.datarecord);
            }
        }
        this.trigger('on_button_cancel');
        return false;
    },
    on_button_new: function() {
        var self = this;
        this.to_edit_mode();
        return $.when(this.has_been_loaded).then(function() {
            if (self.can_be_discarded()) {
                return self.load_defaults();
            }
        });
    },
    on_button_edit: function() {
        return this.to_edit_mode();
    },
    on_button_create: function() {
        this.dataset.index = null;
        this.do_show();
    },
    on_button_duplicate: function() {
        var self = this;
        return this.has_been_loaded.then(function() {
            return self.dataset.call('copy', [self.datarecord.id, {}, self.dataset.context]).then(function(new_id) {
                self.record_created(new_id);
                self.to_edit_mode();
            });
        });
    },
    on_button_delete: function() {
        var self = this;
        var def = $.Deferred();
        this.has_been_loaded.done(function() {
            if (self.datarecord.id && confirm(_t("Do you really want to delete this record?"))) {
                self.dataset.unlink([self.datarecord.id]).done(function() {
                    self.execute_pager_action('next');
                    def.resolve();
                });
            } else {
                $.async_when().done(function () {
                    def.reject();
                })
            }
        });
        return def.promise();
    },
    can_be_discarded: function() {
        if (this.$el.is('.oe_form_dirty')) {
            if (!confirm(_t("Warning, the record has been modified, your changes will be discarded.\n\nAre you sure you want to leave this page ?"))) {
                return false;
            }
            this.$el.removeClass('oe_form_dirty');
        }
        return true;
    },
    /**
     * Triggers saving the form's record. Chooses between creating a new
     * record or saving an existing one depending on whether the record
     * already has an id property.
     *
     * @param {Boolean} [prepend_on_create=false] if ``save`` creates a new
     * record, should that record be inserted at the start of the dataset (by
     * default, records are added at the end)
     */
    save: function(prepend_on_create) {
        var self = this;
        var save_obj = {prepend_on_create: prepend_on_create, ret: null};
        this.save_list.push(save_obj);
        return this._process_operations().then(function() {
            if (save_obj.error)
                return $.Deferred().reject();
            return $.when.apply($, save_obj.ret);
        });
    },
    _process_save: function(save_obj) {
        var self = this;
        var prepend_on_create = save_obj.prepend_on_create;
        try {
            var form_invalid = false,
                values = {},
                first_invalid_field = null;
            for (var f in self.fields) {
                if (!self.fields.hasOwnProperty(f)) { continue; }
                f = self.fields[f];
                if (!f.is_valid()) {
                    form_invalid = true;
                    if (!first_invalid_field) {
                        first_invalid_field = f;
                    }
                } else if (f.name !== 'id' && !f.get("readonly") && (!self.datarecord.id || f._dirty_flag)) {
                    // Special case 'id' field, do not save this field
                    // on 'create' : save all non readonly fields
                    // on 'edit' : save non readonly modified fields
                    values[f.name] = f.get_value();
                }
            }
            if (form_invalid) {
                self.set({'display_invalid_fields': true});
                first_invalid_field.focus();
                self.on_invalid();
                return $.Deferred().reject();
            } else {
                self.set({'display_invalid_fields': false});
                var save_deferral;
                if (!self.datarecord.id) {
                    // Creation save
                    save_deferral = self.dataset.create(values).then(function(r) {
                        return self.record_created(r, prepend_on_create);
                    }, null);
                } else if (_.isEmpty(values)) {
                    // Not dirty, noop save
                    save_deferral = $.Deferred().resolve({}).promise();
                } else {
                    // Write save
                    save_deferral = self.dataset.write(self.datarecord.id, values, {}).then(function(r) {
                        return self.record_saved(r);
                    }, null);
                }
                return save_deferral;
            }
        } catch (e) {
            console.error(e);
            return $.Deferred().reject();
        }
    },
    on_invalid: function() {
        var warnings = _(this.fields).chain()
            .filter(function (f) { return !f.is_valid(); })
            .map(function (f) {
                return _.str.sprintf('<li>%s</li>',
                    _.escape(f.string));
            }).value();
        warnings.unshift('<ul>');
        warnings.push('</ul>');
        this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
    },
    /**
     * Reload the form after saving
     *
     * @param {Object} r result of the write function.
     */
    record_saved: function(r) {
        var self = this;
        if (!r) {
            // should not happen in the server, but may happen for internal purpose
            this.trigger('record_saved', r);
            return $.Deferred().reject();
        } else {
            return $.when(this.reload()).then(function () {
                self.trigger('record_saved', r);
                return r;
            });
        }
    },
    /**
     * Updates the form' dataset to contain the new record:
     *
     * * Adds the newly created record to the current dataset (at the end by
     *   default)
     * * Selects that record (sets the dataset's index to point to the new
     *   record's id).
     * * Updates the pager and sidebar displays
     *
     * @param {Object} r
     * @param {Boolean} [prepend_on_create=false] adds the newly created record
     * at the beginning of the dataset instead of the end
     */
    record_created: function(r, prepend_on_create) {
        var self = this;
        if (!r) {
            // should not happen in the server, but may happen for internal purpose
            this.trigger('record_created', r);
            return $.Deferred().reject();
        } else {
            this.datarecord.id = r;
            if (!prepend_on_create) {
                this.dataset.alter_ids(this.dataset.ids.concat([this.datarecord.id]));
                this.dataset.index = this.dataset.ids.length - 1;
            } else {
                this.dataset.alter_ids([this.datarecord.id].concat(this.dataset.ids));
                this.dataset.index = 0;
            }
            this.do_update_pager();
            if (this.sidebar) {
                this.sidebar.do_attachement_update(this.dataset, this.datarecord.id);
            }
            //openerp.log("The record has been created with id #" + this.datarecord.id);
            return $.when(this.reload()).then(function () {
                self.trigger('record_created', r);
                return _.extend(r, {created: true});
            });
        }
    },
    on_action: function (action) {
        console.debug('Executing action', action);
    },
    reload: function() {
        var self = this;
        return this.reload_mutex.exec(function() {
            if (self.dataset.index == null) {
                self.trigger("previous_view");
                return $.Deferred().reject().promise();
            }
            if (self.dataset.index == null || self.dataset.index < 0) {
                return $.when(self.on_button_new());
            } else {
                var fields = _.keys(self.fields_view.fields);
                fields.push('display_name');
                return self.dataset.read_index(fields,
                    {
                        context: {
                            'bin_size': true,
                            'future_display_name': true
                        }
                    }).then(function(r) {
                        self.trigger('load_record', r);
                    });
            }
        });
    },
    get_widgets: function() {
        return _.filter(this.getChildren(), function(obj) {
            return obj instanceof instance.web.form.FormWidget;
        });
    },
    get_fields_values: function() {
        var values = {};
        var ids = this.get_selected_ids();
        values["id"] = ids.length > 0 ? ids[0] : false;
        _.each(this.fields, function(value_, key) {
            values[key] = value_.get_value();
        });
        return values;
    },
    get_selected_ids: function() {
        var id = this.dataset.ids[this.dataset.index];
        return id ? [id] : [];
    },
    recursive_save: function() {
        var self = this;
        return $.when(this.save()).then(function(res) {
            if (self.dataset.parent_view)
                return self.dataset.parent_view.recursive_save();
        });
    },
    recursive_reload: function() {
        var self = this;
        var pre = $.when();
        if (self.dataset.parent_view)
                pre = self.dataset.parent_view.recursive_reload();
        return pre.then(function() {
            return self.reload();
        });
    },
    is_dirty: function() {
        return _.any(this.fields, function (value_) {
            return value_._dirty_flag;
        });
    },
    is_interactible_record: function() {
        var id = this.datarecord.id;
        if (!id) {
            if (this.options.not_interactible_on_create)
                return false;
        } else if (typeof(id) === "string") {
            if(instance.web.BufferedDataSet.virtual_id_regex.test(id))
                return false;
        }
        return true;
    },
    sidebar_eval_context: function () {
        return $.when(this.build_eval_context());
    },
    open_defaults_dialog: function () {
        var self = this;
        var display = function (field, value) {
            if (field instanceof instance.web.form.FieldSelection) {
                return _(field.values).find(function (option) {
                    return option[0] === value;
                })[1];
            } else if (field instanceof instance.web.form.FieldMany2One) {
                return field.get_displayed();
            }
            return value;
        }
        var fields = _.chain(this.fields)
            .map(function (field, name) {
                var value = field.get_value();
                // ignore fields which are empty, invisible, readonly, o2m
                // or m2m
                if (!value
                        || field.get('invisible')
                        || field.get("readonly")
                        || field.field.type === 'one2many'
                        || field.field.type === 'many2many'
                        || field.field.type === 'binary'
                        || field.password) {
                    return false;
                }

                return {
                    name: name,
                    string: field.string,
                    value: value,
                    displayed: display(field, value),
                }
            })
            .compact()
            .sortBy(function (field) { return field.string; })
            .value();
        var conditions = _.chain(self.fields)
            .filter(function (field) { return field.field.change_default; })
            .map(function (field, name) {
                var value = field.get_value();
                return {
                    name: name,
                    string: field.string,
                    value: value,
                    displayed: display(field, value),
                }
            })
            .value();

        var d = new instance.web.Dialog(this, {
            title: _t("Set Default"),
            args: {
                fields: fields,
                conditions: conditions
            },
            buttons: [
                {text: _t("Close"), click: function () { d.close(); }},
                {text: _t("Save default"), click: function () {
                    var $defaults = d.$el.find('#formview_default_fields');
                    var field_to_set = $defaults.val();
                    if (!field_to_set) {
                        $defaults.parent().addClass('oe_form_invalid');
                        return;
                    }
                    var condition = d.$el.find('#formview_default_conditions').val(),
                        all_users = d.$el.find('#formview_default_all').is(':checked');
                    new instance.web.DataSet(self, 'ir.values').call(
                        'set_default', [
                            self.dataset.model,
                            field_to_set,
                            self.fields[field_to_set].get_value(),
                            all_users,
                            true,
                            condition || false
                    ]).done(function () { d.close(); });
                }}
            ]
        });
        d.template = 'FormView.set_default';
        d.open();
    },
    register_field: function(field, name) {
        this.fields[name] = field;
        this.fields_order.push(name);
        if (JSON.parse(field.node.attrs.default_focus || "0")) {
            this.default_focus_field = field;
        }

        field.on('focused', null, this.proxy('widgetFocused'))
             .on('blurred', null, this.proxy('widgetBlurred'));
        if (this.get_field_desc(name).translate) {
            this.translatable_fields.push(field);
        }
        field.on('changed_value', this, function() {
            if (field.is_syntax_valid()) {
                this.trigger('field_changed:' + name);
            }
            if (field._inhibit_on_change_flag) {
                return;
            }
            field._dirty_flag = true;
            if (field.is_syntax_valid()) {
                this.do_onchange(field);
                this.on_form_changed(true);
                this.do_notify_change();
            }
        });
    },
    get_field_desc: function(field_name) {
        return this.fields_view.fields[field_name];
    },
    get_field_value: function(field_name) {
        return this.fields[field_name].get_value();
    },
    compute_domain: function(expression) {
        return instance.web.form.compute_domain(expression, this.fields);
    },
    _build_view_fields_values: function() {
        var a_dataset = this.dataset;
        var fields_values = this.get_fields_values();
        var active_id = a_dataset.ids[a_dataset.index];
        _.extend(fields_values, {
            active_id: active_id || false,
            active_ids: active_id ? [active_id] : [],
            active_model: a_dataset.model,
            parent: {}
        });
        if (a_dataset.parent_view) {
            fields_values.parent = a_dataset.parent_view.get_fields_values();
        }
        return fields_values;
    },
    build_eval_context: function() {
        var a_dataset = this.dataset;
        return new instance.web.CompoundContext(a_dataset.get_context(), this._build_view_fields_values());
    },
});

/**
 * Interface to be implemented by rendering engines for the form view.
 */
instance.web.form.FormRenderingEngineInterface = instance.web.Class.extend({
    set_fields_view: function(fields_view) {},
    set_fields_registry: function(fields_registry) {},
    render_to: function($el) {},
});

/**
 * Default rendering engine for the form view.
 *
 * It is necessary to set the view using set_view() before usage.
 */
instance.web.form.FormRenderingEngine = instance.web.form.FormRenderingEngineInterface.extend({
    init: function(view) {
        this.view = view;
    },
    set_fields_view: function(fvg) {
        this.fvg = fvg;
        this.version = parseFloat(this.fvg.arch.attrs.version);
        if (isNaN(this.version)) {
            this.version = 6.1;
        }
    },
    set_tags_registry: function(tags_registry) {
        this.tags_registry = tags_registry;
    },
    set_fields_registry: function(fields_registry) {
        this.fields_registry = fields_registry;
    },
    set_widgets_registry: function(widgets_registry) {
        this.widgets_registry = widgets_registry;
    },
    // Backward compatibility tools, current default version: v6.1
    process_version: function() {
        if (this.version < 7.0) {
            this.$form.find('form:first').wrapInner('<group col="4"/>');
            this.$form.find('page').each(function() {
                if (!$(this).parents('field').length) {
                    $(this).wrapInner('<group col="4"/>');
                }
            });
        }
    },
    get_arch_fragment: function() {
        var doc = $.parseXML(instance.web.json_node_to_xml(this.fvg.arch)).documentElement;
        // IE won't allow custom button@type and will revert it to spec default : 'submit'
        $('button', doc).each(function() {
            $(this).attr('data-button-type', $(this).attr('type')).attr('type', 'button');
        });
        // IE's html parser is also a css parser. How convenient...
        $('board', doc).each(function() {
            $(this).attr('layout', $(this).attr('style'));
        });
        return $('<div class="oe_form"/>').append(instance.web.xml_to_str(doc));
    },
    render_to: function($target) {
        var self = this;
        this.$target = $target;

        this.$form = this.get_arch_fragment();

        this.process_version();

        this.fields_to_init = [];
        this.tags_to_init = [];
        this.widgets_to_init = [];
        this.labels = {};
        this.process(this.$form);

        this.$form.appendTo(this.$target);

        this.to_replace = [];

        _.each(this.fields_to_init, function($elem) {
            var name = $elem.attr("name");
            if (!self.fvg.fields[name]) {
                throw new Error(_.str.sprintf(_t("Field '%s' specified in view could not be found."), name));
            }
            var obj = self.fields_registry.get_any([$elem.attr('widget'), self.fvg.fields[name].type]);
            if (!obj) {
                throw new Error(_.str.sprintf(_t("Widget type '%s' is not implemented"), $elem.attr('widget')));
            }
            var w = new (obj)(self.view, instance.web.xml_to_json($elem[0]));
            var $label = self.labels[$elem.attr("name")];
            if ($label) {
                w.set_input_id($label.attr("for"));
            }
            self.alter_field(w);
            self.view.register_field(w, $elem.attr("name"));
            self.to_replace.push([w, $elem]);
        });
        _.each(this.tags_to_init, function($elem) {
            var tag_name = $elem[0].tagName.toLowerCase();
            var obj = self.tags_registry.get_object(tag_name);
            var w = new (obj)(self.view, instance.web.xml_to_json($elem[0]));
            self.to_replace.push([w, $elem]);
        });
        _.each(this.widgets_to_init, function($elem) {
            var widget_type = $elem.attr("type");
            var obj = self.widgets_registry.get_object(widget_type);
            var w = new (obj)(self.view, instance.web.xml_to_json($elem[0]));
            self.to_replace.push([w, $elem]);
        });
    },
    init_fields: function() {
        var defs = [];
        _.each(this.to_replace, function(el) {
            defs.push(el[0].replace(el[1]));
        });
        this.to_replace = [];
        return $.when.apply($, defs);
    },
    render_element: function(template /* dictionaries */) {
        var dicts = [].slice.call(arguments).slice(1);
        var dict = _.extend.apply(_, dicts);
        dict['classnames'] = dict['class'] || ''; // class is a reserved word and might caused problem to Safari when used from QWeb
        return $(QWeb.render(template, dict));
    },
    alter_field: function(field) {
    },
    toggle_layout_debugging: function() {
        if (!this.$target.has('.oe_layout_debug_cell:first').length) {
            this.$target.find('[title]').removeAttr('title');
            this.$target.find('.oe_form_group_cell').each(function() {
                var text = 'W:' + ($(this).attr('width') || '') + ' - C:' + $(this).attr('colspan');
                $(this).attr('title', text);
            });
        }
        this.$target.toggleClass('oe_layout_debugging');
    },
    process: function($tag) {
        var self = this;
        var tagname = $tag[0].nodeName.toLowerCase();
        if (this.tags_registry.contains(tagname)) {
            this.tags_to_init.push($tag);
            return $tag;
        }
        var fn = self['process_' + tagname];
        if (fn) {
            var args = [].slice.call(arguments);
            args[0] = $tag;
            return fn.apply(self, args);
        } else {
            // generic tag handling, just process children
            $tag.children().each(function() {
                self.process($(this));
            });
            self.handle_common_properties($tag, $tag);
            $tag.removeAttr("modifiers");
            return $tag;
        }
    },
    process_widget: function($widget) {
        this.widgets_to_init.push($widget);
        return $widget;
    },
    process_sheet: function($sheet) {
        var $new_sheet = this.render_element('FormRenderingSheet', $sheet.getAttributes());
        this.handle_common_properties($new_sheet, $sheet);
        var $dst = $new_sheet.find('.oe_form_sheet');
        $sheet.contents().appendTo($dst);
        $sheet.before($new_sheet).remove();
        this.process($new_sheet);
    },
    process_form: function($form) {
        if ($form.find('> sheet').length === 0) {
            $form.addClass('oe_form_nosheet');
        }
        var $new_form = this.render_element('FormRenderingForm', $form.getAttributes());
        this.handle_common_properties($new_form, $form);
        $form.contents().appendTo($new_form);
        if ($form[0] === this.$form[0]) {
            // If root element, replace it
            this.$form = $new_form;
        } else {
            $form.before($new_form).remove();
        }
        this.process($new_form);
    },
    /*
     * Used by direct <field> children of a <group> tag only
     * This method will add the implicit <label...> for every field
     * in the <group>
    */
    preprocess_field: function($field) {
        var self = this;
        var name = $field.attr('name'),
            field_colspan = parseInt($field.attr('colspan'), 10),
            field_modifiers = JSON.parse($field.attr('modifiers') || '{}');

        if ($field.attr('nolabel') === '1')
            return;
        $field.attr('nolabel', '1');
        var found = false;
        this.$form.find('label[for="' + name + '"]').each(function(i ,el) {
            $(el).parents().each(function(unused, tag) {
                var name = tag.tagName.toLowerCase();
                if (name === "field" || name in self.tags_registry.map)
                    found = true;
            });
        });
        if (found)
            return;

        var $label = $('<label/>').attr({
            'for' : name,
            "modifiers": JSON.stringify({invisible: field_modifiers.invisible}),
            "string": $field.attr('string'),
            "help": $field.attr('help'),
            "class": $field.attr('class'),
        });
        $label.insertBefore($field);
        if (field_colspan > 1) {
            $field.attr('colspan', field_colspan - 1);
        }
        return $label;
    },
    process_field: function($field) {
        if ($field.parent().is('group')) {
            // No implicit labels for normal fields, only for <group> direct children
            var $label = this.preprocess_field($field);
            if ($label) {
                this.process($label);
            }
        }
        this.fields_to_init.push($field);
        return $field;
    },
    process_group: function($group) {
        var self = this;
        $group.children('field').each(function() {
            self.preprocess_field($(this));
        });
        var $new_group = this.render_element('FormRenderingGroup', $group.getAttributes());
        var $table;
        if ($new_group.first().is('table.oe_form_group')) {
            $table = $new_group;
        } else if ($new_group.filter('table.oe_form_group').length) {
            $table = $new_group.filter('table.oe_form_group').first();
        } else {
            $table = $new_group.find('table.oe_form_group').first();
        }

        var $tr, $td,
            cols = parseInt($group.attr('col') || 2, 10),
            row_cols = cols;

        var children = [];
        $group.children().each(function(a,b,c) {
            var $child = $(this);
            var colspan = parseInt($child.attr('colspan') || 1, 10);
            var tagName = $child[0].tagName.toLowerCase();
            var $td = $('<td/>').addClass('oe_form_group_cell').attr('colspan', colspan);
            var newline = tagName === 'newline';

            // Note FME: those classes are used in layout debug mode
            if ($tr && row_cols > 0 && (newline || row_cols < colspan)) {
                $tr.addClass('oe_form_group_row_incomplete');
                if (newline) {
                    $tr.addClass('oe_form_group_row_newline');
                }
            }
            if (newline) {
                $tr = null;
                return;
            }
            if (!$tr || row_cols < colspan) {
                $tr = $('<tr/>').addClass('oe_form_group_row').appendTo($table);
                row_cols = cols;
            } else if (tagName==='group') {
                // When <group> <group/><group/> </group>, we need a spacing between the two groups
                $td.addClass('oe_group_right')
            }
            row_cols -= colspan;

            // invisibility transfer
            var field_modifiers = JSON.parse($child.attr('modifiers') || '{}');
            var invisible = field_modifiers.invisible;
            self.handle_common_properties($td, $("<dummy>").attr("modifiers", JSON.stringify({invisible: invisible})));

            $tr.append($td.append($child));
            children.push($child[0]);
        });
        if (row_cols && $td) {
            $td.attr('colspan', parseInt($td.attr('colspan'), 10) + row_cols);
        }
        $group.before($new_group).remove();

        $table.find('> tbody > tr').each(function() {
            var to_compute = [],
                row_cols = cols,
                total = 100;
            $(this).children().each(function() {
                var $td = $(this),
                    $child = $td.children(':first');
                switch ($child[0].tagName.toLowerCase()) {
                    case 'separator':
                        break;
                    case 'label':
                        if ($child.attr('for')) {
                            $td.attr('width', '1%').addClass('oe_form_group_cell_label');
                            row_cols-= $td.attr('colspan') || 1;
                            total--;
                        }
                        break;
                    default:
                        var width = _.str.trim($child.attr('width') || ''),
                            iwidth = parseInt(width, 10);
                        if (iwidth) {
                            if (width.substr(-1) === '%') {
                                total -= iwidth;
                                width = iwidth + '%';
                            } else {
                                // Absolute width
                                $td.css('min-width', width + 'px');
                            }
                            $td.attr('width', width);
                            $child.removeAttr('width');
                            row_cols-= $td.attr('colspan') || 1;
                        } else {
                            to_compute.push($td);
                        }

                }
            });
            if (row_cols) {
                var unit = Math.floor(total / row_cols);
                if (!$(this).is('.oe_form_group_row_incomplete')) {
                    _.each(to_compute, function($td, i) {
                        var width = parseInt($td.attr('colspan'), 10) * unit;
                        $td.attr('width', width + '%');
                        total -= width;
                    });
                }
            }
        });
        _.each(children, function(el) {
            self.process($(el));
        });
        this.handle_common_properties($new_group, $group);
        return $new_group;
    },
    process_notebook: function($notebook) {
        var self = this;
        var pages = [];
        $notebook.find('> page').each(function() {
            var $page = $(this);
            var page_attrs = $page.getAttributes();
            page_attrs.id = _.uniqueId('notebook_page_');
            var $new_page = self.render_element('FormRenderingNotebookPage', page_attrs);
            $page.contents().appendTo($new_page);
            $page.before($new_page).remove();
            var ic = self.handle_common_properties($new_page, $page).invisibility_changer;
            page_attrs.__page = $new_page;
            page_attrs.__ic = ic;
            pages.push(page_attrs);

            $new_page.children().each(function() {
                self.process($(this));
            });
        });
        var $new_notebook = this.render_element('FormRenderingNotebook', { pages : pages });
        $notebook.contents().appendTo($new_notebook);
        $notebook.before($new_notebook).remove();
        self.process($($new_notebook.children()[0]));
        //tabs and invisibility handling
        $new_notebook.tabs();
        _.each(pages, function(page, i) {
            if (! page.__ic)
                return;
            page.__ic.on("change:effective_invisible", null, function() {
                if (!page.__ic.get('effective_invisible')) {
                    $new_notebook.tabs('select', i);
                    return;
                }
                var current = $new_notebook.tabs("option", "selected");
                if (! pages[current].__ic || ! pages[current].__ic.get("effective_invisible"))
                    return;
                var first_visible = _.find(_.range(pages.length), function(i2) {
                    return (! pages[i2].__ic) || (! pages[i2].__ic.get("effective_invisible"));
                });
                if (first_visible !== undefined) {
                    $new_notebook.tabs('select', first_visible);
                }
            });
        });

        this.handle_common_properties($new_notebook, $notebook);
        return $new_notebook;
    },
    process_separator: function($separator) {
        var $new_separator = this.render_element('FormRenderingSeparator', $separator.getAttributes());
        $separator.before($new_separator).remove();
        this.handle_common_properties($new_separator, $separator);
        return $new_separator;
    },
    process_label: function($label) {
        var name = $label.attr("for"),
            field_orm = this.fvg.fields[name];
        var dict = {
            string: $label.attr('string') || (field_orm || {}).string || '',
            help: $label.attr('help') || (field_orm || {}).help || '',
            _for: name ? _.uniqueId('oe-field-input-') : undefined,
        };
        var align = parseFloat(dict.align);
        if (isNaN(align) || align === 1) {
            align = 'right';
        } else if (align === 0) {
            align = 'left';
        } else {
            align = 'center';
        }
        dict.align = align;
        var $new_label = this.render_element('FormRenderingLabel', dict);
        $label.before($new_label).remove();
        this.handle_common_properties($new_label, $label);
        if (name) {
            this.labels[name] = $new_label;
        }
        return $new_label;
    },
    handle_common_properties: function($new_element, $node) {
        var str_modifiers = $node.attr("modifiers") || "{}";
        var modifiers = JSON.parse(str_modifiers);
        var ic = null;
        if (modifiers.invisible !== undefined)
            ic = new instance.web.form.InvisibilityChanger(this.view, this.view, modifiers.invisible, $new_element);
        $new_element.addClass($node.attr("class") || "");
        $new_element.attr('style', $node.attr('style'));
        return {invisibility_changer: ic,};
    },
});

/**
    Welcome.

    If you read this documentation, it probably means that you were asked to use a form view widget outside of
    a form view. Before going further, you must understand that those fields were never really created for
    that usage. Don't think that this class will hold the answer to all your problems, at best it will allow
    you to hack the system with more style.
*/
instance.web.form.DefaultFieldManager = instance.web.Widget.extend({
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
        return instance.web.form.compute_domain(expression, {});
    },
    build_eval_context: function() {
        return new instance.web.CompoundContext(this.eval_context);
    },
});

instance.web.form.compute_domain = function(expr, fields) {
    if (! (expr instanceof Array))
        return !! expr;
    var stack = [];
    for (var i = expr.length - 1; i >= 0; i--) {
        var ex = expr[i];
        if (ex.length == 1) {
            var top = stack.pop();
            switch (ex) {
                case '|':
                    stack.push(stack.pop() || top);
                    continue;
                case '&':
                    stack.push(stack.pop() && top);
                    continue;
                case '!':
                    stack.push(!top);
                    continue;
                default:
                    throw new Error(_.str.sprintf(
                        _t("Unknown operator %s in domain %s"),
                        ex, JSON.stringify(expr)));
            }
        }

        var field = fields[ex[0]];
        if (!field) {
            throw new Error(_.str.sprintf(
                _t("Unknown field %s in domain %s"),
                ex[0], JSON.stringify(expr)));
        }
        var field_value = field.get_value ? field.get_value() : field.value;
        var op = ex[1];
        var val = ex[2];

        switch (op.toLowerCase()) {
            case '=':
            case '==':
                stack.push(_.isEqual(field_value, val));
                break;
            case '!=':
            case '<>':
                stack.push(!_.isEqual(field_value, val));
                break;
            case '<':
                stack.push(field_value < val);
                break;
            case '>':
                stack.push(field_value > val);
                break;
            case '<=':
                stack.push(field_value <= val);
                break;
            case '>=':
                stack.push(field_value >= val);
                break;
            case 'in':
                if (!_.isArray(val)) val = [val];
                stack.push(_(val).contains(field_value));
                break;
            case 'not in':
                if (!_.isArray(val)) val = [val];
                stack.push(!_(val).contains(field_value));
                break;
            default:
                console.warn(
                    _t("Unsupported operator %s in domain %s"),
                    op, JSON.stringify(expr));
        }
    }
    return _.all(stack, _.identity);
};

instance.web.form.is_bin_size = function(v) {
    return /^\d+(\.\d*)? \w+$/.test(v);
};

/**
 * Must be applied over an class already possessing the PropertiesMixin.
 *
 * Apply the result of the "invisible" domain to this.$el.
 */
instance.web.form.InvisibilityChangerMixin = {
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

instance.web.form.InvisibilityChanger = instance.web.Class.extend(instance.web.PropertiesMixin, instance.web.form.InvisibilityChangerMixin, {
    init: function(parent, field_manager, invisible_domain, $el) {
        this.setParent(parent);
        instance.web.PropertiesMixin.init.call(this);
        instance.web.form.InvisibilityChangerMixin.init.call(this, field_manager, invisible_domain);
        this.$el = $el;
        this.start();
    },
});

/**
    Base class for all fields, custom widgets and buttons to be displayed in the form view.

    Properties:
        - effective_readonly: when it is true, the widget is displayed as readonly. Vary depending
        the values of the "readonly" property and the "mode" property on the field manager.
*/
instance.web.form.FormWidget = instance.web.Widget.extend(instance.web.form.InvisibilityChangerMixin, {
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
        if (this.field_manager instanceof instance.web.FormView)
            this.view = this.field_manager;
        this.node = node;
        this.modifiers = JSON.parse(this.node.attrs.modifiers || '{}');
        instance.web.form.InvisibilityChangerMixin.init.call(this, this.field_manager, this.modifiers.invisible);

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
        $.fn.tipsy.clear();
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
                delayIn: 500,
                delayOut: 0,
                fade: true,
                title: function() {
                    var template = widget.template + '.tooltip';
                    if (!QWeb.has_template(template)) {
                        template = 'WidgetLabel.tooltip';
                    }
                    return QWeb.render(template, {
                        debug: instance.session.debug,
                        widget: widget
                })},
                gravity: $.fn.tipsy.autoBounds(50, 'nw'),
                html: true,
                opacity: 0.85,
                trigger: 'hover'
            }, options || {});
        $(trigger).tipsy(options);
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
            v_context = new instance.web.CompoundContext(v_context).set_eval_context(fields_values);
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
            final_domain = new instance.web.CompoundDomain(final_domain).set_eval_context(fields_values);
        }
        return final_domain;
    }
});

instance.web.form.WidgetButton = instance.web.form.FormWidget.extend({
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
        if (this.node.attrs.icon && (! /\//.test(this.node.attrs.icon))) {
            this.node.attrs.icon = '/web/static/src/img/icons/' + this.node.attrs.icon + '.png';
        }
        this.view.on('view_content_has_changed', this, this.check_disable);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$el.click(this.on_click);
        if (this.node.attrs.help || instance.session.debug) {
            this.do_attach_tooltip();
        }
        this.setupFocus(this.$el);
    },
    on_click: function() {
        var self = this;
        this.force_disabled = true;
        this.check_disable();
        this.execute_action().always(function() {
            self.force_disabled = false;
            self.check_disable();
        });
    },
    execute_action: function() {
        var self = this;
        var exec_action = function() {
            if (self.node.attrs.confirm) {
                var def = $.Deferred();
                var dialog = instance.web.dialog($('<div/>').text(self.node.attrs.confirm), {
                    title: _t('Confirm'),
                    modal: true,
                    buttons: [
                        {text: _t("Cancel"), click: function() {
                                $(this).dialog("close");
                            }
                        },
                        {text: _t("Ok"), click: function() {
                                var self2 = this;
                                self.on_confirmed().always(function() {
                                    $(self2).dialog("close");
                                });
                            }
                        },
                    ],
                    beforeClose: function() {
                        def.resolve();
                    },
                });
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
            this.view.dataset, this.view.datarecord.id, function () {
                self.view.recursive_reload();
            });
    },
    check_disable: function() {
        var disabled = (this.force_disabled || !this.view.is_interactible_record());
        this.$el.prop('disabled', disabled);
        this.$el.css('color', disabled ? 'grey' : '');
    }
});

/**
 * Interface to be implemented by fields.
 *
 * Events:
 *     - changed_value: triggered when the value of the field has changed. This can be due
 *      to a user interaction or a call to set_value().
 *
 */
instance.web.form.FieldInterface = {
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
instance.web.form.AbstractField = instance.web.form.FormWidget.extend(instance.web.form.FieldInterface, {
    /**
     * @constructs instance.web.form.AbstractField
     * @extends instance.web.form.FormWidget
     *
     * @param field_manager
     * @param node
     */
    init: function(field_manager, node) {
        var self = this
        this._super(field_manager, node);
        this.name = this.node.attrs.name;
        this.field = this.field_manager.get_field_desc(this.name);
        this.widget = this.node.attrs.widget;
        this.string = this.node.attrs.string || this.field.string || this.name;
        this.options = instance.web.py_eval(this.node.attrs.options || '{}');
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
        if (instance.session.debug) {
            this.do_attach_tooltip(this, this.$label[0] || this.$el);
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
        var tmp = this._super();
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
        var tmp = this.no_render;
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
        var trans = new instance.web.DataSet(this, 'ir.translation');
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
 * A mixin to apply on any FormWidget that has to completely re-render when its readonly state
 * switch.
 */
instance.web.form.ReinitializeWidgetMixin =  {
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
instance.web.form.ReinitializeFieldMixin =  _.extend({}, instance.web.form.ReinitializeWidgetMixin, {
    reinitialize: function() {
        instance.web.form.ReinitializeWidgetMixin.reinitialize.call(this);
        this.render_value();
    },
});

/**
    Some hack to make placeholders work in ie9.
*/
if ($.browser.msie && $.browser.version === "9.0") {
    document.addEventListener("DOMNodeInserted",function(event){
        var nodename =  event.target.nodeName.toLowerCase();
        if ( nodename === "input" || nodename == "textarea" ) {
            $(event.target).placeholder();
        }
    });
}

instance.web.form.FieldChar = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldChar',
    widget_class: 'oe_form_field_char',
    events: {
        'change input': 'store_dom_value',
    },
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.password = this.node.attrs.password === 'True' || this.node.attrs.password === '1';
    },
    initialize_content: function() {
        this.setupFocus(this.$('input'));
    },
    store_dom_value: function () {
        if (!this.get('effective_readonly')
                && this.$('input').length
                && this.is_syntax_valid()) {
            this.internal_set_value(
                this.parse_value(
                    this.$('input').val()));
        }
    },
    commit_value: function () {
        this.store_dom_value();
        return this._super();
    },
    render_value: function() {
        var show_value = this.format_value(this.get('value'), '');
        if (!this.get("effective_readonly")) {
            this.$el.find('input').val(show_value);
        } else {
            if (this.password) {
                show_value = new Array(show_value.length + 1).join('*');
            }
            this.$(".oe_form_char_content").text(show_value);
        }
    },
    is_syntax_valid: function() {
        if (!this.get("effective_readonly") && this.$("input").size() > 0) {
            try {
                this.parse_value(this.$('input').val(), '');
                return true;
            } catch(e) {
                return false;
            }
        }
        return true;
    },
    parse_value: function(val, def) {
        return instance.web.parse_value(val, this, def);
    },
    format_value: function(val, def) {
        return instance.web.format_value(val, this, def);
    },
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    focus: function() {
        this.$('input:first')[0].focus();
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        this.$('input').css({
            height: height,
            width: width
        });
    }
});

instance.web.form.FieldID = instance.web.form.FieldChar.extend({
    process_modifiers: function () {
        this._super();
        this.set({ readonly: true });
    },
});

instance.web.form.FieldEmail = instance.web.form.FieldChar.extend({
    template: 'FieldEmail',
    initialize_content: function() {
        this._super();
        var $button = this.$el.find('button');
        $button.click(this.on_button_clicked);
        this.setupFocus($button);
    },
    render_value: function() {
        if (!this.get("effective_readonly")) {
            this._super();
        } else {
            this.$el.find('a')
                    .attr('href', 'mailto:' + this.get('value'))
                    .text(this.get('value') || '');
        }
    },
    on_button_clicked: function() {
        if (!this.get('value') || !this.is_syntax_valid()) {
            this.do_warn(_t("E-mail error"), _t("Can't send email to invalid e-mail address"));
        } else {
            location.href = 'mailto:' + this.get('value');
        }
    }
});

instance.web.form.FieldUrl = instance.web.form.FieldChar.extend({
    template: 'FieldUrl',
    initialize_content: function() {
        this._super();
        var $button = this.$el.find('button');
        $button.click(this.on_button_clicked);
        this.setupFocus($button);
    },
    render_value: function() {
        if (!this.get("effective_readonly")) {
            this._super();
        } else {
            var tmp = this.get('value');
            var s = /(\w+):(.+)|^\.{0,2}\//.exec(tmp);
            if (!s) {
                tmp = "http://" + this.get('value');
            }
            this.$el.find('a').attr('href', tmp).text(this.get('value') ? tmp : '');
        }
    },
    on_button_clicked: function() {
        if (!this.get('value')) {
            this.do_warn(_t("Resource error"), _t("This resource is empty"));
        } else {
            var url = $.trim(this.get('value'));
            if(/^www\./i.test(url))
                url = 'http://'+url;
            window.open(url);
        }
    }
});

instance.web.form.FieldFloat = instance.web.form.FieldChar.extend({
    is_field_number: true,
    widget_class: 'oe_form_field_float',
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.internal_set_value(0);
        if (this.node.attrs.digits) {
            this.digits = this.node.attrs.digits;
        } else {
            this.digits = this.field.digits;
        }
    },
    set_value: function(value_) {
        if (value_ === false || value_ === undefined) {
            // As in GTK client, floats default to 0
            value_ = 0;
        }
        this._super.apply(this, [value_]);
    },
    focus: function () {
        this.$('input:first').select();
    }
});

instance.web.DateTimeWidget = instance.web.Widget.extend({
    template: "web.datepicker",
    jqueryui_object: 'datetimepicker',
    type_of_date: "datetime",
    events: {
        'change .oe_datepicker_master': 'change_datetime',
        'dragstart img.oe_datepicker_trigger': function () { return false; },
    },
    init: function(parent) {
        this._super(parent);
        this.name = parent.name;
    },
    start: function() {
        var self = this;
        this.$input = this.$el.find('input.oe_datepicker_master');
        this.$input_picker = this.$el.find('input.oe_datepicker_container');

        this.picker({
            onClose: this.on_picker_select,
            onSelect: this.on_picker_select,
            changeMonth: true,
            changeYear: true,
            showWeek: true,
            showButtonPanel: true,
            firstDay: Date.CultureInfo.firstDayOfWeek
        });
        // Some clicks in the datepicker dialog are not stopped by the
        // datepicker and "bubble through", unexpectedly triggering the bus's
        // click event. Prevent that.
        this.picker('widget').click(function (e) { e.stopPropagation(); });

        this.$el.find('img.oe_datepicker_trigger').click(function() {
            if (self.get("effective_readonly") || self.picker('widget').is(':visible')) {
                self.$input.focus();
                return;
            }
            self.picker('setDate', self.get('value') ? instance.web.auto_str_to_date(self.get('value')) : new Date());
            self.$input_picker.show();
            self.picker('show');
            self.$input_picker.hide();
        });
        this.set_readonly(false);
        this.set({'value': false});
    },
    picker: function() {
        return $.fn[this.jqueryui_object].apply(this.$input_picker, arguments);
    },
    on_picker_select: function(text, instance_) {
        var date = this.picker('getDate');
        this.$input
            .val(date ? this.format_client(date) : '')
            .change()
            .focus();
    },
    set_value: function(value_) {
        this.set({'value': value_});
        this.$input.val(value_ ? this.format_client(value_) : '');
    },
    get_value: function() {
        return this.get('value');
    },
    set_value_from_ui_: function() {
        var value_ = this.$input.val() || false;
        this.set({'value': this.parse_client(value_)});
    },
    set_readonly: function(readonly) {
        this.readonly = readonly;
        this.$input.prop('readonly', this.readonly);
        this.$el.find('img.oe_datepicker_trigger').toggleClass('oe_input_icon_disabled', readonly);
    },
    is_valid_: function() {
        var value_ = this.$input.val();
        if (value_ === "") {
            return true;
        } else {
            try {
                this.parse_client(value_);
                return true;
            } catch(e) {
                return false;
            }
        }
    },
    parse_client: function(v) {
        return instance.web.parse_value(v, {"widget": this.type_of_date});
    },
    format_client: function(v) {
        return instance.web.format_value(v, {"widget": this.type_of_date});
    },
    change_datetime: function() {
        if (this.is_valid_()) {
            this.set_value_from_ui_();
            this.trigger("datetime_changed");
        }
    },
    commit_value: function () {
        this.change_datetime();
    },
});

instance.web.DateWidget = instance.web.DateTimeWidget.extend({
    jqueryui_object: 'datepicker',
    type_of_date: "date"
});

instance.web.form.FieldDatetime = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: "FieldDatetime",
    build_widget: function() {
        return new instance.web.DateTimeWidget(this);
    },
    destroy_content: function() {
        if (this.datewidget) {
            this.datewidget.destroy();
            this.datewidget = undefined;
        }
    },
    initialize_content: function() {
        if (!this.get("effective_readonly")) {
            this.datewidget = this.build_widget();
            this.datewidget.on('datetime_changed', this, _.bind(function() {
                this.internal_set_value(this.datewidget.get_value());
            }, this));
            this.datewidget.appendTo(this.$el);
            this.setupFocus(this.datewidget.$input);
        }
    },
    render_value: function() {
        if (!this.get("effective_readonly")) {
            this.datewidget.set_value(this.get('value'));
        } else {
            this.$el.text(instance.web.format_value(this.get('value'), this, ''));
        }
    },
    is_syntax_valid: function() {
        if (!this.get("effective_readonly") && this.datewidget) {
            return this.datewidget.is_valid_();
        }
        return true;
    },
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    focus: function() {
        if (this.datewidget && this.datewidget.$input) {
            this.datewidget.$input[0].focus();
        }
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        this.datewidget.$input.css('height', height);
    }
});

instance.web.form.FieldDate = instance.web.form.FieldDatetime.extend({
    template: "FieldDate",
    build_widget: function() {
        return new instance.web.DateWidget(this);
    }
});

instance.web.form.FieldText = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldText',
    events: {
        'keyup': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                e.stopPropagation();
            }
        },
        'change textarea': 'store_dom_value',
    },
    init: function (field_manager, node) {
        this._super(field_manager, node);
    },
    initialize_content: function() {
        var self = this;
        this.$textarea = this.$el.find('textarea');
        this.auto_sized = false;
        this.default_height = this.$textarea.css('height');
        if (this.get("effective_readonly")) {
            this.$textarea.attr('disabled', 'disabled');
        }
        this.setupFocus(this.$textarea);
    },
    commit_value: function () {
        this.store_dom_value();
        return this._super();
    },
    store_dom_value: function () {
        if (!this.get('effective_readonly') && this.$('textarea').length) {
            this.internal_set_value(
                instance.web.parse_value(
                    this.$textarea.val(),
                    this));
        }
    },
    render_value: function() {
        var show_value = instance.web.format_value(this.get('value'), this, '');
        if (show_value === '') {
            this.$textarea.css('height', parseInt(this.default_height)+"px");
        }
        this.$textarea.val(show_value);
        if (! this.auto_sized) {
            this.auto_sized = true;
            this.$textarea.autosize();
        } else {
            this.$textarea.trigger("autosize");
        }
    },
    is_syntax_valid: function() {
        if (!this.get("effective_readonly") && this.$textarea) {
            try {
                instance.web.parse_value(this.$textarea.val(), this, '');
                return true;
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
        this.$textarea[0].focus();
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        this.$textarea.css({
            width: width,
            minHeight: height
        });
    },
});

/**
 * FieldTextHtml Widget
 * Intended for FieldText widgets meant to display HTML content. This
 * widget will instantiate the CLEditor (see cleditor in static/src/lib)
 * To find more information about CLEditor configutation: go to
 * http://premiumsoftware.net/cleditor/docs/GettingStarted.html
 */
instance.web.form.FieldTextHtml = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldTextHtml',
    init: function() {
        this._super.apply(this, arguments);
    },
    initialize_content: function() {
        var self = this;
        if (! this.get("effective_readonly")) {
            self._updating_editor = false;
            this.$textarea = this.$el.find('textarea');
            var width = ((this.node.attrs || {}).editor_width || '100%');
            var height = ((this.node.attrs || {}).editor_height || 250);
            this.$textarea.cleditor({
                width:      width, // width not including margins, borders or padding
                height:     height, // height not including margins, borders or padding
                controls:   // controls to add to the toolbar
                            "bold italic underline strikethrough " +
                            "| removeformat | bullets numbering | outdent " +
                            "indent | link unlink | source",
                bodyStyle:  // style to assign to document body contained within the editor
                            "margin:4px; color:#4c4c4c; font-size:13px; font-family:\"Lucida Grande\",Helvetica,Verdana,Arial,sans-serif; cursor:text"
            });
            this.$cleditor = this.$textarea.cleditor()[0];
            this.$cleditor.change(function() {
                if (! self._updating_editor) {
                    self.$cleditor.updateTextArea();
                    self.internal_set_value(self.$textarea.val());
                }
            });
        }
    },
    render_value: function() {
        if (! this.get("effective_readonly")) {
            this.$textarea.val(this.get('value') || '');
            this._updating_editor = true;
            this.$cleditor.updateFrame();
            this._updating_editor = false;
        } else {
            this.$el.html(this.get('value'));
        }
    },
});

instance.web.form.FieldBoolean = instance.web.form.AbstractField.extend({
    template: 'FieldBoolean',
    start: function() {
        var self = this;
        this.$checkbox = $("input", this.$el);
        this.setupFocus(this.$checkbox);
        this.$el.click(_.bind(function() {
            this.internal_set_value(this.$checkbox.is(':checked'));
        }, this));
        var check_readonly = function() {
            self.$checkbox.prop('disabled', self.get("effective_readonly"));
        };
        this.on("change:effective_readonly", this, check_readonly);
        check_readonly.call(this);
        this._super.apply(this, arguments);
    },
    render_value: function() {
        this.$checkbox[0].checked = this.get('value');
    },
    focus: function() {
        this.$checkbox[0].focus();
    }
});

/**
    The progressbar field expect a float from 0 to 100.
*/
instance.web.form.FieldProgressBar = instance.web.form.AbstractField.extend({
    template: 'FieldProgressBar',
    render_value: function() {
        this.$el.progressbar({
            value: this.get('value') || 0,
            disabled: this.get("effective_readonly")
        });
        var formatted_value = instance.web.format_value(this.get('value') || 0, { type : 'float' });
        this.$('span').html(formatted_value + '%');
    }
});


instance.web.form.FieldSelection = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldSelection',
    events: {
        'change select': 'store_dom_value',
    },
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.values = _(this.field.selection).chain()
            .reject(function (v) { return v[0] === false && v[1] === ''; })
            .unshift([false, ''])
            .value();
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
        //   changing the selected value), takes the action as validating the
        //   row
        var ischanging = false;
        var $select = this.$el.find('select')
            .change(function () { ischanging = true; })
            .click(function () { ischanging = false; })
            .keyup(function (e) {
                if (e.which !== 13 || !ischanging) { return; }
                e.stopPropagation();
                ischanging = false;
            });
        this.setupFocus($select);
    },
    commit_value: function () {
        this.store_dom_value();
        return this._super();
    },
    store_dom_value: function () {
        if (!this.get('effective_readonly') && this.$('select').length) {
            this.internal_set_value(
                this.values[this.$('select')[0].selectedIndex][0]);
        }
    },
    set_value: function(value_) {
        value_ = value_ === null ? false : value_;
        value_ = value_ instanceof Array ? value_[0] : value_;
        this._super(value_);
    },
    render_value: function() {
        if (!this.get("effective_readonly")) {
            var index = 0;
            for (var i = 0, ii = this.values.length; i < ii; i++) {
                if (this.values[i][0] === this.get('value')) index = i;
            }
            this.$el.find('select')[0].selectedIndex = index;
        } else {
            var self = this;
            var option = _(this.values)
                .detect(function (record) { return record[0] === self.get('value'); });
            this.$el.text(option ? option[1] : this.values[0][1]);
        }
    },
    focus: function() {
        this.$('select:first')[0].focus();
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        this.$('select').css({
            height: height,
            width: width
        });
    }
});

// jquery autocomplete tweak to allow html and classnames
(function() {
    var proto = $.ui.autocomplete.prototype,
        initSource = proto._initSource;

    function filter( array, term ) {
        var matcher = new RegExp( $.ui.autocomplete.escapeRegex(term), "i" );
        return $.grep( array, function(value_) {
            return matcher.test( $( "<div>" ).html( value_.label || value_.value || value_ ).text() );
        });
    }

    $.extend( proto, {
        _initSource: function() {
            if ( this.options.html && $.isArray(this.options.source) ) {
                this.source = function( request, response ) {
                    response( filter( this.options.source, request.term ) );
                };
            } else {
                initSource.call( this );
            }
        },

        _renderItem: function( ul, item) {
            return $( "<li></li>" )
                .data( "item.autocomplete", item )
                .append( $( "<a></a>" )[ this.options.html ? "html" : "text" ]( item.label ) )
                .appendTo( ul )
                .addClass(item.classname);
        }
    });
})();

/**
 * A mixin containing some useful methods to handle completion inputs.
 */
instance.web.form.CompletionFieldMixin = {
    init: function() {
        this.limit = 7;
        this.orderer = new instance.web.DropMisordered();
    },
    /**
     * Call this method to search using a string.
     */
    get_search_result: function(search_val) {
        var self = this;

        var dataset = new instance.web.DataSet(this, this.field.relation, self.build_context());
        var blacklist = this.get_search_blacklist();
        this.last_query = search_val;

        return this.orderer.add(dataset.name_search(
                search_val, new instance.web.CompoundDomain(self.build_domain(), [["id", "not in", blacklist]]),
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
                        dataset.name_search(search_val, self.build_domain(), 'ilike', false).done(function(data) {
                            self._search_create_popup("search", data);
                        });
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            // quick create
            var raw_result = _(data.result).map(function(x) {return x[1];});
            if (search_val.length > 0 && !_.include(raw_result, search_val)) {
                values.push({
                    label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                        $('<span />').text(search_val).html()),
                    action: function() {
                        self._quick_create(search_val);
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            // create...
            values.push({
                label: _t("Create and Edit..."),
                action: function() {
                    self._search_create_popup("form", undefined, self._create_context(search_val));
                },
                classname: 'oe_m2o_dropdown_option'
            });

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
            new instance.web.DataSet(this, this.field.relation, self.build_context())
                .name_create(name).done(function(data) {
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
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.select_element(
            self.field.relation,
            {
                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
                initial_ids: ids ? _.map(ids, function(x) {return x[0]}) : undefined,
                initial_view: view,
                disable_multiple_selection: true
            },
            self.build_domain(),
            new instance.web.CompoundContext(self.build_context(), context || {})
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

instance.web.form.M2ODialog = instance.web.Dialog.extend({
    template: "M2ODialog",
    init: function(parent) {
        this._super(parent, {
            title: _.str.sprintf(_t("Add %s"), parent.string),
            width: 312,
        });
    },
    start: function() {
        var self = this;
        this.$buttons.html(QWeb.render("M2ODialog.buttons"));
        this.$("input").val(this.getParent().last_query);
        this.$buttons.find(".oe_form_m2o_qc_button").click(function(){
            self.getParent()._quick_create(self.$("input").val());
            self.destroy();
        });
        this.$buttons.find(".oe_form_m2o_sc_button").click(function(){
            self.getParent()._search_create_popup("form", undefined, self.getParent()._create_context(self.$("input").val()));
            self.destroy();
        });
        this.$buttons.find(".oe_form_m2o_cancel_button").click(function(){
            self.destroy();
        });
    },
});

instance.web.form.FieldMany2One = instance.web.form.AbstractField.extend(instance.web.form.CompletionFieldMixin, instance.web.form.ReinitializeFieldMixin, {
    template: "FieldMany2One",
    events: {
        'keydown input': function (e) {
            switch (e.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                e.stopPropagation();
            }
        },
        'dragstart .oe_m2o_drop_down_button img': function () { return false; },
        'dragstart .oe_m2o_cm_button': function () { return false; }
    },
    init: function(field_manager, node) {
        this._super(field_manager, node);
        instance.web.form.CompletionFieldMixin.init.call(this);
        this.set({'value': false});
        this.display_value = {};
        this.last_search = [];
        this.floating = false;
        this.current_display = null;
        this.is_started = false;
    },
    reinit_value: function(val) {
        this.internal_set_value(val);
        this.floating = false;
        if (this.is_started)
            this.render_value();
    },
    initialize_field: function() {
        this.is_started = true;
        instance.web.bus.on('click', this, function() {
            if (!this.get("effective_readonly") && this.$input && this.$input.autocomplete('widget').is(':visible')) {
                this.$input.autocomplete("close");
            }
        });
        instance.web.form.ReinitializeFieldMixin.initialize_field.call(this);
    },
    initialize_content: function() {
        if (!this.get("effective_readonly"))
            this.render_editable();
    },
    init_error_displayer: function() {
        // nothing
    },
    hide_error_displayer: function() {
        // doesn't work
    },
    show_error_displayer: function() {
        new instance.web.form.M2ODialog(this).open();
    },
    render_editable: function() {
        var self = this;
        this.$input = this.$el.find("input");

        this.init_error_displayer();

        self.$input.on('focus', function() {
            self.hide_error_displayer();
        });

        this.$drop_down = this.$el.find(".oe_m2o_drop_down_button");
        this.$follow_button = $(".oe_m2o_cm_button", this.$el);

        this.$follow_button.click(function(ev) {
            ev.preventDefault();
            if (!self.get('value')) {
                self.focus();
                return;
            }
            var pop = new instance.web.form.FormOpenPopup(self);
            pop.show_element(
                self.field.relation,
                self.get("value"),
                self.build_context(),
                {
                    title: _t("Open: ") + self.string
                }
            );
            pop.on('write_completed', self, function(){
                self.display_value = {};
                self.render_value();
                self.focus();
            });
        });

        // some behavior for input
        var input_changed = function() {
            if (self.current_display !== self.$input.val()) {
                self.current_display = self.$input.val();
                if (self.$input.val() === "") {
                    self.internal_set_value(false);
                    self.floating = false;
                } else {
                    self.floating = true;
                }
            }
        };
        this.$input.keydown(input_changed);
        this.$input.change(input_changed);
        this.$drop_down.click(function() {
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");
                self.$input.focus();
            } else {
                if (self.get("value") && ! self.floating) {
                    self.$input.autocomplete("search", "");
                } else {
                    self.$input.autocomplete("search");
                }
            }
        });

        // Autocomplete close on dialog content scroll
        var close_autocomplete = _.debounce(function() {
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");
            }
        }, 50);
        this.$input.closest(".ui-dialog .ui-dialog-content").on('scroll', this, close_autocomplete);

        self.ed_def = $.Deferred();
        self.uned_def = $.Deferred();
        var ed_delay = 200;
        var ed_duration = 15000;
        var anyoneLoosesFocus = function (e) {
            var used = false;
            if (self.floating) {
                if (self.last_search.length > 0) {
                    if (self.last_search[0][0] != self.get("value")) {
                        self.display_value = {};
                        self.display_value["" + self.last_search[0][0]] = self.last_search[0][1];
                        self.reinit_value(self.last_search[0][0]);
                    } else {
                        used = true;
                        self.render_value();
                    }
                } else {
                    used = true;
                    self.reinit_value(false);
                }
                self.floating = false;
            }
            if (used && self.get("value") === false && ! self.no_ed) {
                self.ed_def.reject();
                self.uned_def.reject();
                self.ed_def = $.Deferred();
                self.ed_def.done(function() {
                    self.show_error_displayer();
                    ignore_blur = false;
                    self.trigger('focused');
                });
                ignore_blur = true;
                setTimeout(function() {
                    self.ed_def.resolve();
                    self.uned_def.reject();
                    self.uned_def = $.Deferred();
                    self.uned_def.done(function() {
                        self.hide_error_displayer();
                    });
                    setTimeout(function() {self.uned_def.resolve();}, ed_duration);
                }, ed_delay);
            } else {
                self.no_ed = false;
                self.ed_def.reject();
            }
        };
        var ignore_blur = false;
        this.$input.on({
            focusout: anyoneLoosesFocus,
            focus: function () { self.trigger('focused'); },
            autocompleteopen: function () { ignore_blur = true; },
            autocompleteclose: function () { ignore_blur = false; },
            blur: function () {
                // autocomplete open
                if (ignore_blur) { return; }
                if (_(self.getChildren()).any(function (child) {
                    return child instanceof instance.web.form.AbstractFormPopup;
                })) { return; }
                self.trigger('blurred');
            }
        });

        var isSelecting = false;
        // autocomplete
        this.$input.autocomplete({
            source: function(req, resp) {
                self.get_search_result(req.term).done(function(result) {
                    resp(result);
                });
            },
            select: function(event, ui) {
                isSelecting = true;
                var item = ui.item;
                if (item.id) {
                    self.display_value = {};
                    self.display_value["" + item.id] = item.name;
                    self.reinit_value(item.id);
                } else if (item.action) {
                    item.action();
                    // Cancel widget blurring, to avoid form blur event
                    self.trigger('focused');
                    return false;
                }
            },
            focus: function(e, ui) {
                e.preventDefault();
            },
            html: true,
            // disabled to solve a bug, but may cause others
            //close: anyoneLoosesFocus,
            minLength: 0,
            delay: 0
        });
        this.$input.autocomplete("widget").openerpClass();
        // used to correct a bug when selecting an element by pushing 'enter' in an editable list
        this.$input.keyup(function(e) {
            if (e.which === 13) { // ENTER
                if (isSelecting)
                    e.stopPropagation();
            }
            isSelecting = false;
        });
        this.setupFocus(this.$follow_button);
    },
    render_value: function(no_recurse) {
        var self = this;
        if (! this.get("value")) {
            this.display_string("");
            return;
        }
        var display = this.display_value["" + this.get("value")];
        if (display) {
            this.display_string(display);
            return;
        }
        if (! no_recurse) {
            var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
            dataset.name_get([self.get("value")]).done(function(data) {
                self.display_value["" + self.get("value")] = data[0][1];
                self.render_value(true);
            });
        }
    },
    display_string: function(str) {
        var self = this;
        if (!this.get("effective_readonly")) {
            this.$input.val(str.split("\n")[0]);
            this.current_display = this.$input.val();
            if (this.is_false()) {
                this.$('.oe_m2o_cm_button').css({'display':'none'});
            } else {
                this.$('.oe_m2o_cm_button').css({'display':'inline'});
            }
        } else {
            var lines = _.escape(str).split("\n");
            var link = "";
            var follow = "";
            link = lines[0];
            follow = _.rest(lines).join("<br />");
            if (follow)
                link += "<br />";
            var $link = this.$el.find('.oe_form_uri')
                 .unbind('click')
                 .html(link);
            if (! this.options.no_open)
                $link.click(function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        views: [[false, 'form']],
                        target: 'current'
                    });
                    return false;
                 });
            $(".oe_form_m2o_follow", this.$el).html(follow);
        }
    },
    set_value: function(value_) {
        var self = this;
        if (value_ instanceof Array) {
            this.display_value = {};
            if (! this.options.always_reload) {
                this.display_value["" + value_[0]] = value_[1];
            }
            value_ = value_[0];
        }
        value_ = value_ || false;
        this.reinit_value(value_);
    },
    get_displayed: function() {
        return this.display_value["" + this.get("value")];
    },
    add_id: function(id) {
        this.display_value = {};
        this.reinit_value(id);
    },
    is_false: function() {
        return ! this.get("value");
    },
    focus: function () {
        if (!this.get('effective_readonly')) {
            this.$input[0].focus();
        }
    },
    _quick_create: function() {
        this.no_ed = true;
        this.ed_def.reject();
        return instance.web.form.CompletionFieldMixin._quick_create.apply(this, arguments);
    },
    _search_create_popup: function() {
        this.no_ed = true;
        this.ed_def.reject();
        return instance.web.form.CompletionFieldMixin._search_create_popup.apply(this, arguments);
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        this.$input.css('height', height);
    }
});

instance.web.form.Many2OneButton = instance.web.form.AbstractField.extend({
    template: 'Many2OneButton',
    init: function(field_manager, node) {
        this._super.apply(this, arguments);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.set_button();
    },
    set_button: function() {
        var self = this;
        if (this.$button) {
            this.$button.remove();
        }
        this.string = '';
        this.node.attrs.icon = this.get('value') ? '/web/static/src/img/icons/gtk-yes.png' : '/web/static/src/img/icons/gtk-no.png';
        this.$button = $(QWeb.render('WidgetButton', {'widget': this}));
        this.$button.addClass('oe_link').css({'padding':'4px'});
        this.$el.append(this.$button);
        this.$button.on('click', self.on_click);
    },
    on_click: function(ev) {
        var self = this;
        this.popup =  new instance.web.form.FormOpenPopup(this);
        this.popup.show_element(
            this.field.relation,
            this.get('value'),
            this.build_context(),
            {title: this.string}
        );
        this.popup.on('create_completed', self, function(r) {
            self.set_value(r);
        });
    },
    set_value: function(value_) {
        var self = this;
        if (value_ instanceof Array) {
            value_ = value_[0];
        }
        value_ = value_ || false;
        this.set('value', value_);
        this.set_button();
     },
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
instance.web.form.FieldOne2Many = instance.web.form.AbstractField.extend({
    multi_selection: false,
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        lazy_build_o2m_kanban_view();
        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;
        this.form_last_update = $.Deferred();
        this.init_form_last_update = this.form_last_update;
        this.is_started = false;
        this.dataset = new instance.web.form.One2ManyDataSet(this, this.field.relation);
        this.dataset.o2m = this;
        this.dataset.parent_view = this.view;
        this.dataset.child_name = this.name;
        var self = this;
        this.dataset.on('dataset_changed', this, function() {
            self.trigger_on_change();
        });
        this.set_value([]);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('oe_form_field oe_form_field_one2many');

        var self = this;

        self.load_views();
        this.is_loaded.done(function() {
            self.on("change:effective_readonly", self, function() {
                self.is_loaded = self.is_loaded.then(function() {
                    self.viewmanager.destroy();
                    return $.when(self.load_views()).done(function() {
                        self.reload_current_view();
                    });
                });
            });
        });
        this.is_started = true;
        this.reload_current_view();
    },
    trigger_on_change: function() {
        this.trigger('changed_value');
    },
    load_views: function() {
        var self = this;

        var modes = this.node.attrs.mode;
        modes = !!modes ? modes.split(",") : ["tree"];
        var views = [];
        _.each(modes, function(mode) {
            if (! _.include(["list", "tree", "graph", "kanban"], mode)) {
                throw new Error(_.str.sprintf(_t("View type '%s' is not supported in One2Many."), mode));
            }
            var view = {
                view_id: false,
                view_type: mode == "tree" ? "list" : mode,
                options: {}
            };
            if (self.field.views && self.field.views[mode]) {
                view.embedded_view = self.field.views[mode];
            }
            if(view.view_type === "list") {
                _.extend(view.options, {
                    addable: null,
                    selectable: self.multi_selection,
                    sortable: false,
                    import_enabled: false,
                    deletable: true
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        deletable: null,
                        reorderable: false,
                    });
                }
            } else if (view.view_type === "form") {
                if (self.get("effective_readonly")) {
                    view.view_type = 'form';
                }
                _.extend(view.options, {
                    not_interactible_on_create: true,
                });
            } else if (view.view_type === "kanban") {
                _.extend(view.options, {
                    confirm_on_delete: false,
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        action_buttons: false,
                        quick_creatable: false,
                        creatable: false,
                        read_only_mode: true,
                    });
                }
            }
            views.push(view);
        });
        this.views = views;

        this.viewmanager = new instance.web.form.One2ManyViewManager(this, this.dataset, views, {});
        this.viewmanager.o2m = self;
        var once = $.Deferred().done(function() {
            self.init_form_last_update.resolve();
        });
        var def = $.Deferred().done(function() {
            self.initial_is_loaded.resolve();
        });
        this.viewmanager.on("controller_inited", self, function(view_type, controller) {
            controller.o2m = self;
            if (view_type == "list") {
                if (self.get("effective_readonly")) {
                    controller.on('edit:before', self, function (e) {
                        e.cancel = true;
                    });
                    _(controller.columns).find(function (column) {
                        if (!(column instanceof instance.web.list.Handle)) {
                            return false;
                        }
                        column.modifiers.invisible = true;
                        return true;
                    });
                }
            } else if (view_type === "form") {
                if (self.get("effective_readonly")) {
                    $(".oe_form_buttons", controller.$el).children().remove();
                }
                controller.on("load_record", self, function(){
                     once.resolve();
                 });
                controller.on('pager_action_executed',self,self.save_any_view);
            } else if (view_type == "graph") {
                self.reload_current_view()
            }
            def.resolve();
        });
        this.viewmanager.on("switch_mode", self, function(n_mode, b, c, d, e) {
            $.when(self.save_any_view()).done(function() {
                if (n_mode === "list") {
                    $.async_when().done(function() {
                        self.reload_current_view();
                    });
                }
            });
        });
        $.async_when().done(function () {
            self.viewmanager.appendTo(self.$el);
        });
        return def;
    },
    reload_current_view: function() {
        var self = this;
        return self.is_loaded = self.is_loaded.then(function() {
            var active_view = self.viewmanager.active_view;
            var view = self.viewmanager.views[active_view].controller;
            if(active_view === "list") {
                return view.reload_content();
            } else if (active_view === "form") {
                if (self.dataset.index === null && self.dataset.ids.length >= 1) {
                    self.dataset.index = 0;
                }
                var act = function() {
                    return view.do_show();
                };
                self.form_last_update = self.form_last_update.then(act, act);
                return self.form_last_update;
            } else if (view.do_search) {
                return view.do_search(self.build_domain(), self.dataset.get_context(), []);
            }
        }, undefined);
    },
    set_value: function(value_) {
        value_ = value_ || [];
        var self = this;
        this.dataset.reset_ids([]);
        if(value_.length >= 1 && value_[0] instanceof Array) {
            var ids = [];
            _.each(value_, function(command) {
                var obj = {values: command[2]};
                switch (command[0]) {
                    case commands.CREATE:
                        obj['id'] = _.uniqueId(self.dataset.virtual_id_prefix);
                        obj.defaults = {};
                        self.dataset.to_create.push(obj);
                        self.dataset.cache.push(_.extend(_.clone(obj), {values: _.clone(command[2])}));
                        ids.push(obj.id);
                        return;
                    case commands.UPDATE:
                        obj['id'] = command[1];
                        self.dataset.to_write.push(obj);
                        self.dataset.cache.push(_.extend(_.clone(obj), {values: _.clone(command[2])}));
                        ids.push(obj.id);
                        return;
                    case commands.DELETE:
                        self.dataset.to_delete.push({id: command[1]});
                        return;
                    case commands.LINK_TO:
                        ids.push(command[1]);
                        return;
                    case commands.DELETE_ALL:
                        self.dataset.delete_all = true;
                        return;
                }
            });
            this._super(ids);
            this.dataset.set_ids(ids);
        } else if (value_.length >= 1 && typeof(value_[0]) === "object") {
            var ids = [];
            this.dataset.delete_all = true;
            _.each(value_, function(command) {
                var obj = {values: command};
                obj['id'] = _.uniqueId(self.dataset.virtual_id_prefix);
                obj.defaults = {};
                self.dataset.to_create.push(obj);
                self.dataset.cache.push(_.clone(obj));
                ids.push(obj.id);
            });
            this._super(ids);
            this.dataset.set_ids(ids);
        } else {
            this._super(value_);
            this.dataset.reset_ids(value_);
        }
        if (this.dataset.index === null && this.dataset.ids.length > 0) {
            this.dataset.index = 0;
        }
        this.trigger_on_change();
        if (this.is_started) {
            return self.reload_current_view();
        } else {
            return $.when();
        }
    },
    get_value: function() {
        var self = this;
        if (!this.dataset)
            return [];
        var val = this.dataset.delete_all ? [commands.delete_all()] : [];
        val = val.concat(_.map(this.dataset.ids, function(id) {
            var alter_order = _.detect(self.dataset.to_create, function(x) {return x.id === id;});
            if (alter_order) {
                return commands.create(alter_order.values);
            }
            alter_order = _.detect(self.dataset.to_write, function(x) {return x.id === id;});
            if (alter_order) {
                return commands.update(alter_order.id, alter_order.values);
            }
            return commands.link_to(id);
        }));
        return val.concat(_.map(
            this.dataset.to_delete, function(x) {
                return commands['delete'](x.id);}));
    },
    commit_value: function() {
        return this.save_any_view();
    },
    save_any_view: function() {
        if (this.viewmanager && this.viewmanager.views && this.viewmanager.active_view &&
            this.viewmanager.views[this.viewmanager.active_view] &&
            this.viewmanager.views[this.viewmanager.active_view].controller) {
            var view = this.viewmanager.views[this.viewmanager.active_view].controller;
            if (this.viewmanager.active_view === "form") {
                if (!view.is_initialized.state() === 'resolved') {
                    return $.when(false);
                }
                return $.when(view.save());
            } else if (this.viewmanager.active_view === "list") {
                return $.when(view.ensure_saved());
            }
        }
        return $.when(false);
    },
    is_syntax_valid: function() {
        if (! this.viewmanager || ! this.viewmanager.views[this.viewmanager.active_view])
            return true;
        var view = this.viewmanager.views[this.viewmanager.active_view].controller;
        switch (this.viewmanager.active_view) {
        case 'form':
            return _(view.fields).chain()
                .invoke('is_valid')
                .all(_.identity)
                .value();
            break;
        case 'list':
            return view.is_valid();
        }
        return true;
    },
});

instance.web.form.One2ManyViewManager = instance.web.ViewManager.extend({
    template: 'One2Many.viewmanager',
    init: function(parent, dataset, views, flags) {
        this._super(parent, dataset, views, _.extend({}, flags, {$sidebar: false}));
        this.registry = this.registry.extend({
            list: 'instance.web.form.One2ManyListView',
            form: 'instance.web.form.One2ManyFormView',
            kanban: 'instance.web.form.One2ManyKanbanView',
        });
        this.__ignore_blur = false;
    },
    switch_mode: function(mode, unused) {
        if (mode !== 'form') {
            return this._super(mode, unused);
        }
        var self = this;
        var id = self.o2m.dataset.index !== null ? self.o2m.dataset.ids[self.o2m.dataset.index] : null;
        var pop = new instance.web.form.FormOpenPopup(this);
        pop.show_element(self.o2m.field.relation, id, self.o2m.build_context(), {
            title: _t("Open: ") + self.o2m.string,
            create_function: function(data) {
                return self.o2m.dataset.create(data).done(function(r) {
                    self.o2m.dataset.set_ids(self.o2m.dataset.ids.concat([r]));
                    self.o2m.dataset.trigger("dataset_changed", r);
                });
            },
            write_function: function(id, data, options) {
                return self.o2m.dataset.write(id, data, {}).done(function() {
                    self.o2m.reload_current_view();
                });
            },
            alternative_form_view: self.o2m.field.views ? self.o2m.field.views["form"] : undefined,
            parent_view: self.o2m.view,
            child_name: self.o2m.name,
            read_function: function() {
                return self.o2m.dataset.read_ids.apply(self.o2m.dataset, arguments);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: self.o2m.get("effective_readonly")
        });
        pop.on("elements_selected", self, function() {
            self.o2m.reload_current_view();
        });
    },
});

instance.web.form.One2ManyDataSet = instance.web.BufferedDataSet.extend({
    get_context: function() {
        this.context = this.o2m.build_context();
        return this.context;
    }
});

instance.web.form.One2ManyListView = instance.web.ListView.extend({
    _template: 'One2Many.listview',
    init: function (parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, _.extend(options || {}, {
            GroupsType: instance.web.form.One2ManyGroups,
            ListType: instance.web.form.One2ManyList
        }));
        this.on('edit:before', this, this.proxy('_before_edit'));
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));

        this.records
            .bind('add', this.proxy("changed_records"))
            .bind('edit', this.proxy("changed_records"))
            .bind('remove', this.proxy("changed_records"));
    },
    start: function () {
        var ret = this._super();
        this.$el
            .off('mousedown.handleButtons')
            .on('mousedown.handleButtons', 'table button', this.proxy('_button_down'));
        return ret;
    },
    changed_records: function () {
        this.o2m.trigger_on_change();
    },
    is_valid: function () {
        var form = this.editor.form;

        // If the form has not been modified, the view can only be valid
        // NB: is_dirty will also be set on defaults/onchanges/whatever?
        // oe_form_dirty seems to only be set on actual user actions
        if (!form.$el.is('.oe_form_dirty')) {
            return true;
        }
        this.o2m._dirty_flag = true;

        // Otherwise validate internal form
        return _(form.fields).chain()
            .invoke(function () {
                this._check_css_flags();
                return this.is_valid();
            })
            .all(_.identity)
            .value();
    },
    do_add_record: function () {
        if (this.editable()) {
            this._super.apply(this, arguments);
        } else {
            var self = this;
            var pop = new instance.web.form.SelectCreatePopup(this);
            pop.select_element(
                self.o2m.field.relation,
                {
                    title: _t("Create: ") + self.o2m.string,
                    initial_view: "form",
                    alternative_form_view: self.o2m.field.views ? self.o2m.field.views["form"] : undefined,
                    create_function: function(data, callback, error_callback) {
                        return self.o2m.dataset.create(data).done(function(r) {
                            self.o2m.dataset.set_ids(self.o2m.dataset.ids.concat([r]));
                            self.o2m.dataset.trigger("dataset_changed", r);
                        }).done(callback).fail(error_callback);
                    },
                    read_function: function() {
                        return self.o2m.dataset.read_ids.apply(self.o2m.dataset, arguments);
                    },
                    parent_view: self.o2m.view,
                    child_name: self.o2m.name,
                    form_view_options: {'not_interactible_on_create':true}
                },
                self.o2m.build_domain(),
                self.o2m.build_context()
            );
            pop.on("elements_selected", self, function() {
                self.o2m.reload_current_view();
            });
        }
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.show_element(self.o2m.field.relation, id, self.o2m.build_context(), {
            title: _t("Open: ") + self.o2m.string,
            write_function: function(id, data) {
                return self.o2m.dataset.write(id, data, {}).done(function() {
                    self.o2m.reload_current_view();
                });
            },
            alternative_form_view: self.o2m.field.views ? self.o2m.field.views["form"] : undefined,
            parent_view: self.o2m.view,
            child_name: self.o2m.name,
            read_function: function() {
                return self.o2m.dataset.read_ids.apply(self.o2m.dataset, arguments);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: !this.is_action_enabled('edit') || self.o2m.get("effective_readonly")
        });
    },
    do_button_action: function (name, id, callback) {
        if (!_.isNumber(id)) {
            instance.webclient.notification.warn(
                _t("Action Button"),
                _t("The o2m record must be saved before an action can be used"));
            return;
        }
        var parent_form = this.o2m.view;
        var self = this;
        this.ensure_saved().then(function () {
            if (parent_form)
                return parent_form.save();
            else
                return $.when();
        }).done(function () {
            self.handle_button(name, id, callback);
        });
    },

    _before_edit: function () {
        this.__ignore_blur = false;
        this.editor.form.on('blurred', this, this._on_form_blur);
    },
    _after_edit: function () {
        // The form's blur thing may be jiggered during the edition setup,
        // potentially leading to the o2m instasaving the row. Cancel any
        // blurring triggered the edition startup here
        this.editor.form.widgetFocused();
    },
    _before_unedit: function () {
        this.editor.form.off('blurred', this, this._on_form_blur);
    },
    _button_down: function () {
        // If a button is clicked (usually some sort of action button), it's
        // the button's responsibility to ensure the editable list is in the
        // correct state -> ignore form blurring
        this.__ignore_blur = true;
    },
    /**
     * Handles blurring of the nested form (saves the currently edited row),
     * unless the flag to ignore the event is set to ``true``
     *
     * Makes the internal form go away
     */
    _on_form_blur: function () {
        if (this.__ignore_blur) {
            this.__ignore_blur = false;
            return;
        }
        // FIXME: why isn't there an API for this?
        if (this.editor.form.$el.hasClass('oe_form_dirty')) {
            this.ensure_saved();
            return;
        }
        this.cancel_edition();
    },
    keyup_ENTER: function () {
        // blurring caused by hitting the [Return] key, should skip the
        // autosave-on-blur and let the handler for [Return] do its thing (save
        // the current row *anyway*, then create a new one/edit the next one)
        this.__ignore_blur = true;
        this._super.apply(this, arguments);
    },
    do_delete: function (ids) {
        var confirm = window.confirm;
        window.confirm = function () { return true; };
        try {
            return this._super(ids);
        } finally {
            window.confirm = confirm;
        }
    }
});
instance.web.form.One2ManyGroups = instance.web.ListView.Groups.extend({
    setup_resequence_rows: function () {
        if (!this.view.o2m.get('effective_readonly')) {
            this._super.apply(this, arguments);
        }
    }
});
instance.web.form.One2ManyList = instance.web.ListView.List.extend({
    pad_table_to: function (count) {
        if (!this.view.is_action_enabled('create')) {
            this._super(count);
        } else {
            this._super(count > 0 ? count - 1 : 0);
        }

        // magical invocation of wtf does that do
        if (this.view.o2m.get('effective_readonly')) {
            return;
        }

        var self = this;
        var columns = _(this.columns).filter(function (column) {
            return column.invisible !== '1';
        }).length;
        if (this.options.selectable) { columns++; }
        if (this.options.deletable) { columns++; }

        if (!this.view.is_action_enabled('create')) {
            return;
        }

        var $cell = $('<td>', {
            colspan: columns,
            'class': 'oe_form_field_one2many_list_row_add'
        }).append(
            $('<a>', {href: '#'}).text(_t("Add an item"))
                .mousedown(function () {
                    // FIXME: needs to be an official API somehow
                    if (self.view.editor.is_editing()) {
                        self.view.__ignore_blur = true;
                    }
                })
                .click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    // FIXME: there should also be an API for that one
                    if (self.view.editor.form.__blur_timeout) {
                        clearTimeout(self.view.editor.form.__blur_timeout);
                        self.view.editor.form.__blur_timeout = false;
                    }
                    self.view.ensure_saved().done(function () {
                        self.view.do_add_record();
                    });
                }));

        var $padding = this.$current.find('tr:not([data-id]):first');
        var $newrow = $('<tr>').append($cell);
        if ($padding.length) {
            $padding.before($newrow);
        } else {
            this.$current.append($newrow)
        }
    }
});

instance.web.form.One2ManyFormView = instance.web.FormView.extend({
    form_template: 'One2Many.formview',
    load_form: function(data) {
        this._super(data);
        var self = this;
        this.$buttons.find('button.oe_form_button_create').click(function() {
            self.save().done(self.on_button_new);
        });
    },
    do_notify_change: function() {
        if (this.dataset.parent_view) {
            this.dataset.parent_view.do_notify_change();
        } else {
            this._super.apply(this, arguments);
        }
    }
});

var lazy_build_o2m_kanban_view = function() {
    if (! instance.web_kanban || instance.web.form.One2ManyKanbanView)
        return;
    instance.web.form.One2ManyKanbanView = instance.web_kanban.KanbanView.extend({
    });
};

instance.web.form.FieldMany2ManyTags = instance.web.form.AbstractField.extend(instance.web.form.CompletionFieldMixin, instance.web.form.ReinitializeFieldMixin, {
    template: "FieldMany2ManyTags",
    init: function() {
        this._super.apply(this, arguments);
        instance.web.form.CompletionFieldMixin.init.call(this);
        this.set({"value": []});
        this._display_orderer = new instance.web.DropMisordered();
        this._drop_shown = false;
    },
    initialize_content: function() {
        if (this.get("effective_readonly"))
            return;
        var self = this;
        self.$text = this.$("textarea");
        self.$text.textext({
            plugins : 'tags arrow autocomplete',
            autocomplete: {
                render: function(suggestion) {
                    return $('<span class="text-label"/>').
                             data('index', suggestion['index']).html(suggestion['label']);
                }
            },
            ext: {
                autocomplete: {
                    selectFromDropdown: function() {
                        $(this).trigger('hideDropdown');
                        var index = Number(this.selectedSuggestionElement().children().children().data('index'));
                        var data = self.search_result[index];
                        if (data.id) {
                            self.add_id(data.id);
                        } else {
                            data.action();
                        }
                    },
                },
                tags: {
                    isTagAllowed: function(tag) {
                        return !!tag.name;

                    },
                    removeTag: function(tag) {
                        var id = tag.data("id");
                        self.set({"value": _.without(self.get("value"), id)});
                    },
                    renderTag: function(stuff) {
                        return $.fn.textext.TextExtTags.prototype.renderTag.
                            call(this, stuff).data("id", stuff.id);
                    },
                },
                itemManager: {
                    itemToString: function(item) {
                        return item.name;
                    },
                },
                core: {
                    onSetInputData: function(e, data) {
                        if (data == '') {
                            this._plugins.autocomplete._suggestions = null;
                        }
                        this.input().val(data);
                    },
                },
            },
        }).bind('getSuggestions', function(e, data) {
            var _this = this;
            var str = !!data ? data.query || '' : '';
            self.get_search_result(str).done(function(result) {
                self.search_result = result;
                $(_this).trigger('setSuggestions', {result : _.map(result, function(el, i) {
                    return _.extend(el, {index:i});
                })});
            });
        }).bind('hideDropdown', function() {
            self._drop_shown = false;
        }).bind('showDropdown', function() {
            self._drop_shown = true;
        });
        self.tags = self.$text.textext()[0].tags();
        self.$text
            .focusin(function () {
                self.trigger('focused');
            })
            .focusout(function() {
                self.$text.trigger("setInputData", "");
                self.trigger('blurred');
            }).keydown(function(e) {
                if (e.which === $.ui.keyCode.TAB && self._drop_shown) {
                    self.$text.textext()[0].autocomplete().selectFromDropdown();
                }
            });
    },
    set_value: function(value_) {
        value_ = value_ || [];
        if (value_.length >= 1 && value_[0] instanceof Array) {
            value_ = value_[0][2];
        }
        this._super(value_);
    },
    is_false: function() {
        return _(this.get("value")).isEmpty();
    },
    get_value: function() {
        var tmp = [commands.replace_with(this.get("value"))];
        return tmp;
    },
    get_search_blacklist: function() {
        return this.get("value");
    },
    render_value: function() {
        var self = this;
        var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
        var values = self.get("value");
        var handle_names = function(data) {
            if (self.isDestroyed())
                return;
            var indexed = {};
            _.each(data, function(el) {
                indexed[el[0]] = el;
            });
            data = _.map(values, function(el) { return indexed[el]; });
            if (! self.get("effective_readonly")) {
                self.tags.containerElement().children().remove();
                self.$('textarea').css("padding-left", "3px");
                self.tags.addTags(_.map(data, function(el) {return {name: el[1], id:el[0]};}));
            } else {
                self.$el.html(QWeb.render("FieldMany2ManyTag", {elements: data}));
            }
        };
        if (! values || values.length > 0) {
            this._display_orderer.add(dataset.name_get(values)).done(handle_names);
        } else {
            handle_names([]);
        }
    },
    add_id: function(id) {
        this.set({'value': _.uniq(this.get('value').concat([id]))});
    },
    focus: function () {
        this.$text[0].focus();
    },
});

/**
    widget options:
    - reload_on_button: Reload the whole form view if click on a button in a list view.
        If you see this options, do not use it, it's basically a dirty hack to make one
        precise o2m to behave the way we want.
*/
instance.web.form.FieldMany2Many = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    multi_selection: false,
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.is_loaded = $.Deferred();
        this.dataset = new instance.web.form.Many2ManyDataSet(this, this.field.relation);
        this.dataset.m2m = this;
        var self = this;
        this.dataset.on('unlink', self, function(ids) {
            self.dataset_changed();
        });
        this.set_value([]);
        this.list_dm = new instance.web.DropMisordered();
        this.render_value_dm = new instance.web.DropMisordered();
    },
    initialize_content: function() {
        var self = this;

        this.$el.addClass('oe_form_field oe_form_field_many2many');

        this.list_view = new instance.web.form.Many2ManyListView(this, this.dataset, false, {
                    'addable': this.get("effective_readonly") ? null : _t("Add"),
                    'deletable': this.get("effective_readonly") ? false : true,
                    'selectable': this.multi_selection,
                    'sortable': false,
                    'reorderable': false,
                    'import_enabled': false,
            });
        var embedded = (this.field.views || {}).tree;
        if (embedded) {
            this.list_view.set_embedded_view(embedded);
        }
        this.list_view.m2m_field = this;
        var loaded = $.Deferred();
        this.list_view.on("list_view_loaded", this, function() {
            loaded.resolve();
        });
        this.list_view.appendTo(this.$el);

        var old_def = self.is_loaded;
        self.is_loaded = $.Deferred().done(function() {
            old_def.resolve();
        });
        this.list_dm.add(loaded).then(function() {
            self.is_loaded.resolve();
        });
    },
    destroy_content: function() {
        this.list_view.destroy();
        this.list_view = undefined;
    },
    set_value: function(value_) {
        value_ = value_ || [];
        if (value_.length >= 1 && value_[0] instanceof Array) {
            value_ = value_[0][2];
        }
        this._super(value_);
    },
    get_value: function() {
        return [commands.replace_with(this.get('value'))];
    },
    is_false: function () {
        return _(this.get("value")).isEmpty();
    },
    render_value: function() {
        var self = this;
        this.dataset.set_ids(this.get("value"));
        this.render_value_dm.add(this.is_loaded).then(function() {
            return self.list_view.reload_content();
        });
    },
    dataset_changed: function() {
        this.internal_set_value(this.dataset.ids);
    },
});

instance.web.form.Many2ManyDataSet = instance.web.DataSetStatic.extend({
    get_context: function() {
        this.context = this.m2m.build_context();
        return this.context;
    }
});

/**
 * @class
 * @extends instance.web.ListView
 */
instance.web.form.Many2ManyListView = instance.web.ListView.extend(/** @lends instance.web.form.Many2ManyListView# */{
    do_add_record: function () {
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.select_element(
            this.model,
            {
                title: _t("Add: ") + this.m2m_field.string
            },
            new instance.web.CompoundDomain(this.m2m_field.build_domain(), ["!", ["id", "in", this.m2m_field.dataset.ids]]),
            this.m2m_field.build_context()
        );
        var self = this;
        pop.on("elements_selected", self, function(element_ids) {
            var reload = false;
            _(element_ids).each(function (id) {
                if(! _.detect(self.dataset.ids, function(x) {return x == id;})) {
                    self.dataset.set_ids(self.dataset.ids.concat([id]));
                    self.m2m_field.dataset_changed();
                    reload = true;
                }
            });
            if (reload) {
                self.reload_content();
            }
        });
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new instance.web.form.FormOpenPopup(this);
        pop.show_element(this.dataset.model, id, this.m2m_field.build_context(), {
            title: _t("Open: ") + this.m2m_field.string,
            readonly: this.getParent().get("effective_readonly")
        });
        pop.on('write_completed', self, self.reload_content);
    },
    do_button_action: function(name, id, callback) {
        var self = this;
        var _sup = _.bind(this._super, this);
        if (! this.m2m_field.options.reload_on_button) {
            return _sup(name, id, callback);
        } else {
            return this.m2m_field.view.save().then(function() {
                return _sup(name, id, function() {
                    self.m2m_field.view.reload();
                });
            });
        }
     },
});

instance.web.form.FieldMany2ManyKanban = instance.web.form.AbstractField.extend(instance.web.form.CompletionFieldMixin, {
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        instance.web.form.CompletionFieldMixin.init.call(this);
        m2m_kanban_lazy_init();
        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;

        var self = this;
        this.dataset = new instance.web.form.Many2ManyDataSet(this, this.field.relation);
        this.dataset.m2m = this;
        this.dataset.on('unlink', self, function(ids) {
            self.dataset_changed();
        });
    },
    start: function() {
        this._super.apply(this, arguments);

        var self = this;

        self.load_view();
        self.on("change:effective_readonly", self, function() {
            self.is_loaded = self.is_loaded.then(function() {
                self.kanban_view.destroy();
                return $.when(self.load_view()).done(function() {
                    self.render_value();
                });
            });
        });
    },
    set_value: function(value_) {
        value_ = value_ || [];
        if (value_.length >= 1 && value_[0] instanceof Array) {
            value_ = value_[0][2];
        }
        this._super(value_);
    },
    get_value: function() {
        return [commands.replace_with(this.get('value'))];
    },
    load_view: function() {
        var self = this;
        this.kanban_view = new instance.web.form.Many2ManyKanbanView(this, this.dataset, false, {
                    'create_text': _t("Add"),
                    'creatable': self.get("effective_readonly") ? false : true,
                    'quick_creatable': self.get("effective_readonly") ? false : true,
                    'read_only_mode': self.get("effective_readonly") ? true : false,
                    'confirm_on_delete': false,
            });
        var embedded = (this.field.views || {}).kanban;
        if (embedded) {
            this.kanban_view.set_embedded_view(embedded);
        }
        this.kanban_view.m2m = this;
        var loaded = $.Deferred();
        this.kanban_view.on("kanban_view_loaded",self,function() {
            self.initial_is_loaded.resolve();
            loaded.resolve();
        });
        this.kanban_view.on('switch_mode', this, this.open_popup);
        $.async_when().done(function () {
            self.kanban_view.appendTo(self.$el);
        });
        return loaded;
    },
    render_value: function() {
        var self = this;
        this.dataset.set_ids(this.get("value"));
        this.is_loaded = this.is_loaded.then(function() {
            return self.kanban_view.do_search(self.build_domain(), self.dataset.get_context(), []);
        });
    },
    dataset_changed: function() {
        this.set({'value': this.dataset.ids});
    },
    open_popup: function(type, unused) {
        if (type !== "form")
            return;
        var self = this;
        if (this.dataset.index === null) {
            var pop = new instance.web.form.SelectCreatePopup(this);
            pop.select_element(
                this.field.relation,
                {
                    title: _t("Add: ") + this.string
                },
                new instance.web.CompoundDomain(this.build_domain(), ["!", ["id", "in", this.dataset.ids]]),
                this.build_context()
            );
            pop.on("elements_selected", self, function(element_ids) {
                _.each(element_ids, function(one_id) {
                    if(! _.detect(self.dataset.ids, function(x) {return x == one_id;})) {
                        self.dataset.set_ids([].concat(self.dataset.ids, [one_id]));
                        self.dataset_changed();
                        self.render_value();
                    }
                });
            });
        } else {
            var id = self.dataset.ids[self.dataset.index];
            var pop = new instance.web.form.FormOpenPopup(this);
            pop.show_element(self.field.relation, id, self.build_context(), {
                title: _t("Open: ") + self.string,
                write_function: function(id, data, options) {
                    return self.dataset.write(id, data, {}).done(function() {
                        self.render_value();
                    });
                },
                alternative_form_view: self.field.views ? self.field.views["form"] : undefined,
                parent_view: self.view,
                child_name: self.name,
                readonly: self.get("effective_readonly")
            });
        }
    },
    add_id: function(id) {
        this.quick_create.add_id(id);
    },
});

function m2m_kanban_lazy_init() {
if (instance.web.form.Many2ManyKanbanView)
    return;
instance.web.form.Many2ManyKanbanView = instance.web_kanban.KanbanView.extend({
    quick_create_class: 'instance.web.form.Many2ManyQuickCreate',
    _is_quick_create_enabled: function() {
        return this._super() && ! this.group_by;
    },
});
instance.web.form.Many2ManyQuickCreate = instance.web.Widget.extend({
    template: 'Many2ManyKanban.quick_create',

    /**
     * close_btn: If true, the widget will display a "Close" button able to trigger
     * a "close" event.
     */
    init: function(parent, dataset, context, buttons) {
        this._super(parent);
        this.m2m = this.getParent().view.m2m;
        this.m2m.quick_create = this;
        this._dataset = dataset;
        this._buttons = buttons || false;
        this._context = context || {};
    },
    start: function () {
        var self = this;
        self.$text = this.$el.find('input').css("width", "200px");
        self.$text.textext({
            plugins : 'arrow autocomplete',
            autocomplete: {
                render: function(suggestion) {
                    return $('<span class="text-label"/>').
                             data('index', suggestion['index']).html(suggestion['label']);
                }
            },
            ext: {
                autocomplete: {
                    selectFromDropdown: function() {
                        $(this).trigger('hideDropdown');
                        var index = Number(this.selectedSuggestionElement().children().children().data('index'));
                        var data = self.search_result[index];
                        if (data.id) {
                            self.add_id(data.id);
                        } else {
                            data.action();
                        }
                    },
                },
                itemManager: {
                    itemToString: function(item) {
                        return item.name;
                    },
                },
            },
        }).bind('getSuggestions', function(e, data) {
            var _this = this;
            var str = !!data ? data.query || '' : '';
            self.m2m.get_search_result(str).done(function(result) {
                self.search_result = result;
                $(_this).trigger('setSuggestions', {result : _.map(result, function(el, i) {
                    return _.extend(el, {index:i});
                })});
            });
        });
        self.$text.focusout(function() {
            self.$text.val("");
        });
    },
    focus: function() {
        this.$text[0].focus();
    },
    add_id: function(id) {
        var self = this;
        self.$text.val("");
        self.trigger('added', id);
        this.m2m.dataset_changed();
    },
});
}

/**
 * Class with everything which is common between FormOpenPopup and SelectCreatePopup.
 */
instance.web.form.AbstractFormPopup = instance.web.Widget.extend({
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
        _.defaults(this.options, {
        });
    },
    init_dataset: function() {
        var self = this;
        this.created_elements = [];
        this.dataset = new instance.web.ProxyDataSet(this, this.model, this.context);
        this.dataset.read_function = this.options.read_function;
        this.dataset.create_function = function(data, sup) {
            var fct = self.options.create_function || sup;
            return fct.call(this, data).done(function(r) {
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
        var dialog = new instance.web.Dialog(this, {
            min_width: '800px',
            dialogClass: 'oe_act_window',
            close: function() {
                self.check_exit(true);
            },
            title: this.options.title || "",
        }, this.$el).open();
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
        this.view_form = new instance.web.FormView(this, this.dataset, this.options.view_id || false, options);
        if (this.options.alternative_form_view) {
            this.view_form.set_embedded_view(this.options.alternative_form_view);
        }
        this.view_form.appendTo(this.$el.find(".oe_popup_form"));
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
        if (this.$el.is(":data(dialog)")) {
            this.$el.dialog('close');
        }
        this._super();
    },
});

/**
 * Class to display a popup containing a form view.
 */
instance.web.form.FormOpenPopup = instance.web.form.AbstractFormPopup.extend({
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

/**
 * Class to display a popup to display a list to search a row. It also allows
 * to switch to a form view to create a new row.
 */
instance.web.form.SelectCreatePopup = instance.web.form.AbstractFormPopup.extend({
    /**
     * options:
     * - initial_ids
     * - initial_view: form or search (default search)
     * - disable_multiple_selection
     * - list_view_options
     */
    select_element: function(model, options, domain, context) {
        this.init_popup(model, null, domain, context, options);
        var self = this;
        _.defaults(this.options, {
            initial_view: "search",
        });
        this.initial_ids = this.options.initial_ids;
        this.display_popup();
    },
    start: function() {
        var self = this;
        this.init_dataset();
        if (this.options.initial_view == "search") {
            instance.web.pyeval.eval_domains_and_contexts({
                domains: [],
                contexts: [this.context]
            }).done(function (results) {
                var search_defaults = {};
                _.each(results.context, function (value_, key) {
                    var match = /^search_default_(.*)$/.exec(key);
                    if (match) {
                        search_defaults[match[1]] = value_;
                    }
                });
                self.setup_search_view(search_defaults);
            });
        } else { // "form"
            this.new_object();
        }
    },
    setup_search_view: function(search_defaults) {
        var self = this;
        if (this.searchview) {
            this.searchview.destroy();
        }
        this.searchview = new instance.web.SearchView(this,
                this.dataset, false,  search_defaults);
        this.searchview.on('search_data', self, function(domains, contexts, groupbys) {
            if (self.initial_ids) {
                self.do_search(domains.concat([[["id", "in", self.initial_ids]], self.domain]),
                    contexts, groupbys);
                self.initial_ids = undefined;
            } else {
                self.do_search(domains.concat([self.domain]), contexts.concat(self.context), groupbys);
            }
        });
        this.searchview.on("search_view_loaded", self, function() {
            self.view_list = new instance.web.form.SelectCreateListView(self,
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
            self.view_list.appendTo($(".oe_popup_list", self.$el)).then(function() {
                self.view_list.do_show();
            }).then(function() {
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
                var $cbutton = self.$buttonpane.find(".oe_selectcreatepopup-search-create");
                $cbutton.click(function() {
                    self.new_object();
                });
            });
        });
        this.searchview.appendTo($(".oe_popup_search", self.$el));
    },
    do_search: function(domains, contexts, groupbys) {
        var self = this;
        instance.web.pyeval.eval_domains_and_contexts({
            domains: domains || [],
            contexts: contexts || [],
            group_by_seq: groupbys || []
        }).done(function (results) {
            self.view_list.do_search(results.domain, results.context, results.group_by);
        });
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
            this.searchview.hide();
        }
        if (this.view_list) {
            this.view_list.$el.hide();
        }
        this.setup_form_view();
    },
});

instance.web.form.SelectCreateListView = instance.web.ListView.extend({
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

instance.web.form.FieldReference = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldReference',
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
        var fm = new instance.web.form.DefaultFieldManager(this);
        this.fm = fm;
        fm.extend_field_desc({
            "selection": {
                selection: this.field_manager.get_field_desc(this.name).selection,
                type: "selection",
            },
            "m2o": {
                relation: null,
                type: "many2one",
            },
        });
        this.selection = new instance.web.form.FieldSelection(fm, { attrs: {
            name: 'selection',
            modifiers: JSON.stringify({readonly: this.get('effective_readonly')}),
        }});
        this.selection.on("change:value", this, this.on_selection_changed);
        this.selection.appendTo(this.$(".oe_form_view_reference_selection"));
        this.selection
            .on('focused', null, function () {self.trigger('focused')})
            .on('blurred', null, function () {self.trigger('blurred')});

        this.m2o = new instance.web.form.FieldMany2One(fm, { attrs: {
            name: 'm2o',
            modifiers: JSON.stringify({readonly: this.get('effective_readonly')}),
        }});
        this.m2o.on("change:value", this, this.data_changed);
        this.m2o.appendTo(this.$(".oe_form_view_reference_m2o"));
        this.m2o
            .on('focused', null, function () {self.trigger('focused')})
            .on('blurred', null, function () {self.trigger('blurred')});
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
        this.m2o.$el.toggle(!!this.get('value')[0]);
        this.reference_ready = true;
    },
});

instance.web.form.FieldBinary = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.binary_value = false;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = 25 * 1024 * 1024; // 25Mo
        if (!this.useFileAPI) {
            this.fileupload_id = _.uniqueId('oe_fileupload');
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
        this.$el.find('input.oe_form_binary_file').change(this.on_file_change);
        this.$el.find('button.oe_form_binary_file_save').click(this.on_save_as);
        this.$el.find('.oe_form_binary_file_clear').click(this.on_clear);
    },
    on_file_change: function(e) {
        var self = this;
        var file_node = e.target;
        if ((this.useFileAPI && file_node.files.length) || (!this.useFileAPI && $(file_node).val() !== '')) {
            if (this.useFileAPI) {
                var file = file_node.files[0];
                if (file.size > this.max_upload_size) {
                    var msg = _t("The selected file exceed the maximum file size of %s.");
                    instance.webclient.notification.warn(_t("File upload"), _.str.sprintf(msg, instance.web.human_size(this.max_upload_size)));
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
                this.$el.find('form.oe_form_binary_form input[name=session_id]').val(this.session.session_id);
                this.$el.find('form.oe_form_binary_form').submit();
            }
            this.$el.find('.oe_form_binary_progress').show();
            this.$el.find('.oe_form_binary').hide();
        }
    },
    on_file_uploaded: function(size, name, content_type, file_base64) {
        if (size === false) {
            this.do_warn(_t("File Upload"), _t("There was a problem while uploading your file"));
            // TODO: use openerp web crashmanager
            console.warn("Error while uploading file : ", name);
        } else {
            this.filename = name;
            this.on_file_uploaded_and_valid.apply(this, arguments);
        }
        this.$el.find('.oe_form_binary_progress').hide();
        this.$el.find('.oe_form_binary').show();
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
    },
    on_save_as: function(ev) {
        var value = this.get('value');
        if (!value) {
            this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
            ev.stopPropagation();
        } else {
            instance.web.blockUI();
            var c = instance.webclient.crashmanager;
            this.session.get_file({
                url: '/web/binary/saveas_ajax',
                data: {data: JSON.stringify({
                    model: this.view.dataset.model,
                    id: (this.view.datarecord.id || ''),
                    field: this.name,
                    filename_field: (this.node.attrs.filename || ''),
                    data: instance.web.form.is_bin_size(value) ? null : value,
                    context: this.view.dataset.get_context()
                })},
                complete: instance.web.unblockUI,
                error: c.rpc_error.bind(c)
            });
            ev.stopPropagation();
            return false;
        }
    },
    set_filename: function(value) {
        var filename = this.node.attrs.filename;
        if (filename) {
            var tmp = {};
            tmp[filename] = value;
            this.field_manager.set_values(tmp);
        }
    },
    on_clear: function() {
        if (this.get('value') !== false) {
            this.binary_value = false;
            this.internal_set_value(false);
        }
        return false;
    }
});

instance.web.form.FieldBinaryFile = instance.web.form.FieldBinary.extend({
    template: 'FieldBinaryFile',
    initialize_content: function() {
        this._super();
        if (this.get("effective_readonly")) {
            var self = this;
            this.$el.find('a').click(function(ev) {
                if (self.get('value')) {
                    self.on_save_as(ev);
                }
                return false;
            });
        }
    },
    render_value: function() {
        if (!this.get("effective_readonly")) {
            var show_value;
            if (this.node.attrs.filename) {
                show_value = this.view.datarecord[this.node.attrs.filename] || '';
            } else {
                show_value = (this.get('value') != null && this.get('value') !== false) ? this.get('value') : '';
            }
            this.$el.find('input').eq(0).val(show_value);
        } else {
            this.$el.find('a').toggle(!!this.get('value'));
            if (this.get('value')) {
                var show_value = _t("Download")
                if (this.view)
                    show_value += " " + (this.view.datarecord[this.node.attrs.filename] || '');
                this.$el.find('a').text(show_value);
            }
        }
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
        this.binary_value = true;
        this.internal_set_value(file_base64);
        var show_value = name + " (" + instance.web.human_size(size) + ")";
        this.$el.find('input').eq(0).val(show_value);
        this.set_filename(name);
    },
    on_clear: function() {
        this._super.apply(this, arguments);
        this.$el.find('input').eq(0).val('');
        this.set_filename('');
    }
});

instance.web.form.FieldBinaryImage = instance.web.form.FieldBinary.extend({
    template: 'FieldBinaryImage',
    placeholder: "/web/static/src/img/placeholder.png",
    render_value: function() {
        var self = this;
        var url;
        if (this.get('value') && !instance.web.form.is_bin_size(this.get('value'))) {
            url = 'data:image/png;base64,' + this.get('value');
        } else if (this.get('value')) {
            var id = JSON.stringify(this.view.datarecord.id || null);
            var field = this.name;
            if (this.options.preview_image)
                field = this.options.preview_image;
            url = this.session.url('/web/binary/image', {
                                        model: this.view.dataset.model,
                                        id: id,
                                        field: field,
                                        t: (new Date().getTime()),
            });
        } else {
            url = this.placeholder;
        }
        var $img = $(QWeb.render("FieldBinaryImage-img", { widget: this, url: url }));
        this.$el.find('> img').remove();
        this.$el.prepend($img);
        $img.load(function() {
            if (! self.options.size)
                return;
            $img.css("max-width", "" + self.options.size[0] + "px");
            $img.css("max-height", "" + self.options.size[1] + "px");
            $img.css("margin-left", "" + (self.options.size[0] - $img.width()) / 2 + "px");
            $img.css("margin-top", "" + (self.options.size[1] - $img.height()) / 2 + "px");
        });
        $img.on('error', function() {
            $img.attr('src', self.placeholder);
            instance.webclient.notification.warn(_t("Image"), _t("Could not display the selected image."));
        });
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
        this.internal_set_value(file_base64);
        this.binary_value = true;
        this.render_value();
        this.set_filename(name);
    },
    on_clear: function() {
        this._super.apply(this, arguments);
        this.render_value();
        this.set_filename('');
    }
});

/**
 * Widget for (one2many field) to upload one or more file in same time and display in list.
 * The user can delete his files.
 * Options on attribute ; "blockui" {Boolean} block the UI or not
 * during the file is uploading
 */
instance.web.form.FieldMany2ManyBinaryMultiFiles = instance.web.form.AbstractField.extend({
    template: "FieldBinaryFileUploader",
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.field_manager = field_manager;
        this.node = node;
        if(this.field.type != "many2many" || this.field.relation != 'ir.attachment') {
            throw _.str.sprintf(_t("The type of the field '%s' must be a many2many field with a relation to 'ir.attachment' model."), this.field.string);
        }
        this.ds_file = new instance.web.DataSetSearch(this, 'ir.attachment');
        this.fileupload_id = _.uniqueId('oe_fileupload_temp');
        $(window).on(this.fileupload_id, _.bind(this.on_file_loaded, this));
    },
    start: function() {
        this._super(this);
        this.$el.on('change', 'input.oe_form_binary_file', this.on_file_change );
    },
    set_value: function(value_) {
        var value_ = value_ || [];
        var self = this;
        var ids = [];
        _.each(value_, function(command) {
            if (isNaN(command) && command.id == undefined) {
                switch (command[0]) {
                    case commands.CREATE:
                        ids = ids.concat(command[2]);
                        return;
                    case commands.REPLACE_WITH:
                        ids = ids.concat(command[2]);
                        return;
                    case commands.UPDATE:
                        ids = ids.concat(command[2]);
                        return;
                    case commands.LINK_TO:
                        ids = ids.concat(command[1]);
                        return;
                    case commands.DELETE:
                        ids = _.filter(ids, function (id) { return id != command[1];});
                        return;
                    case commands.DELETE_ALL:
                        ids = [];
                        return;
                }
            } else {
                ids.push(command);
            }
        });
        this._super( ids );
    },
    get_value: function() {
        return _.map(this.get('value'), function (value) { return commands.link_to( isNaN(value) ? value.id : value ); });
    },
    get_file_url: function (attachment) {
        return this.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname', id: attachment['id']});
    },
    read_name_values : function () {
        var self = this;
        // select the list of id for a get_name
        var values = [];
        _.each(this.get('value'), function (val) {
            if (typeof val != 'object') {
                values.push(val);
            }
        });
        // send request for get_name
        if (values.length) {
            return this.ds_file.call('read', [values, ['id', 'name', 'datas_fname']]).done(function (datas) {
                _.each(datas, function (data) {
                    data.no_unlink = true;
                    data.url = self.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname', id: data.id});

                    _.each(self.get('value'), function (val, key) {
                        if(val == data.id) {
                            self.get('value')[key] = data;
                        }
                    });
                });
            });
        } else {
            return $.when(this.get('value'));
        }
    },
    render_value: function () {
        var self = this;
        this.read_name_values().then(function (datas) {

            var render = $(instance.web.qweb.render('FieldBinaryFileUploader.files', {'widget': self}));
            render.on('click', '.oe_delete', _.bind(self.on_file_delete, self));
            self.$('.oe_placeholder_files, .oe_attachments').replaceWith( render );

            // reinit input type file
            var $input = self.$('input.oe_form_binary_file');
            $input.after($input.clone(true)).remove();
            self.$(".oe_fileupload").show();

        });
    },
    on_file_change: function (event) {
        event.stopPropagation();
        var self = this;
        var $target = $(event.target);
        if ($target.val() !== '') {

            var filename = $target.val().replace(/.*[\\\/]/,'');

            // if the files is currently uploded, don't send again
            if( !isNaN(_.find(this.get('value'), function (file) { return (file.filename || file.name) == filename && file.upload; } )) ) {
                return false;
            }

            // block UI or not
            if(this.node.attrs.blockui>0) {
                instance.web.blockUI();
            }

            // if the files exits for this answer, delete the file before upload
            var files = _.filter(this.get('value'), function (file) {
                if((file.filename || file.name) == filename) {
                    self.ds_file.unlink([file.id]);
                    return false;
                } else {
                    return true;
                }
            });

            // TODO : unactivate send on wizard and form

            // submit file
            this.$('form.oe_form_binary_form').submit();
            this.$(".oe_fileupload").hide();

            // add file on result
            files.push({
                'id': 0,
                'name': filename,
                'filename': filename,
                'url': '',
                'upload': true
            });

            this.set({'value': files});
        }
    },
    on_file_loaded: function (event, result) {
        var files = this.get('value');

        // unblock UI
        if(this.node.attrs.blockui>0) {
            instance.web.unblockUI();
        }

        // TODO : activate send on wizard and form

        if (result.error || !result.id ) {
            this.do_warn( _t('Uploading error'), result.error);
            files = _.filter(files, function (val) { return !val.upload; });
        } else {
            for(var i in files){
                if(files[i].filename == result.filename && files[i].upload) {
                    files[i] = {
                        'id': result.id,
                        'name': result.name,
                        'filename': result.filename,
                        'url': this.get_file_url(result)
                    };
                }
            }
        }

        this.set({'value': files});
        this.render_value()
    },
    on_file_delete: function (event) {
        event.stopPropagation();
        var file_id=$(event.target).data("id");
        if (file_id) {
            var files=[];
            for(var i in this.get('value')){
                if(file_id != this.get('value')[i].id){
                    files.push(this.get('value')[i]);
                }
                else if(!this.get('value')[i].no_unlink) {
                    this.ds_file.unlink([file_id]);
                }
            }
            this.set({'value': files});
        }
    },
});

instance.web.form.FieldStatus = instance.web.form.AbstractField.extend({
    template: "FieldStatus",
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.options.clickable = this.options.clickable || (this.node.attrs || {}).clickable || false;
        this.options.visible = this.options.visible || (this.node.attrs || {}).statusbar_visible || false;
        this.set({value: false});
        this.selection = [];
        this.set("selection", []);
        this.selection_dm = new instance.web.DropMisordered();
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
            this.$el.on('click','li',this.on_click_stage);
        }
        if (this.$el.parent().is('header')) {
            this.$el.after('<div class="oe_clear"/>');
        }
        this._super();
    },
    set_value: function(value_) {
        if (value_ instanceof Array) {
            value_ = value_[0];
        }
        this._super(value_);
    },
    render_value: function() {
        var self = this;
        var content = QWeb.render("FieldStatus.content", {widget: self});
        self.$el.html(content);
        var colors = JSON.parse((self.node.attrs || {}).statusbar_colors || "{}");
        var color = colors[self.get('value')];
        if (color) {
            self.$("oe_active").css("color", color);
        }
    },
    calc_domain: function() {
        var d = instance.web.pyeval.eval('domain', this.build_domain());
        domain = ['|', ['id', '=', this.get('value')]].concat(d);
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
        var selection = [];

        var calculation = _.bind(function() {
            if (this.field.type == "many2one") {
                var domain = [];
                var ds = new instance.web.DataSetSearch(this, this.field.relation,
                    self.build_context(), this.get("evaluated_selection_domain"));
                return ds.read_slice(['name'], {}).then(function (records) {
                    for(var i = 0; i < records.length; i++) {
                        selection.push([records[i].id, records[i].name]);
                    }
                });
            } else {
                // For field type selection filter values according to
                // statusbar_visible attribute of the field. For example:
                // statusbar_visible="draft,open".
                var select = this.field.selection;
                for(var i=0; i < select.length; i++) {
                    var key = select[i][0];
                    if(key == this.get('value') || !this.options.visible || this.options.visible.indexOf(key) != -1) {
                        selection.push(select[i]);
                    }
                }
                return $.when();
            }
        }, this);
        this.selection_dm.add(calculation()).then(function () {
            if (! _.isEqual(selection, self.get("selection"))) {
                self.set("selection", selection);
            }
        });
    },
    on_click_stage: function (ev) {
        var self = this;
        var $li = $(ev.currentTarget);
        var val = parseInt($li.data("id"));
        if (val != self.get('value')) {
            this.view.recursive_save().done(function() {
                var change = {};
                change[self.name] = val;
                self.view.dataset.write(self.view.datarecord.id, change).done(function() {
                    self.view.reload();
                });
            });
        }
    },
});

instance.web.form.FieldMonetary = instance.web.form.FieldFloat.extend({
    template: "FieldMonetary",
    widget_class: 'oe_form_field_float oe_form_field_monetary',
    init: function() {
        this._super.apply(this, arguments);
        this.set({"currency": false});
        if (this.options.currency_field) {
            this.field_manager.on("field_changed:" + this.options.currency_field, this, function() {
                this.set({"currency": this.field_manager.get_field_value(this.options.currency_field)});
            });
        }
        this.on("change:currency", this, this.get_currency_info);
        this.get_currency_info();
        this.ci_dm = new instance.web.DropMisordered();
    },
    start: function() {
        var tmp = this._super();
        this.on("change:currency_info", this, this.reinitialize);
        return tmp;
    },
    get_currency_info: function() {
        var self = this;
        if (this.get("currency") === false) {
            this.set({"currency_info": null});
            return;
        }
        return this.ci_dm.add(self.alive(new instance.web.Model("res.currency").query(["symbol", "position"])
            .filter([["id", "=", self.get("currency")]]).first())).then(function(res) {
            self.set({"currency_info": res});
        });
    },
    parse_value: function(val, def) {
        return instance.web.parse_value(val, {type: "float", digits: (this.node.attrs || {}).digits || this.field.digits}, def);
    },
    format_value: function(val, def) {
        return instance.web.format_value(val, {type: "float", digits: (this.node.attrs || {}).digits || this.field.digits}, def);
    },
});

/**
 * Registry of form fields, called by :js:`instance.web.FormView`.
 *
 * All referenced classes must implement FieldInterface. Those represent the classes whose instances
 * will substitute to the <field> tags as defined in OpenERP's views.
 */
instance.web.form.widgets = new instance.web.Registry({
    'char' : 'instance.web.form.FieldChar',
    'id' : 'instance.web.form.FieldID',
    'email' : 'instance.web.form.FieldEmail',
    'url' : 'instance.web.form.FieldUrl',
    'text' : 'instance.web.form.FieldText',
    'html' : 'instance.web.form.FieldTextHtml',
    'date' : 'instance.web.form.FieldDate',
    'datetime' : 'instance.web.form.FieldDatetime',
    'selection' : 'instance.web.form.FieldSelection',
    'many2one' : 'instance.web.form.FieldMany2One',
    'many2onebutton' : 'instance.web.form.Many2OneButton',
    'many2many' : 'instance.web.form.FieldMany2Many',
    'many2many_tags' : 'instance.web.form.FieldMany2ManyTags',
    'many2many_kanban' : 'instance.web.form.FieldMany2ManyKanban',
    'one2many' : 'instance.web.form.FieldOne2Many',
    'one2many_list' : 'instance.web.form.FieldOne2Many',
    'reference' : 'instance.web.form.FieldReference',
    'boolean' : 'instance.web.form.FieldBoolean',
    'float' : 'instance.web.form.FieldFloat',
    'integer': 'instance.web.form.FieldFloat',
    'float_time': 'instance.web.form.FieldFloat',
    'progressbar': 'instance.web.form.FieldProgressBar',
    'image': 'instance.web.form.FieldBinaryImage',
    'binary': 'instance.web.form.FieldBinaryFile',
    'many2many_binary': 'instance.web.form.FieldMany2ManyBinaryMultiFiles',
    'statusbar': 'instance.web.form.FieldStatus',
    'monetary': 'instance.web.form.FieldMonetary',
});

/**
 * Registry of widgets usable in the form view that can substitute to any possible
 * tags defined in OpenERP's form views.
 *
 * Every referenced class should extend FormWidget.
 */
instance.web.form.tags = new instance.web.Registry({
    'button' : 'instance.web.form.WidgetButton',
});

instance.web.form.custom_widgets = new instance.web.Registry({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
