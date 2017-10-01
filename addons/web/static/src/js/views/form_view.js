odoo.define('web.FormView', function (require) {
"use strict";

var common = require('web.form_common');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var Dialog = require('web.Dialog');
var FormRenderingEngine = require('web.FormRenderingEngine');
var Model = require('web.DataModel');
var Pager = require('web.Pager');
var Sidebar = require('web.Sidebar');
var utils = require('web.utils');
var View = require('web.View');

var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

/**
 * Properties:
 *      - actual_mode: always "view", "edit" or "create". Read-only property. Determines
 *      the mode used by the view.
 */
var FormView = View.extend(common.FieldManagerMixin, {
    className: "o_form_view",
    defaults: _.extend({}, View.prototype.defaults, {
        not_interactible_on_create: false,
        initial_mode: "view",
        disable_autofocus: false,
        footer_to_buttons: false,
    }),
    display_name: _lt('Form'),
    icon: 'fa-edit',
    multi_record: false,
    // Indicates that this view is not searchable, and thus that no search view should be displayed.
    searchable: false,

    /**
     * Called each time the form view is attached into the DOM
     */
    on_attach_callback: function() {
        this.trigger('attached');
        this.autofocus();
    },
    /**
     * Called each time the form view is detached from the DOM
     */
    on_detach_callback: function() {
        this.trigger('detached');
    },
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.fields = {};
        this.fields_order = [];
        this.datarecord = {};
        this.onchanges_mutex = new utils.Mutex();
        this.default_focus_field = null;
        this.default_focus_button = null;
        this.fields_registry = core.form_widget_registry;
        this.tags_registry = core.form_tag_registry;
        this.widgets_registry = core.form_custom_registry;
        this.has_been_loaded = $.Deferred();
        this.translatable_fields = [];
        this.is_initialized = $.Deferred();
        this.record_loaded = $.Deferred();
        this.mutating_mutex = new utils.Mutex();
        this.save_list = [];
        this.render_value_defs = [];
        this.reload_mutex = new utils.Mutex();
        this.__clicked_inside = false;
        this.__blur_timeout = null;
        this.rendering_engine = new FormRenderingEngine(this);
        this.set({actual_mode: this.options.initial_mode});
        this.has_been_loaded.done(function() {
            self.on("change:actual_mode", self, self.toggle_buttons);
            self.on("change:actual_mode", self, self.toggle_sidebar);
        });
        self.on("load_record", self, self.load_record);
        core.bus.on('clear_uncommitted_changes', this, function(chain_callbacks) {
            var self = this;
            chain_callbacks(function() {
                return self.can_be_discarded();
            });
        });
    },
    start: function() {
        if (this.$pager) {
            this.$pager.off();
        }
        var self = this;

        this.rendering_engine.set_fields_registry(this.fields_registry);
        this.rendering_engine.set_tags_registry(this.tags_registry);
        this.rendering_engine.set_widgets_registry(this.widgets_registry);
        this.rendering_engine.set_fields_view(this.fields_view);
        this.rendering_engine.render_to(this.$el);

        this.$el.on('mousedown.formBlur', function () {
            self.__clicked_inside = true;
        });

        this.has_been_loaded.resolve();

        // Add bounce effect on button 'Edit' when click on readonly page view.
        this.$(".oe_title,.o_group").on('click', function (e) {
            if(self.get("actual_mode") === "view" && self.$buttons && !$(e.target).is('[data-toggle]')) {
                self.$buttons.find(".o_form_button_edit").openerpBounce();
                core.bus.trigger('click', e);
            }
        });
        return this._super();
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
    /**
     * Render the buttons according to the FormView.buttons template and add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the FormView inserts them into this.options.$buttons
     * if it exists
     */
    render_buttons: function($node) {
        this.$buttons = $('<div/>');

        var $footer = this.$('footer');
        if (this.options.action_buttons !== false || this.options.footer_to_buttons && $footer.children().length === 0) {
            this.$buttons.append(QWeb.render("FormView.buttons", {'widget': this}));
        }
        if (this.options.footer_to_buttons) {
            $footer.appendTo(this.$buttons);
        }

        // Show or hide the buttons according to the view mode
        this.toggle_buttons();
        this.$buttons.on('click', '.o_form_button_create', this.on_button_create);
        this.$buttons.on('click', '.o_form_button_edit', this.on_button_edit);
        this.$buttons.on('click', '.o_form_button_save', this.on_button_save);
        this.$buttons.on('click', '.o_form_button_cancel', this.on_button_cancel);

        this.$buttons.appendTo($node);
    },
    /**
     * Instantiate and render the sidebar if a sidebar is requested
     * Sets this.sidebar
     * @param {jQuery} [$node] a jQuery node where the sidebar should be inserted
     **/
    render_sidebar: function($node) {
        if (!this.sidebar && this.options.sidebar) {
            this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
            if (this.fields_view.toolbar) {
                this.sidebar.add_toolbar(this.fields_view.toolbar);
            }
            var canDuplicate = this.is_action_enabled('create') && this.is_action_enabled('duplicate');
            this.sidebar.add_items('other', _.compact([
                this.is_action_enabled('delete') && { label: _t('Delete'), callback: this.on_button_delete },
                canDuplicate && { label: _t('Duplicate'), callback: this.on_button_duplicate }
            ]));

            this.sidebar.appendTo($node);

            // Show or hide the sidebar according to the view mode
            this.toggle_sidebar();
        }
    },
    /**
     * Instantiate and render the pager and add listeners on it.
     * Set this.pager
     * @param {jQuery} [$node] a jQuery node where the pager should be inserted
     * $node may be undefined, in which case the FormView inserts the pager into this.options.$pager
     */
    render_pager: function($node) {
        if (this.options.pager) {
            var self = this;
            var options = {
                validate: _.bind(this.can_be_discarded, this),
            };

            this.pager = new Pager(this, this.dataset.ids.length, this.dataset.index + 1, 1, options);
            this.pager.on('pager_changed', this, function (new_state) {
                this.pager.disable();
                this.dataset.index = new_state.current_min - 1;
                this.trigger('pager_action_executed');
                $.when(this.reload()).then(function () {
                    self.pager.enable();
                });
            });

            this.pager.appendTo($node = $node || this.options.$pager);

            // Hide the pager in create mode
            if (this.get("actual_mode") === "create") {
                this.pager.do_hide();
            }
        }
    },
    /**
     * Show or hide the buttons according to the actual_mode
     */
    toggle_buttons: function() {
        var view_mode = this.get("actual_mode") === "view";
        if (this.$buttons) {
            this.$buttons.find('.o_form_buttons_view').toggle(view_mode);
            this.$buttons.find('.o_form_buttons_edit').toggle(!view_mode);
        }
    },
    /**
     * Show or hide the sidebar according to the actual_mode
     */
    toggle_sidebar: function() {
        if (this.sidebar) {
            this.sidebar.do_toggle(this.get("actual_mode") === "view");
        }
    },
    update_pager: function() {
        if (this.pager) {
            // Hide the pager in create mode
            if (this.get("actual_mode") === "create") {
                this.pager.do_hide();
            } else {
                this.pager.update_state({size: this.dataset.ids.length, current_min: this.dataset.index + 1});
            }
        }
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
            this.do_show();
        }
    },
    /**
     * @param {Boolean} [options.mode=undefined] If specified, switch the form to specified mode. Can be "edit" or "view".
     * @param {Boolean} [options.reload=true] whether the form should reload its content on show, or use the currently loaded record
     * @return {$.Deferred}
     */
    do_show: function (options) {
        var self = this;
        options = options || {};
        this.$el.removeClass('oe_form_dirty');

        var shown = this.has_been_loaded;
        if (options.reload !== false) {
            shown = shown.then(function() {
                if (self.dataset.index === null) {
                    // null index means we should start a new record
                    return self.on_button_new();
                }
                var fields = _.keys(self.fields_view.fields);
                fields.push('display_name');
                fields.push('__last_update');
                return self.dataset.read_index(fields, {
                    context: { 'bin_size': true }
                }).then(function(r) {
                    self.trigger('load_record', r);
                });
            });
        }
        return $.when(shown, this._super()).then(function() {
            self._actualize_mode(options.mode || self.options.initial_mode);
            core.bus.trigger('form_view_shown', self);
        });
    },
    load_record: function(record) {
        var self = this, set_values = [];
        if (!record) {
            this.set({ 'title' : undefined });
            this.do_warn(_t("Form"), _t("The record could not be found in the database."), true);
            return $.Deferred().reject();
        }
        this.datarecord = record;

        this.record_loaded = $.Deferred();
        _(this.fields).each(function (field, f) {
            field._dirty_flag = false;
            field._inhibit_on_change_flag = true;
            var result = field.set_value_from_record(self.datarecord);
            field._inhibit_on_change_flag = false;
            set_values.push(result);
        });
        this._actualize_mode(); // call after updating the fields as it may trigger a re-rendering
        this.set({ 'title' : record.id ? record.display_name : _t("New") });
        this.update_pager(); // the mode must be actualized before updating the pager
        return $.when.apply(null, set_values).then(function() {
            if (!record.id) {
                // trigger onchange for new record after x2many with non-embedded views are loaded
                var fields_loaded = _.pluck(self.fields, 'is_loaded');
                $.when.apply(null, fields_loaded).done(function() {
                    self.do_onchange(null);
                });
            }
            self.on_form_changed();
            self.rendering_engine.init_fields().then(function() {
                self.is_initialized.resolve();
                self.record_loaded.resolve();
                if (self.sidebar) {
                    self.sidebar.do_attachement_update(self.dataset, self.datarecord.id);
                }
                if (record.id) {
                    self.do_push_state({id:record.id});
                } else {
                    self.do_push_state({});
                }
                self.$el.removeClass('oe_form_dirty');
            });
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
                self.trigger('load_record', _.clone(r));
            });
        }
        return $.when().then(this.trigger.bind(this, 'load_record', {}));
    },
    on_form_changed: function() {
        this.trigger("view_content_has_changed");
    },
    do_notify_change: function() {
        this.$el.addClass('oe_form_dirty');
    },
    _build_onchange_specs: function() {
        var self = this;
        var find = function(field_name, root) {
            var fields = [root];
            while (fields.length) {
                var node = fields.pop();
                if (!node) {
                    continue;
                }
                if (node.tag === 'field' && node.attrs.name === field_name) {
                    return node.attrs.on_change || "";
                }
                fields = _.union(fields, node.children);
            }
            return "";
        };

        self._onchange_fields = [];
        self._onchange_specs = {};
        _.each(this.fields, function(field, name) {
            self._onchange_fields.push(name);
            self._onchange_specs[name] = find(name, field.node);

            // we get the list of first-level fields of x2many firstly by
            // getting them from the field embedded views, then if no embedded
            // view is present for a loaded view, we get them from the default
            // view that has been loaded

            // gather embedded view objects
            var views = _.clone(field.field.views);
            // also gather default view objects
            if (field.viewmanager) {
                _.each(field.viewmanager.views, function(view, view_type) {
                    // add default view if it was not embedded and it is loaded
                    if (views[view_type] === undefined && view.controller) {
                        views[view_type] = view.controller.fields_view;
                    }
                });
            }
            _.each(views, function(view) {
                _.each(view.fields, function(_, subname) {
                    self._onchange_specs[name + '.' + subname] = find(subname, view.arch);
                });
            });
        });
    },
    _get_onchange_values: function() {
        var field_values = this.get_fields_values();
        if (field_values.id.toString().match(data.BufferedDataSet.virtual_id_regex)) {
            delete field_values.id;
        }
        if (this.dataset.parent_view) {
            // this belongs to a parent view: add parent field if possible
            var parent_view = this.dataset.parent_view;
            var child_name = this.dataset.child_name;
            var parent_name = parent_view.get_field_desc(child_name).relation_field;
            if (parent_name) {
                // consider all fields except the inverse of the parent field
                var parent_values = parent_view.get_fields_values();
                delete parent_values[child_name];
                field_values[parent_name] = parent_values;
            }
        }
        return field_values;
    },

    do_onchange: function(widget) {
        var self = this;
        if (self._onchange_specs === undefined) {
            self._build_onchange_specs();
        }
        var onchange_specs = self._onchange_specs;
        try {
            var def = $.when({});
            var change_spec = widget ? onchange_specs[widget.name] : null;
            if (!widget || (!_.isEmpty(change_spec) && change_spec !== "0")) {
                var ids = [],
                    trigger_field_name = widget ? widget.name : self._onchange_fields,
                    values = self._get_onchange_values(),
                    context = new data.CompoundContext(self.dataset.get_context());

                if (widget && widget.build_context()) {
                    context.add(widget.build_context());
                }
                if (self.dataset.parent_view) {
                    var parent_name = self.dataset.parent_view.get_field_desc(self.dataset.child_name).relation_field;
                    context.add({field_parent: parent_name});
                }

                if (self.datarecord.id && !data.BufferedDataSet.virtual_id_regex.test(self.datarecord.id)) {
                    // In case of a o2m virtual id, we should pass an empty ids list
                    ids.push(self.datarecord.id);
                }
                def = self.alive(self.dataset.call(
                    "onchange", [ids, values, trigger_field_name, onchange_specs, context]));
            }
            this.onchanges_mutex.exec(function(){
                return def.then(function(response) {
                    var fields = {};
                    if (widget){
                        fields[widget.name] = widget.field;
                    }
                    else{
                        fields = self.fields_view.fields;
                    }
                    var defs = [];
                    _.each(fields, function(field, fieldname){
                        if (field && field.change_default) {
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
                                defs.push(self.alive(new Model('ir.values').call(
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
                                }));
                            }
                        }
                    });
                    return _.isEmpty(defs) ? response : $.when.apply(null, defs);
                }).then(function(response) {
                    return self.on_processed_onchange(response);
                });
            });
            return this.onchanges_mutex.def;
        } catch(e) {
            console.error(e);
            crash_manager.show_message(e);
            return $.Deferred().reject();
        }
    },
    on_processed_onchange: function(result) {
        try {
        var fields = this.fields;
        _(result.domain).each(function (domain, fieldname) {
            var field = fields[fieldname];
            if (!field) { return; }
            field.node.attrs.domain = domain;
        });

        var def = $.when(!_.isEmpty(result.value) && this._internal_set_values(result.value));

        // FIXME XXX a list of warnings?
        if (!_.isEmpty(result.warning)) {
            this.warning_displayed = true;
            var dialog = new Dialog(this, {
                size: 'medium',
                title:result.warning.title,
                $content: QWeb.render("CrashManager.warning", result.warning)
            });
            dialog.open();
            dialog.on('closed', this, function () {
                this.warning_displayed = false;
            });
        }

        return def;
        } catch(e) {
            console.error(e);
            crash_manager.show_message(e);
            return $.Deferred().reject();
        }
    },
    _process_operations: function() {
        var self = this;
        return this.mutating_mutex.exec(function() {
            function onchanges_mutex () {return self.onchanges_mutex.def;}
            function iterate() {
                var mutex = new utils.Mutex();
                mutex.exec(onchanges_mutex);
                _.each(self.fields, function(field) {
                    mutex.exec(function(){
                        return field.commit_value();
                    });
                    mutex.exec(onchanges_mutex);
                });

                return mutex.def.then(function() {
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
                }).fail(function() {
                    self.save_list.pop();
                    return $.when();
                });
            }
            return iterate();
        });
    },
    _internal_set_values: function(values) {
        for (var f in values) {
            if (!values.hasOwnProperty(f)) { continue; }
            var field = this.fields[f];
            // If field is not defined in the view, just ignore it
            if (field) {
                var value_ = values[f];
                if (field.get_value() !== value_) {
                    field._inhibit_on_change_flag = true;
                    field.set_value(value_);
                    field._inhibit_on_change_flag = false;
                    field._dirty_flag = true;
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
        this.trigger('to_view_mode');
    },
    /**
     * Ask the view to switch to edit mode if possible. The view may not do it
     * if the current record is not yet saved. It will then stay in create mode.
     */
    to_edit_mode: function() {
        this.onchanges_mutex = new utils.Mutex();
        this._actualize_mode("edit");
        this.trigger('to_edit_mode');
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

        var viewMode = (mode === "view");
        this.$el.toggleClass('o_form_readonly', viewMode).toggleClass('o_form_editable', !viewMode);

        this.render_value_defs = [];
        this.set({actual_mode: mode});

        if(!viewMode) {
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
    disable_button: function () {
        this.$('.oe_form_buttons,.o_statusbar_buttons').add(this.$buttons).find('button').addClass('o_disabled').prop('disabled', true);
        this.is_disabled = true;
    },
    enable_button: function () {
        this.$('.oe_form_buttons,.o_statusbar_buttons').add(this.$buttons).find('button.o_disabled').removeClass('o_disabled').prop('disabled', false);
        this.is_disabled = false;
    },
    on_button_save: function() {
        var self = this;
        if (this.is_disabled) {
            return;
        }
        this.disable_button();
        return this.save().then(function(result) {
            self.trigger("save", result);
            return self.reload().then(function() {
                self.to_view_mode();
                core.bus.trigger('do_reload_needaction');
                core.bus.trigger('form_view_saved', self);
            }).always(function() {
                self.enable_button();
            });
        }).fail(function(){
            self.enable_button();
        });
    },
    on_button_cancel: function() {
        var self = this;
        this.can_be_discarded().then(function() {
            if (self.get('actual_mode') === 'create') {
                self.trigger('history_back');
            } else {
                self.to_view_mode();
                $.when.apply(null, self.render_value_defs).then(function(){
                    self.trigger('load_record', self.datarecord);
                });
            }
        });
        this.trigger('on_button_cancel');
        return false;
    },
    on_button_new: function() {
        return $.when(this.has_been_loaded)
            .then(this.can_be_discarded.bind(this))
            .then(this.load_defaults.bind(this));
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
                    if (self.dataset.size()) {
                        self.reload();
                        self.update_pager();
                    } else {
                        self.do_action('history_back');
                    }
                    def.resolve();
                });
            } else {
                utils.async_when().done(function () {
                    def.reject();
                });
            }
        });
        return def.promise();
    },
    can_be_discarded: function(message) {
        if (!this.$el.is('.oe_form_dirty')) {
            return $.Deferred().resolve();
        }

        message = message || _t("The record has been modified, your changes will be discarded. Are you sure you want to leave this page ?");

        var self = this;
        var def = $.Deferred();
        var options = {
            title: _t("Warning"),
            confirm_callback: function() {
                self.$el.removeClass('oe_form_dirty');
                this.on('closed', null, function() { // 'this' is the dialog widget
                    def.resolve();
                });
            },
            cancel_callback: function() {
                def.reject();
            },
        };
        var dialog = Dialog.confirm(this, message, options);
        dialog.$modal.on('hidden.bs.modal', function() {
            def.reject();
        });
        return def;
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
        return self._process_operations().then(function() {
            if (save_obj.error)
                return $.Deferred().reject();
            return $.when.apply($, save_obj.ret);
        }).done(function(result) {
            self.$el.removeClass('oe_form_dirty');
        });
    },
    _process_save: function(save_obj) {
        var self = this;
        var prepend_on_create = save_obj.prepend_on_create;
        var def_process_save = $.Deferred();
        try {
            var form_invalid = false,
                values = {},
                first_invalid_field = null,
                readonly_values = {},
                deferred = [];

            $.when.apply($, deferred).always(function () {

                _.each(self.fields, function (f) {
                    if (!f.is_valid()) {
                        form_invalid = true;
                        if (!first_invalid_field) {
                            first_invalid_field = f;
                        }
                    } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                        // Special case 'id' field, do not save this field
                        // on 'create' : save all non readonly fields
                        // on 'edit' : save non readonly modified fields
                        if (!f.get("readonly")) {
                            values[f.name] = f.get_value(true);
                        } else {
                            readonly_values[f.name] = f.get_value(true);
                        }
                    }

                });

                // Heuristic to assign a proper sequence number for new records that
                // are added in a dataset containing other lines with existing sequence numbers
                if (!self.datarecord.id && self.fields.sequence &&
                    !_.has(values, 'sequence') && !_.isEmpty(self.dataset.cache)) {
                    // Find current max or min sequence (editable top/bottom)
                    var current = _[prepend_on_create ? "min" : "max"](
                        _.map(self.dataset.cache, function(o){return o.values.sequence})
                    );
                    values['sequence'] = prepend_on_create ? current - 1 : current + 1;
                }
                if (form_invalid) {
                    self.set({'display_invalid_fields': true});
                    first_invalid_field.focus();
                    self.on_invalid();
                    def_process_save.reject();
                } else {
                    self.set({'display_invalid_fields': false});
                    var save_deferral;
                    if (!self.datarecord.id) {
                        // Creation save
                        save_deferral = self.dataset.create(values, {readonly_fields: readonly_values}).then(function(r) {
                            self.display_translation_alert(values);
                            return self.record_created(r, prepend_on_create);
                        }, null);
                    } else if (_.isEmpty(values)) {
                        // Not dirty, noop save
                        save_deferral = $.Deferred().resolve({}).promise();
                    } else {
                        // Write save
                        save_deferral = self.dataset.write(self.datarecord.id, values, {readonly_fields: readonly_values}).then(function(r) {
                            self.display_translation_alert(values);
                            return self.record_saved(r);
                        }, null);
                    }
                    save_deferral.then(function(result) {
                        def_process_save.resolve(result);
                    }).fail(function() {
                        def_process_save.reject();
                    });
                }
            });
        } catch (e) {
            console.error(e);
            return def_process_save.reject();
        }
        return def_process_save;
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
        this.trigger('record_saved', r);
        if (!r) {
            // should not happen in the server, but may happen for internal purpose
            return $.Deferred().reject();
        }
        return r;
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
            this.update_pager();
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
            if (self.dataset.index === null || self.dataset.index === undefined) {
                self.do_action('reload');
                return $.Deferred().reject().promise();
            }
            if (self.dataset.index < 0) {
                return $.when(self.on_button_new());
            } else {
                var fields = _.keys(self.fields_view.fields);
                fields.push('display_name');
                fields.push('__last_update');
                return self.dataset.read_index(fields,
                    {
                        context: { 'bin_size': true },
                        check_access_rule: true
                    }).then(function(r) {
                        self.trigger('load_record', r);
                    }).fail(function (){
                        self.do_action('history_back');
                    });
            }
        });
    },
    get_widgets: function() {
        return _.filter(this.getChildren(), function(obj) {
            return obj instanceof common.FormWidget;
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
            if(data.BufferedDataSet.virtual_id_regex.test(id))
                return false;
        }
        return true;
    },
    sidebar_eval_context: function () {
        return $.when(this.build_eval_context());
    },
    /*
     * Show a warning message if the user modified a translated field.  For each
     * field, the notification provides a link to edit the field's translations.
     */
    display_translation_alert: function(values) {
        if (_t.database.multi_lang) {
            var alert_fields = _.filter(this.translatable_fields, function(field) {
                return _.has(values, field.name)
            });
            if (alert_fields.length) {
                var $content = $(QWeb.render('translation-alert', {
                        fields: alert_fields,
                        lang: _t.database.parameters.name
                    }));
                // bind click event on "Update translations" links
                $content.find('.oe_field_translate').click(function(ev) {
                    ev.preventDefault();
                    _.find(alert_fields, {'name': ev.target.name}).on_translate();
                });
                // show notification
                this.once('to_view_mode', this, function () {
                    this.notify_in_form($content);
                });
            }
        }
    },
    /**
     * Add a notification box inside the form. The notification automatically
     * goes away (by default when switching to edit mode or changing the form
     * content.)
     *
     * @param {jQuery} $content
     * @param {Object} [options]
     * @param {String} [options.type], one of: "success", "info", "warning", "danger"
     * @param {String} [options.events], when to remove notification
     */
    notify_in_form: function ($content, options) {
        options = options || {};
        var type = options.type || 'info';
        var $box = $(QWeb.render('notification-box', {type: type}));
        $box.append($content);
        // create handler to remove notification box
        var events = options.events || 'to_edit_mode view_content_has_changed';
        this.once(events, null, function() {
            $box.remove();
        });
        // add content inside notification box on top of the sheet/form
        var $target = this.$('.o_form_sheet_bg').length ? this.$('.o_form_sheet_bg') : this.$el;
        $target.prepend($box);
    },
    open_defaults_dialog: function () {
        var self = this;
        var display = function (field, value) {
            var FieldSelection = core.form_widget_registry.get('selection');
            var FieldMany2One = core.form_widget_registry.get('many2one');
            if (!value) { return value; }
            if (field instanceof FieldSelection) {
                return _(field.get('values')).find(function (option) {
                    return option[0] === value;
                })[1];
            } else if (field instanceof FieldMany2One) {
                return field.get_displayed();
            }
            return value;
        };
        var fields = _.chain(this.fields)
            .map(function (field) {
                var value = field.get_value();
                // ignore fields which are empty, invisible, readonly, o2m
                // or m2m
                if (!value
                        || field.get('invisible')
                        || field.get("readonly")
                        || field.field.type === 'one2many'
                        || field.field.type === 'many2many'
                        || field.field.type === 'binary'
                        || field.password
                        || !_.isEmpty(field.field.depends)) {
                    return false;
                }

                return {
                    name: field.name,
                    string: field.string,
                    value: value,
                    displayed: display(field, value),
                };
            })
            .compact()
            .sortBy(function (field) { return field.string; })
            .value();
        var conditions = _.chain(self.fields)
            .filter(function (field) { return field.field.change_default; })
            .map(function (field) {
                var value = field.get_value();
                return {
                    name: field.name,
                    string: field.string,
                    value: value,
                    displayed: display(field, value),
                };
            })
            .value();
        var d = new Dialog(this, {
            title: _t("Set Default"),
            buttons: [
                {text: _t("Close"), close: true},
                {text: _t("Save default"), click: function () {
                    var $defaults = d.$el.find('#formview_default_fields');
                    var field_to_set = $defaults.val();
                    if (!field_to_set) {
                        $defaults.parent().addClass('o_form_invalid');
                        return;
                    }
                    var condition = d.$el.find('#formview_default_conditions').val(),
                        all_users = d.$el.find('#formview_default_all').is(':checked');
                    new data.DataSet(self, 'ir.values').call(
                        'set_default', [
                            self.model,
                            field_to_set,
                            self.fields[field_to_set].get_value(),
                            all_users,
                            true,
                            condition || false
                    ]).done(function () { d.close(); });
                }}
            ]
        });
        d.args = {
            fields: fields,
            conditions: conditions
        };
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
        return data.compute_domain(expression, this.fields);
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
        return new data.CompoundContext(a_dataset.get_context(), this._build_view_fields_values());
    },
});

core.view_registry.add('form', FormView);

return FormView;

});


odoo.define('web.FormRenderingEngine', function (require) {
"use strict";

var common = require('web.form_common');
var core = require('web.core');
var utils = require('web.utils');

var _t = core._t;
var QWeb = core.qweb;

/**
 * Default rendering engine for the form view.
 *
 * It is necessary to set the view using set_view() before usage.
 */
return core.Class.extend({
    init: function(view) {
        this.view = view;
    },
    set_fields_view: function(fvg) {
        this.fvg = fvg;
        this.version = parseFloat(this.fvg.arch.attrs.version);
        if (isNaN(this.version)) {
            this.version = 7.0;
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
    // Backward compatibility tools, current default version: v7
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
        var doc = $.parseXML(utils.json_node_to_xml(this.fvg.arch)).documentElement;
        // IE won't allow custom button@type and will revert it to spec default : 'submit'
        $('button', doc).each(function() {
            $(this).attr('data-button-type', $(this).attr('type')).attr('type', 'button');
        });
        // IE's html parser is also a css parser. How convenient...
        $('board', doc).each(function() {
            $(this).attr('layout', $(this).attr('style'));
        });
        return $(utils.xml_to_str(doc));
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

        this.$form.contents().appendTo(this.$target);
        this.handle_common_properties(this.$target, this.$form);

        this.to_replace = [];

        _.each(this.fields_to_init, function($elem) {
            var name = $elem.attr("name");
            if (!self.fvg.fields[name]) {
                throw new Error(_.str.sprintf(_t("Field '%s' specified in view could not be found."), name));
            }
            var obj = self.fields_registry.get_any([$elem.attr('widget'), self.fvg.fields[name].type]);
            if (!obj) {
                throw new Error(_.str.sprintf(_t("Widget type '%s' is not implemented"), $elem.attr('widget') || self.fvg.fields[name].type ));
            }
            var w = new (obj)(self.view, utils.xml_to_json($elem[0]));
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
            var obj = self.tags_registry.get(tag_name);
            var w = new (obj)(self.view, utils.xml_to_json($elem[0]));
            self.to_replace.push([w, $elem]);
        });
        _.each(this.widgets_to_init, function($elem) {
            var widget_type = $elem.attr("type");
            var obj = self.widgets_registry.get(widget_type);
            var w = new (obj)(self.view, utils.xml_to_json($elem[0]));
            self.to_replace.push([w, $elem]);
        });
    },
    init_fields: function() {
        var defs = [];
        _.each(this.to_replace, function(el) {
            defs.push(el[0].replace(el[1]));
            if (el[1].children().length) {
                el[0].$el.append(el[1].children());
            }
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
            return (tagname === 'button') ? this.process_button($tag) : $tag;
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
    process_button: function ($button) {
        var self = this;
        $button.children().each(function() {
            self.process($(this));
        });
        return $button;
    },
    process_widget: function($widget) {
        this.widgets_to_init.push($widget);
        return $widget;
    },
    process_sheet: function($sheet) {
        var $new_sheet = this.render_element('FormRenderingSheet', $sheet.getAttributes());
        this.handle_common_properties($new_sheet, $sheet);
        var $dst = $new_sheet.find('.o_form_sheet');
        $sheet.contents().appendTo($dst);
        $sheet.before($new_sheet).remove();
        this.process($new_sheet);
    },
    process_form: function($form) {
        if ($form.find('> sheet').length === 0) {
            $form.addClass('o_form_nosheet');
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

        // Processes a group containing nested groups
        // Renders a div for each nested group, into a div that is the outer group
        // The nested groups's width is a percentage according to col and colspan attributes
        var _process_outer_group = function(col) {
            var $new_group = self.render_element('FormRenderingOuterGroup', $group.getAttributes());
            $group.children().each(function() {
                var $child = $(this);
                var tagName = $child[0].tagName.toLowerCase();
                var colspan = parseInt($child.attr('colspan') || 1, 10);

                if (tagName === 'newline') {
                    $new_group.append($('<br>')); // Skip to the next line
                    return;
                }
                // compute child's classname from col and colspan attributes
                $child.addClass('o_group_col_' + Math.min(Math.floor(colspan/col*12), 12));
                $new_group.append($child);

                children.push($child[0]);
            });
            return $new_group;
        };
        // Processes a group containing no nested group
        // Renders an HTML table
        var _process_inner_group = function(col) {
            var $new_group = self.render_element('FormRenderingInnerGroup', $group.getAttributes());
            $new_group.find('td').attr('colspan', col); // Group's title spans all column
            var row_col = col;
            var $row = null;

            $group.children().each(function() {
                var $child = $(this);
                var tagName = $child[0].tagName.toLowerCase();
                var colspan = parseInt($child.attr('colspan') || 1, 10);

                if (tagName === 'newline') {
                    $row = null; // Start with a new row
                    return;
                }
                row_col -= colspan;
                if (!$row || row_col < 0) { // Append a new row to the group
                    $row = $('<tr>').appendTo($new_group);
                    row_col = col-colspan;
                }
                $('<td>').attr('colspan', colspan).append($child).appendTo($row);

                children.push($child[0]);
            });

            // Some kind of an hack
            // Add width on table's cell to avoid automatic layout of table which
            // makes first col to take full width available (typically, first col contains label)
            $new_group.find('tr').each(function() {
                var $tr = $(this);
                var nonlabel_width = 100/(col - $tr.find('td > label:first-child').length);
                $tr.find('td').each(function() {
                    var $td = $(this);
                    var $child = $td.children(':first');
                    if ($child.is("label")) {
                        $td.addClass("o_td_label");
                    } else {
                        $td.css("width", (nonlabel_width*parseInt($td.attr('colspan')))+"%");
                    }
                });

            });
            return $new_group;
        };

        // Preprocess field children
        $group.children('field').each(function() {
            self.preprocess_field($(this));
        });

        // Process group
        var nested_groups = $group.children('group').length; // Detect possible nested groups
        var children = [];
        var col = parseInt($group.attr('col') || 2, 10);
        var $new_group;
        if (nested_groups) {
            $new_group = _process_outer_group(col);
        } else {
            $new_group = _process_inner_group(col);
        }
        this.handle_common_properties($new_group, $group);

        // Process group's children
        $group.before($new_group).remove();
        _.each(children, function(el) {
            self.process($(el));
        });

        return $new_group;
    },
    process_notebook: function($notebook) {
        var self = this;

        // Extract useful info from the notebook xml declaration
        var pages = [];
        $notebook.find('> page').each(function() {
            var $page = $(this);
            var page_attrs = $page.getAttributes();
            page_attrs.id = _.uniqueId('notebook_page_');
            page_attrs.contents = $page.html();
            page_attrs.ref = $page;  // reference to the current page node in the xml declaration
            pages.push(page_attrs);
        });

        // Render the notebook and replace $notebook with it
        var $new_notebook = self.render_element('FormRenderingNotebook', {'pages': pages});
        $notebook.before($new_notebook).remove();

        // Bind the invisibility changers and find the page to display
        var pageid_to_display;
        _.each(pages, function(page) {
            var $tab = $new_notebook.find('a[href=#' + page.id + ']').parent();
            var $content = $new_notebook.find('#' + page.id);

            // Case: <page autofocus="autofocus">;
            // We attach the autofocus attribute to the node because it can be useful during the
            // page execution
            self.attach_node_attr($tab, page.ref, 'autofocus');
            self.attach_node_attr($content, page.ref, 'autofocus');
            if (!pageid_to_display && page.autofocus) {
                // If multiple autofocus, keep the first one
                pageid_to_display = page.id;
            }

            // Case: <page attrs="{'invisible': domain}">;
            self.handle_common_properties($tab, page.ref, common.NotebookInvisibilityChanger);
            self.handle_common_properties($content, page.ref, common.NotebookInvisibilityChanger);
        });
        if (!pageid_to_display) {
            pageid_to_display = $new_notebook.find('div[role="tabpanel"]:not(.o_form_invisible):first').attr('id');
        }

        // Display page. Note: we can't use bootstrap's show function because it is looking for
        // document attached DOM, and the form view is only attached when everything is processed
        $new_notebook.find('a[href=#' + pageid_to_display + ']').parent().addClass('active');
        $new_notebook.find('#' + pageid_to_display).addClass('active');

        self.process($new_notebook.children());
        self.handle_common_properties($new_notebook, $notebook);

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
            _for: name ? _.uniqueId('o_field_input_') : undefined,
        };
        var $new_label = this.render_element('FormRenderingLabel', dict);
        $label.before($new_label).remove();
        this.handle_common_properties($new_label, $label);
        if (name) {
            this.labels[name] = $new_label;
        }
        return $new_label;
    },
    handle_common_properties: function($new_element, $node, InvisibilityChanger) {
        var str_modifiers = $node.attr("modifiers") || "{}";
        var modifiers = JSON.parse(str_modifiers);
        var ic = null;
        if (modifiers.invisible !== undefined) {
            var InvisibilityChangerCls = InvisibilityChanger || common.InvisibilityChanger;
            ic = new InvisibilityChangerCls(this.view, this.view, modifiers.invisible, $new_element);
        }
        $new_element.addClass($node.attr("class") || "");
        $new_element.attr('style', $node.attr('style'));
        return {invisibility_changer: ic,};
    },
    /**
    * Attach a node attribute to an html element to be able to use it after
    * the processing of the page.
    */
    attach_node_attr: function($new_element, $node, attr) {
        $new_element.data(attr, $node.attr(attr));
    }
});

});
