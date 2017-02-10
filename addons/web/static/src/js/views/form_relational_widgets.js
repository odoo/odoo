odoo.define('web.form_relational', function (require) {
"use strict";

var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var common = require('web.form_common');
var ListView = require('web.ListView');
require('web.ListEditor'); // one must be sure that the include of ListView are done (for eg: add start_edition methods)
var Model = require('web.DataModel');
var session = require('web.session');
var utils = require('web.utils');
var ViewManager = require('web.ViewManager');

var _t = core._t;
var QWeb = core.qweb;
var COMMANDS = common.commands;
var list_widget_registry = core.list_widget_registry;

var M2ODialog = Dialog.extend({
    template: "M2ODialog",
    init: function(parent) {
        this.name = parent.string;
        this._super(parent, {
            title: _.str.sprintf(_t("Create a %s"), parent.string),
            size: 'medium',
            buttons: [
                {text: _t('Create'), classes: 'btn-primary', click: function(e) {
                    if (this.$("input").val() !== ''){
                        this.getParent()._quick_create(this.$("input").val());
                        this.close();
                    } else {
                        e.preventDefault();
                        this.$("input").focus();
                    }
                }},

                {text: _t('Create and edit'), classes: 'btn-primary', close: true, click: function() {
                    this.getParent()._search_create_popup("form", undefined, this.getParent()._create_context(this.$("input").val()));
                }},

                {text: _t('Cancel'), close: true}
            ]
        });
    },
    start: function() {
        var text = _.str.sprintf(_t("You are creating a new %s, are you sure it does not exist yet?"), this.name);
        this.$("p").text(text);
        this.$("input").val(this.getParent().$input.val());
    },
});

var FieldMany2One = common.AbstractField.extend(common.CompletionFieldMixin, common.ReinitializeFieldMixin, {
    template: "FieldMany2One",
    events: {
        'keydown input': function (e) {
            switch (e.which) {
                case $.ui.keyCode.UP:
                case $.ui.keyCode.DOWN:
                    e.stopPropagation();
            }
        },
    },
    init: function(field_manager, node) {
        this._super(field_manager, node);
        common.CompletionFieldMixin.init.call(this);
        this.display_value = {};
        this.display_value_backup = {};
        this.last_search = [];
        this.floating = false;
        this.current_display = null;
        this.is_started = false;
        this.ignore_focusout = false;
    },
    reinit_value: function(val) {
        this.internal_set_value(val);
        this.floating = false;
        if (this.is_started && !this.no_rerender) {
            this.render_value();
        }
    },
    initialize_field: function() {
        this.is_started = true;
        core.bus.on('click', this, function() {
            if (!this.get("effective_readonly") && this.$input && this.$input.autocomplete('widget').is(':visible')) {
                this.$input.autocomplete("close");
            }
        });
        common.ReinitializeFieldMixin.initialize_field.call(this);
    },
    initialize_content: function() {
        if (!this.get("effective_readonly")) {
            this.render_editable();
        }
    },
    destroy_content: function () {
        if (this.$dropdown) {
            this.$dropdown.off('click');
            delete this.$dropdown;
        }
        if (this.$input) {
            if (this.$input.data('ui-autocomplete')) {
                this.$input.autocomplete("destroy");
            }
            this.$input.closest(".modal .modal-content").off('scroll');
            this.$input.off('keyup blur autocompleteclose autocompleteopen ' +
                            'focus focusout change keydown');
            delete this.$input;
        }
        if (this.$follow_button) {
            this.$follow_button.off('blur focus click');
            delete this.$follow_button;
        }
    },
    destroy: function () {
        this.destroy_content();
        return this._super();
    },
    init_error_displayer: function() {
        // nothing
    },
    hide_error_displayer: function() {
        // doesn't work
    },
    show_error_displayer: function() {
        new M2ODialog(this).open();
    },
    render_editable: function() {
        var self = this;
        this.$input = this.$("input");

        this.init_error_displayer();
        self.$input.on('focus', function() {
            self.hide_error_displayer();
        });

        this.$dropdown = this.$(".o_dropdown_button");
        this.$follow_button = this.$(".o_external_button");

        this.$follow_button.click(function(ev) {
            ev.preventDefault();
            if (!self.get('value')) {
                self.focus();
                return;
            }
            var context = self.build_context().eval();
            var model_obj = new Model(self.field.relation);
            model_obj.call('get_formview_id', [[self.get("value")], context]).then(function(view_id){
                var pop = new common.FormViewDialog(self, {
                    res_model: self.field.relation,
                    res_id: self.get("value"),
                    context: self.build_context(),
                    title: _t("Open: ") + self.string,
                    view_id: view_id,
                    readonly: !self.can_write
                }).open();
                pop.on('write_completed', self, function(){
                    self.display_value = {};
                    self.display_value_backup = {};
                    self.render_value();
                    self.focus();
                    self.trigger('changed_value');
                });
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
        this.$input.on('click', function() {
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");
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
        this.$input.closest(".modal .modal-content").on('scroll', this, close_autocomplete);

        self.ed_def = $.Deferred();
        self.uned_def = $.Deferred();
        var ed_delay = 200;
        var ed_duration = 15000;
        var anyoneLoosesFocus = function (e) {
            if (self.ignore_focusout) { return; }
            var used = false;
            if (self.floating) {
                if (self.last_search.length > 0) {
                    if (self.last_search[0][0] != self.get("value")) {
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.display_value["" + self.last_search[0][0]] = self.last_search[0][1];
                        self.reinit_value(self.last_search[0][0]);
                        self.last_search = [];
                    } else {
                        used = true;
                        self.render_value();
                    }
                } else {
                    used = true;
                }
                self.floating = false;
            }
            var has_changed = (self.get("value") === false || self.display_value["" + self.get("value")] !== self.$input.val());
            if (used && has_changed && ! self.no_ed && ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                self.ed_def.reject();
                self.uned_def.reject();
                self.ed_def = $.Deferred();
                self.ed_def.done(function() {
                    self.can_create && self.$input && self.show_error_displayer();
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
            autocompleteclose: function () { setTimeout(function() {ignore_blur = false;},0); },
            blur: function () {
                // autocomplete open
                if (ignore_blur) { $(this).focus(); return; }
                if (_(self.getChildren()).any(function (child) {
                    return child instanceof common.ViewDialog;
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
                    self.display_value_backup = {};
                    self.display_value["" + item.id] = item.name;
                    self.reinit_value(item.id);
                } else if (item.action) {
                    item.action();
                    // Cancel widget blurring, to avoid form blur event
                    self.trigger('focused');
                }
                return false;
            },
            focus: function(e, ui) {
                e.preventDefault();
            },
            autoFocus: true,
            html: true,
            // disabled to solve a bug, but may cause others
            //close: anyoneLoosesFocus,
            minLength: 0,
            delay: 200,
        });
        // set position for list of suggestions box
        this.$input.autocomplete( "option", "position", { my : "left top", at: "left bottom" } );
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
        if (!this.get("value")) {
            this.display_string(null);
            return;
        }
        var display = this.display_value["" + this.get("value")];
        if (display) {
            this.display_string(display);
            return;
        }
        if (!no_recurse) {
            var dataset = new data.DataSetStatic(this, this.field.relation, self.build_context());
            var def = this.alive(dataset.name_get([self.get("value")])).done(function(data) {
                if (!data[0]) {
                    self.do_warn(_t("Render"),
                        _.str.sprintf(_t("No value found for the field %s for value %s"), self.field.string, self.get("value")));
                    return;
                }
                self.display_value["" + self.get("value")] = data[0][1];
                self.render_value(true);
            }).fail( function (data, event) {
                // avoid displaying crash errors as many2One should be name_get compliant
                event.preventDefault();
                self.display_value["" + self.get("value")] = self.display_value_backup["" + self.get("value")];
                self.render_value(true);
            });
            if (this.view && this.view.render_value_defs){
                this.view.render_value_defs.push(def);
            }
        }
    },
    display_string: function (str) {
        var noValue = (str === null);
        if (!this.get("effective_readonly")) {
            this.$input.val(noValue ? "" : (str.split("\n")[0].trim() || $(data.noDisplayContent).text()));
            this.current_display = this.$input.val();
            this.$follow_button.toggle(!this.is_false());
            this.$el.toggleClass('o_with_button', !!this.$follow_button && this.$follow_button.length > 0 && !this.is_false());
        } else {
            this.$el.html(noValue ? "" : (_.escape(str.trim()).split("\n").join("<br/>") || data.noDisplayContent));
            // Define callback to perform when clicking on the field
            if (!this.options.no_open) {
                // Remove potential previously added event handler
                this.$el.off('click');
                // Ensure that the callback is performed only once even with multiple clicks
                var execute_formview_action_once = _.once(this.execute_formview_action.bind(this));
                this.$el.click(function (ev) {
                    ev.preventDefault();
                    execute_formview_action_once();
                });
            }
        }
    },
    execute_formview_action: function() {
        var self = this;
        var context = self.build_context().eval();
        (new Model(self.field.relation)).call('get_formview_action', [[self.get("value")], context]).then(function(action) {
            self.do_action(action);
        });
    },
    set_value: function(value_) {
        if (value_ instanceof Array) {
            this.display_value = {};
            this.display_value_backup = {};
            if (! this.options.always_reload) {
                this.display_value["" + value_[0]] = value_[1];
            }
            else {
                this.display_value_backup["" + value_[0]] = value_[1];
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
        this.display_value_backup = {};
        this.reinit_value(id);
    },
    is_false: function() {
        return ! this.get("value");
    },
    focus: function () {
        var input = !this.get('effective_readonly') && this.$input && this.$input[0];
        return input ? input.focus() : false;
    },
    _quick_create: function() {
        this.no_ed = true;
        this.ed_def.reject();
        return common.CompletionFieldMixin._quick_create.apply(this, arguments);
    },
    _search_create_popup: function() {
        this.no_ed = true;
        this.ed_def.reject();
        this.ignore_focusout = true;
        this.reinit_value(false);
        var res = common.CompletionFieldMixin._search_create_popup.apply(this, arguments);
        this.ignore_focusout = false;
        this.no_ed = false;
        return res;
    },
});

/**
 * A Abstract field for one2many and many2many field
 * For all fields on2many or many2many:
 *  - this.get('value') contains a list of ids and virtual ids
 *  - get_value() return an odoo write command list
 */
var AbstractManyField = common.AbstractField.extend({
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.dataset = new X2ManyDataSet(this, this.field.relation, this.build_context());
        this.dataset.x2m = this;
        this.dataset.parent_view = this.view;
        this.dataset.child_name = this.name;
        this.set('value', []);
        this.starting_ids = [];
        this.mutex = new utils.Mutex();
        this.view.on("load_record", this, this._on_load_record);
        this.dataset.on('dataset_changed', this, function() {
            var options = _.clone(_.last(arguments));
            if (!_.isObject(options) || _.isArray(options)) {
                options = {};
            }
            // don't trigger changes if all commands are not resolved
            // the editable lists change the dataset without call AbstractManyField methods
            if (!self.internal_dataset_changed && !options.internal_dataset_changed) {
                self.trigger("change:commands", options);
            }
        });
        this.on("change:commands", this, function (options) {
            self._inhibit_on_change_flag = !!options._inhibit_on_change_flag;
            self.set({'value': self.dataset.ids.slice()});
            self._inhibit_on_change_flag = false;
        });
    },

    _on_load_record: function (record) {
        this.starting_ids = [];
        // don't set starting_ids for the new record
        if (record.id && record[this.name] && (!isNaN(record.id) || record.id.indexOf(this.dataset.virtual_id_prefix) === -1)) {
            this.starting_ids =  this.get('value').slice();
        }
        this.trigger("load_record", record);
    },

    set_value: function(ids) {
        ids = (ids || []).slice();
        if (_.find(ids, function(id) { return typeof(id) === "string"; } )) {
            throw new Error("set_value of '"+this.name+"' must receive an list of ids without virtual ids.", ids);
        }
        if (_.find(ids, function(id) { return typeof(id) !== "number"; } )) {
            return this.send_commands(ids, {'_inhibit_on_change_flag': this._inhibit_on_change_flag});
        }
        this.dataset.reset_ids(ids);
        return $.when(this._super(ids));
    },

    internal_set_value: function(ids) {
        if (_.isEqual(ids, this.get("value"))) {
            return;
        }
        var tmp = this.no_rerender;
        this.no_rerender = true;
        var def = this.data_replace(ids.slice());
        this.no_rerender = tmp;
        return def;
    },

    commit_value: function() {
        return this.mutex.def;
    },

    /*
    *@value: data {object} contains all value to send to the db
    *        options {object} options sent to the dataset (like the default values)
    *@return deferred resolve with the created virtual id
    */
    data_create: function (data, options) {
        return this.send_commands([COMMANDS.create(data)], options);
    },

    /*
    *@value: id {int or string} id or virtual id of the record to update
    *        data {object} contains all value to send to the db
    *        options {object} options sent to the dataset
    *@return deferred
    */
    data_update: function (id, data, options) {
        return this.send_commands([COMMANDS.update(id, data)], options);
    },

    /*
    *@value: id {int or string} id or virtual id of the record to add
    *        options {object} options sent to the dataset
    *@return deferred
    */
    data_link: function (id, options) {
        return this.send_commands([COMMANDS.link_to(id)], options);
    },

    /*
    *@value: ids {array} list of ids or virtual ids of the record to add
    *        options {object} options sent to the dataset
    *@return deferred
    */
    data_link_multi: function (ids, options) {
        return this.send_commands(_.map(ids, function (id) { return COMMANDS.link_to(id); }), options);
    },

    /*
    *@value: id {int or string} id or virtual id of the record to unlink or delete (function of field type)
    *@return deferred
    */
    data_delete: function (id) {
        return this.send_commands([COMMANDS.delete(id)]);
    },

    /*
    *@value: id {int or string} id or virtual id of the record to removes relation (unlink or delete function of field type)
    *@return deferred
    */
    data_forget: function (id) {
        return this.send_commands([COMMANDS.forget(id)]);
    },

    /*
    *@value: ids {array} list of ids or virtual ids of the record who replace the previous list
    *        options {object} options sent to the dataset
    *@return deferred
    */
    data_replace: function (ids, options) {
        return this.send_commands([COMMANDS.replace_with(ids)], options);
    },

    /*
    *@value: ids {array} list of ids or virtual ids of the record to read
    *        fields {array} list of the field to read
    *        options {object} options sent to the dataset
    *@return deferred resolve with the records
    */
    data_read: function (ids, fields, options) {
        return this.dataset.read_ids(ids, fields, options);
    },

    /**
     *Compute the write command list into the dataset
     *@value: command_list {array} command list
     *        options {object} options for the datasets (eg: the default values)
     *@return : deferred
     */
    send_commands: function (command_list, options) {
        var self = this;
        var def = $.Deferred();
        var dataset = this.dataset;
        var res = true;
        options = options || {};
        var internal_options = _.extend({}, options, {'internal_dataset_changed': true});

        _.each(command_list, function(command) {
            self.mutex.exec(function() {
                var id = command[1];
                switch (command[0]) {
                    case COMMANDS.CREATE:
                        var data = _.clone(command[2]);
                        delete data.id;
                        return dataset.create(data, internal_options).then(function (id) {
                            dataset.ids.push(id);
                            res = id;
                        });
                    case COMMANDS.UPDATE:
                        return dataset.write(id, command[2], internal_options).then(function () {
                            if (dataset.ids.indexOf(id) === -1) {
                                dataset.ids.push(id);
                                res = id;
                            }
                        });
                    case COMMANDS.FORGET:
                        return dataset.unlink([id]);
                    case COMMANDS.DELETE:
                        return dataset.unlink([id]);
                    case COMMANDS.LINK_TO:
                        if (dataset.ids.indexOf(id) === -1) {
                            return dataset.add_ids([id], internal_options);
                        }
                        return;
                    case COMMANDS.DELETE_ALL:
                        return dataset.reset_ids([], {keep_read_data: true});
                    case COMMANDS.REPLACE_WITH:
                        dataset.ids = [];
                        return dataset.alter_ids(command[2], internal_options);
                    default:
                        throw new Error("send_commands to '"+self.name+"' receive a non command value." +
                            "\n" + JSON.stringify(command_list));
                }
            });
        });

        this.mutex.def.then(function () {
            self.trigger("change:commands", options);
            def.resolve(res);
        });
        return def;
    },

    /**
     *return list of commands: create and update (and delete_all if need) (function of the field type)
     */
    get_value: function() {
        var self = this,
            is_one2many = this.field.type === "one2many",
            not_delete = this.options.not_delete,
            starting_ids = this.starting_ids.slice(),
            replace_with_ids = [],
            add_ids = [],
            command_list = [],
            id, index, record;

        _.each(this.get('value'), function (id) {
            index = starting_ids.indexOf(id);
            if (index !== -1) {
                starting_ids.splice(index, 1);
            }
            var record = self.dataset.get_cache(id);
            if (!_.isEmpty(record.changes)) {
                var values = _.clone(record.changes);
                // format many2one values
                for (var k in values) {
                    if ((values[k] instanceof Array) && values[k].length === 2 && typeof values[k][0] === "number" && typeof values[k][1] === "string") {
                        values[k] = values[k][0];
                    }
                }
                if (record.to_create) {
                    command_list.push(COMMANDS.create(values));
                } else {
                    command_list.push(COMMANDS.update(record.id, values));
                }
                return;
            }
            if (!is_one2many || not_delete || self.dataset.delete_all) {
                replace_with_ids.push(id);
            } else {
                command_list.push(COMMANDS.link_to(id));
            }
        });
        if ((!is_one2many || not_delete || self.dataset.delete_all) && (replace_with_ids.length || starting_ids.length)) {
            _.each(command_list, function (command) {
                if (command[0] === COMMANDS.UPDATE) {
                    replace_with_ids.push(command[1]);
                }
            });
            command_list.unshift(COMMANDS.replace_with(replace_with_ids));
        }

        _.each(starting_ids, function(id) {
            if (is_one2many && !not_delete) {
                command_list.push(COMMANDS.delete(id));
            } else if (is_one2many && !self.dataset.delete_all) {
                command_list.push(COMMANDS.forget(id));
            }
        });

        return command_list;
    },

    is_valid: function () {
        return this.mutex.def.state() === "resolved" && this._super();
    },

    is_false: function() {
        return _(this.get('value')).isEmpty();
    },

    destroy: function () {
        this.view.off("load_record", this, this._on_load_record);
        this._super();
    }
});

var FieldX2Many = AbstractManyField.extend({
    multi_selection: false,
    disable_utility_classes: true,
    x2many_views: {},
    view_options: {},
    default_view: 'tree',
    init: function(field_manager, node) {
        this._super(field_manager, node);

        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;
        this.is_started = false;
        this.set_value([]);
    },
    start: function() {
        this._super.apply(this, arguments);
        var self = this;

        this.load_views();
        var destroy = function() {
            self.is_loaded = self.is_loaded.then(function() {
                self.renderElement();
                self.viewmanager.destroy();
                return $.when(self.load_views()).done(function() {
                    self.reload_current_view();
                });
            });
        };
        this.is_loaded.done(function() {
            self.on("change:effective_readonly", self, destroy);
        });
        this.view.on("on_button_cancel", this, destroy);
        this.is_started = true;
        this.reload_current_view();
    },
    load_views: function() {
        var self = this;

        var view_types = this.node.attrs.mode;
        view_types = !!view_types ? view_types.split(",") : [this.default_view];
        var views = [];
        _.each(view_types, function(view_type) {
            if (! _.include(["list", "tree", "graph", "kanban"], view_type)) {
                throw new Error(_.str.sprintf(_t("View type '%s' is not supported in X2Many."), view_type));
            }
            var view = {
                view_id: false,
                view_type: view_type === "tree" ? "list" : view_type,
                fields_view: self.field.views && self.field.views[view_type],
                options: {},
            };
            if(view.view_type === "list") {
                _.extend(view.options, {
                    action_buttons: false, // to avoid 'Save' and 'Discard' buttons to appear in X2M fields
                    addable: null,
                    selectable: self.multi_selection,
                    sortable: true,
                    import_enabled: false,
                    deletable: true
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        deletable: null,
                        reorderable: false,
                    });
                }
            } else if (view.view_type === "kanban") {
                _.extend(view.options, {
                    action_buttons: true,
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

        this.viewmanager = new X2ManyViewManager(this, this.dataset, views, this.view_options, this.x2many_views);
        this.viewmanager.x2m = self;
        var def = $.Deferred().done(function() {
            self.initial_is_loaded.resolve();
        });
        this.viewmanager.on("controller_inited", self, function(view_type, controller) {
            controller.x2m = self;
            if (view_type == "list") {
                if (self.get("effective_readonly")) {
                    controller.on('edit:before', self, function (e) {
                        e.cancel = true;
                    });
                    _(controller.columns).find(function (column) {
                        if (!(column instanceof list_widget_registry.get('field.handle'))) {
                            return false;
                        }
                        column.modifiers.invisible = true;
                        return true;
                    });
                }
            } else if (view_type == "graph") {
                self.reload_current_view();
            }
            def.resolve();
        });
        this.viewmanager.on("switch_mode", self, function(n_mode) {
            $.when(self.commit_value()).done(function() {
                if (n_mode === "list") {
                    utils.async_when().done(function() {
                        self.reload_current_view();
                    });
                }
            });
        });
        utils.async_when().done(function () {
            self.$el.addClass('o_view_manager_content');
            self.alive(self.viewmanager.attachTo(self.$el));
        });
        return def;
    },
    reload_current_view: function() {
        var self = this;
        self.is_loaded = self.is_loaded.then(function() {
            var view = self.get_active_view();
            if (view.type === "list") {
                view.controller.current_min = 1;
                return view.controller.reload_content();
            } else if (view.controller.do_search) {
                return view.controller.do_search(self.build_domain(), self.dataset.get_context(), []);
            }
        }, undefined);
        return self.is_loaded;
    },
    get_active_view: function () {
        /**
         * Returns the current active view if any.
         */
        return (this.viewmanager && this.viewmanager.active_view);
    },
    set_value: function(value_) {
        var self = this;
        this._super(value_).then(function () {
            if (self.is_started && !self.no_rerender) {
                return self.reload_current_view();
            }
        });
    },
    commit_value: function() {
        var view = this.get_active_view();
        if (view && view.type === "list" && view.controller.__focus) {
            return $.when(this.mutex.def, view.controller._on_blur_one2many());
        }
        return this.mutex.def;
    },
    is_syntax_valid: function() {
        var view = this.get_active_view();
        if (!view){
            return true;
        }
        switch (this.viewmanager.active_view.type) {
        case 'form':
            return _(view.controller.fields).chain()
                .invoke('is_valid')
                .all(_.identity)
                .value();
        case 'list':
            return view.controller.is_valid();
        }
        return true;
    },
    is_false: function() {
        return _(this.dataset.ids).isEmpty();
    },
});

var X2ManyDataSet = data.BufferedDataSet.extend({
    get_context: function() {
        this.context = this.x2m.build_context();
        var self = this;
        _.each(arguments, function(context) {
            self.context.add(context);
        });
        return this.context;
    },
});

var X2ManyViewManager = ViewManager.extend({
    custom_events: {
        // Catch event scrollTo to prevent scrolling to the top when using the
        // pager of List and Kanban views in One2Many fields
        'scrollTo': function() {},
    },
    init: function(parent, dataset, views, flags, x2many_views) {
        // By default, render buttons and pager in X2M fields, but no sidebar
        flags = _.extend({}, flags, {
            headless: false,
            search_view: false,
            action_buttons: true,
            pager: true,
            sidebar: false,
        });
        this.control_panel = new ControlPanel(parent, "X2ManyControlPanel");
        this.set_cp_bus(this.control_panel.get_bus());
        this._super(parent, dataset, views, flags);
        this.registry = core.view_registry.extend(x2many_views);
    },
    start: function() {
        this.control_panel.prependTo(this.$el);
        return this._super();
    },
    switch_mode: function(mode, unused) {
        if (mode !== 'form') {
            return this._super(mode, unused);
        }
        var self = this;
        var id = self.x2m.dataset.index !== null ? self.x2m.dataset.ids[self.x2m.dataset.index] : null;
        var pop = new common.FormViewDialog(this, {
            res_model: self.x2m.field.relation,
            res_id: id,
            context: self.x2m.build_context(),
            title: _t("Open: ") + self.x2m.string,
            create_function: function(data, options) {
                return self.x2m.data_create(data, options);
            },
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: self.x2m.get("effective_readonly")
        }).open();
        pop.on("elements_selected", self, function() {
            self.x2m.reload_current_view();
        });
    },
});

var X2ManyListView = ListView.extend({
    is_valid: function () {
        if (!this.fields_view || !this.editable()){
            return true;
        }
        if (_.isEmpty(this.records.records)){
            return true;
        }
        var fields = this.editor.form.fields;
        var current_values = {};
        _.each(fields, function(field){
            field._inhibit_on_change_flag = true;
            field.__no_rerender = field.no_rerender;
            field.no_rerender = true;
            current_values[field.name] = field.get('value');
        });
        var cached_records = _.filter(this.dataset.cache, function(item){return !_.isEmpty(item.values) && !item.to_delete;});
        var valid = _.every(cached_records, function(record){
            _.each(fields, function(field){
                var value = record.values[field.name];
                field._inhibit_on_change_flag = true;
                field.no_rerender = true;
                field.set_value(_.isArray(value) && _.isArray(value[0]) ? [COMMANDS.delete_all()].concat(value) : value);
            });
            return _.every(fields, function(field){
                field.process_modifiers();
                field._check_css_flags();
                return field.is_valid();
            });
        });
        _.each(fields, function(field){
            field.set('value', current_values[field.name], {silent: true});
            field._inhibit_on_change_flag = false;
            field.no_rerender = field.__no_rerender;
        });
        return valid;
    },
    render_pager: function($node, options) {
        options = _.extend(options || {}, {
            single_page_hidden: true,
        });
        this._super($node, options);
    },
    display_nocontent_helper: function () {
        return false;
    },
});

/**
 * ListView.List subclass adding an "Add an item" row to replace the Create
 * button in the ControlPanel.
 */
var X2ManyList = ListView.List.extend({
    pad_table_to: function (count) {
        var ftype = this.view.x2m.field.type;
        var is_readonly = this.view.x2m.get('effective_readonly');
        if (is_readonly || (ftype === 'one2many' && !this.view.is_action_enabled('create'))) {
            this._super(count);
            return;
        }

        this._super(count > 0 ? count - 1 : 0);

        var self = this;
        var columns = _(this.columns).filter(function (column) {
            return column.invisible !== '1';
        }).length;
        if (this.options.selectable) { columns++; }
        if (this.options.deletable) { columns++; }

        var $cell = $('<td>', {
            colspan: columns,
            'class': 'o_form_field_x2many_list_row_add'
        }).append(
            $('<a>', {href: '#'}).text(_t("Add an item"))
                .click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var def;
                    if (self.view.editable()) {
                        // FIXME: there should also be an API for that one
                        if (self.view.editor.form.__blur_timeout) {
                            clearTimeout(self.view.editor.form.__blur_timeout);
                            self.view.editor.form.__blur_timeout = false;
                        }
                        def = self.view.save_edition();
                    }
                    $.when(def).done(self.view.do_add_record.bind(self));
                }));

        var $padding = this.$current.find('tr:not([data-id]):first');
        var $newrow = $('<tr>').append($cell);
        if ($padding.length) {
            $padding.before($newrow);
        } else {
            this.$current.append($newrow);
        }
    },
});

var One2ManyListView = X2ManyListView.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.options = _.extend(this.options, {
            GroupsType: One2ManyGroups,
            ListType: X2ManyList
        });
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));

        /* detect if the user try to exit the one2many widget */
        core.bus.on('click', this, this._on_click_outside);

        this.dataset.on('dataset_changed', this, function () {
            this._dataset_changed = true;
            this.dataset.x2m._dirty_flag = true;
        });
        this.dataset.x2m.on('load_record', this, function () {
            this._dataset_changed = false;
        });

        this.on('warning', this, function(e) { // In case of editable list view, we do not want any warning which comes from the editor
            if (this.editable()) {
                e.stop_propagation();
            }
        });
    },
    do_add_record: function () {
        if (this.editable()) {
            this._super.apply(this, arguments);
        } else {
            var self = this;
            new common.SelectCreateDialog(this, {
                res_model: self.x2m.field.relation,
                domain: self.x2m.build_domain(),
                context: self.x2m.build_context(),
                title: _t("Create: ") + self.x2m.string,
                initial_view: "form",
                alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
                create_function: function(data, options) {
                    return self.x2m.data_create(data, options);
                },
                read_function: function(ids, fields, options) {
                    return self.x2m.data_read(ids, fields, options);
                },
                parent_view: self.x2m.view,
                child_name: self.x2m.name,
                form_view_options: {'not_interactible_on_create':true},
                on_selected: function() {
                    self.x2m.reload_current_view();
                }
            }).open();
        }
    },
    do_activate_record: function(index, id) {
        var self = this;
        new common.FormViewDialog(self, {
            res_model: self.x2m.field.relation,
            res_id: id,
            context: self.x2m.build_context(),
            title: _t("Open: ") + self.x2m.string,
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: !this.is_action_enabled('edit') || self.x2m.get("effective_readonly")
        }).open();
    },
    do_button_action: function (name, id, callback) {
        if (!_.isNumber(id)) {
            this.do_warn(_t("Action Button"),
                         _t("The o2m record must be saved before an action can be used"));
            return;
        }
        var parent_form = this.x2m.view;
        var self = this;
        this.save_edition().then(function () {
            if (parent_form) {
                return parent_form.save();
            } else {
                return $.when();
            }
        }).done(function () {
            var ds = self.x2m.dataset;
            var changed_records = _.find(ds.cache, function(record) {
                return record.to_create || record.to_delete || !_.isEmpty(record.changes);
            });
            if (!self.x2m.options.reload_on_button && !changed_records) {
                self.handle_button(name, id, callback);
            } else {
                self.handle_button(name, id, function(){
                    self.x2m.view.reload();
                });
            }
        });
    },
    start_edition: function (record, options) {
        if (!this.__focus) {
            this._on_focus_one2many();
        }
        return this._super(record, options);
    },
    reload_content: function () {
        var self = this;
        if (self.__focus) {
            self._on_blur_one2many();
            return this._super().then(function () {
                var record_being_edited = self.records.get(self.editor.form.datarecord.id);
                if (record_being_edited) {
                    self.start_edition(record_being_edited);
                }
            });
        }
        return this._super();
    },
    _on_focus_one2many: function () {
        if(!this.editor.is_editing()) {
            return;
        }
        this.dataset.x2m.internal_dataset_changed = true;
        this._dataset_changed = false;
        this.__focus = true;
    },
    _on_click_outside: function(e) {
        if(this.__ignore_blur || !this.editor.is_editing()) {
            return;
        }

        var $target = $(e.target);

        // If click on a button, a ui-autocomplete dropdown or modal-backdrop, it is not considered as a click outside
        var click_outside = ($target.closest('.ui-autocomplete,.btn,.modal-backdrop').length === 0);

        // Check if click inside the current list editable
        var $o2m = $target.closest(".o_list_editable");
        if($o2m.length && $o2m[0] === this.el) {
            click_outside = false;
        }

        // Check if click inside a modal which is on top of the current list editable
        var $modal = $target.closest(".modal");
        if($modal.length) {
            var $currentModal = this.$el.closest(".modal");
            if($currentModal.length === 0 || $currentModal[0] !== $modal[0]) {
                click_outside = false;
            }
        }

        if (click_outside) {
            this._on_blur_one2many();
        }
    },
    _on_blur_one2many: function() {
        if(this.__ignore_blur) {
            return $.when();
        }

        this.__ignore_blur = true;
        this.__focus = false;
        this.dataset.x2m.internal_dataset_changed = false;

        var self = this;
        return this.save_edition(true).done(function () {
            if (self._dataset_changed) {
                self.dataset.trigger('dataset_changed');
            }
        }).always(function() {
            self.__ignore_blur = false;
        });
    },
    _after_edit: function () {
        this.editor.form.on('blurred', this, this._on_blur_one2many);

        // The form's blur thing may be jiggered during the edition setup,
        // potentially leading to the x2m instasaving the row. Cancel any
        // blurring triggered the edition startup here
        this.editor.form.widgetFocused();
    },
    _before_unedit: function () {
        this.editor.form.off('blurred', this, this._on_blur_one2many);
    },
    do_delete: function (ids) {
        var confirm = window.confirm;
        window.confirm = function () { return true; };
        try {
            return this._super(ids);
        } finally {
            window.confirm = confirm;
        }
    },
    reload_record: function (record, options) {
        if (!options || !options.do_not_evict) {
            // Evict record.id from cache to ensure it will be reloaded correctly
            this.dataset.evict_record(record.get('id'));
        }

        return this._super(record);
    },
});

var One2ManyGroups = ListView.Groups.extend({
    setup_resequence_rows: function () {
        if (!this.view.x2m.get('effective_readonly')) {
            this._super.apply(this, arguments);
        }
    }
});

var FieldOne2Many = FieldX2Many.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = {
            kanban: core.view_registry.get('one2many_kanban'),
            list: One2ManyListView,
        };
    },
    start: function() {
        this.$el.addClass('o_form_field_one2many');
        return this._super.apply(this, arguments);
    },
    commit_value: function() {
        var self = this;
        return this.is_loaded.then(function() {
            var view = self.viewmanager.active_view;
            if(view.type === "list" && view.controller.editable()) {
                return self.mutex.def.then(function () {
                    return view.controller.save_edition();
                });
            }
            return self.mutex.def;
        });
    },
    is_false: function() {
        return false;
    },
});

var Many2ManyListView = X2ManyListView.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.options = _.extend(this.options, {
            ListType: X2ManyList,
        });
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));
    },
    do_add_record: function () {
        var self = this;

        new common.SelectCreateDialog(this, {
            res_model: this.model,
            domain: new data.CompoundDomain(this.x2m.build_domain(), ["!", ["id", "in", this.x2m.dataset.ids]]),
            context: this.x2m.build_context(),
            title: _t("Add: ") + this.x2m.string,
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            no_create: this.x2m.options.no_create || !this.is_action_enabled('create'),
            on_selected: function(element_ids) {
                return self.x2m.data_link_multi(element_ids).then(function() {
                    self.x2m.reload_current_view();
                });
            }
        }).open();
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new common.FormViewDialog(this, {
            res_model: this.model,
            res_id: id,
            context: this.x2m.build_context(),
            title: _t("Open: ") + this.x2m.string,
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            readonly: !this.is_action_enabled('edit') || self.x2m.get("effective_readonly"),
        }).open();
        pop.on('write_completed', self, function () {
            self.dataset.evict_record(id);
            self.reload_content();
        });
    },
    do_button_action: function(name, id, callback) {
        var self = this;
        var _sup = _.bind(this._super, this);
        if (! this.x2m.options.reload_on_button) {
            return _sup(name, id, callback);
        } else {
            return this.x2m.view.save().then(function() {
                return _sup(name, id, function() {
                    self.x2m.view.reload();
                });
            });
        }
    },
    _after_edit: function () {
        this.editor.form.on('blurred', this, this._on_blur_many2many);
    },
    _before_unedit: function () {
        this.editor.form.off('blurred', this, this._on_blur_many2many);
    },
    _on_blur_many2many: function() {
        return this.save_edition().done(function () {
            if (self._dataset_changed) {
                self.dataset.trigger('dataset_changed');
            }
        });
    },

});

var FieldMany2Many = FieldX2Many.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = {
            list: Many2ManyListView,
            kanban: core.view_registry.get('many2many_kanban'),
        };
    },
    start: function() {
        this.$el.addClass('o_form_field_many2many');
        return this._super.apply(this, arguments);
    }
});

var FieldMany2ManyKanban = FieldMany2Many.extend({
    default_view: 'kanban',
    init: function() {
        this._super.apply(this, arguments);
        this.view_options = _.extend({}, this.view_options, {
            'create_text': _t("Add"),
        });
    }
});

var FieldMany2ManyTags = AbstractManyField.extend(common.CompletionFieldMixin, common.ReinitializeFieldMixin, {
    className: "o_form_field_many2manytags",
    tag_template: "FieldMany2ManyTag",

    events: {
        'click .o_delete': function(e) {
            this.remove_id($(e.target).parent().data('id'));
        },
        'click .badge': 'open_color_picker',
        'mousedown .o_colorpicker span': 'update_color',
        'focusout .o_colorpicker': 'close_color_picker',
    },

    init: function(field_manager, node) {
        this._super(field_manager, node);
        common.CompletionFieldMixin.init.call(this);
        this.set({"value": []});
    },
    willStart: function () {
        var self = this;
        return this.dataset.call('fields_get', []).then(function(fields) {
           self.fields = fields;
        });
    },
    commit_value: function() {
        this.dataset.cancel_read();
        return this._super();
    },
    initialize_content: function() {
        if(!this.get("effective_readonly")) {
            this.many2one = new FieldMany2One(this.field_manager, this.node);
            this.many2one.options.no_open = true;
            this.many2one.on('changed_value', this, function() {
                var newValue = this.many2one.get('value');
                if(newValue) {
                    this.add_id(newValue);
                    this.many2one.set({'value': false});
                }
            });

            this.many2one.prependTo(this.$el);

            var self = this;
            this.many2one.$('input').on('keydown', function(e) {
                if(!$(e.target).val() && e.which === 8) {
                    var $badges = self.$('.badge');
                    if($badges.length) {
                        self.remove_id($badges.last().data('id'));
                    }
                }
            });
            this.many2one.get_search_blacklist = function () {
                return self.get('value');
            };
        }
    },
    destroy_content: function() {
        if(this.many2one) {
            this.many2one.destroy();
            this.many2one = undefined;
        }
    },
    get_render_data: function(ids){
        this.dataset.cancel_read();
        var fields = this.fields.color ? ['display_name', 'name', 'color'] : ['display_name', 'name']; // TODO master: remove useless 'name'
        return this.dataset.read_ids(ids, fields);
    },
    render_tag: function(data) {
        this.$('.badge').remove();
        this.$el.prepend(QWeb.render(this.tag_template, {elements: data, readonly: this.get('effective_readonly')}));
    },
    render_value: function() {
        var self = this;
        var values = this.get("value");
        var handle_names = function(_data) {
            _.each(_data, function(el) {
                el.display_name = el.display_name.trim() ? _.str.escapeHTML(el.display_name) : data.noDisplayContent;
            });
            self.render_tag(_data);
        };
        if (!values || values.length > 0) {
            return this.alive(this.get_render_data(values)).done(handle_names);
        } else {
            handle_names([]);
        }
    },
    add_id: function(id) {
        this.set({'value': _.uniq(this.get('value').concat([id]))});
    },
    remove_id: function(id) {
        this.set({'value': _.without(this.get("value"), id)});
    },
    focus: function () {
        if(!this.get("effective_readonly")) {
            return this.many2one.focus();
        }
        return false;
    },
    set_dimensions: function(height, width) {
        if(this.many2one) {
            this.many2one.$el.css('height', 'auto');
        }
        this.$el.css({
            width: width,
            minHeight: height,
        });
        if(this.many2one) {
            this.many2one.$el.css('height', this.$el.height());
        }
    },
    open_color_picker: function(ev){

        if (this.fields.color) {
            this.$color_picker = $(QWeb.render('FieldMany2ManyTag.colorpicker', {
                'widget': this,
                'tag_id': $(ev.currentTarget).data('id'),
            }));

            $(ev.currentTarget).append(this.$color_picker);
            this.$color_picker.dropdown('toggle');
            this.$color_picker.attr("tabindex", 1).focus();
        }
    },
    close_color_picker: function(){
        this.$color_picker.remove();
    },
    update_color: function(ev) {
        ev.preventDefault();

        var color = $(ev.currentTarget).data('color');
        var id = $(ev.currentTarget).data('id');

        var self = this;
        this.dataset.call('write', [id, {'color': color}]).done(function(){
            self.dataset.cache[id].from_read = {};
            self.dataset.evict_record(id);
            var tag = self.$el.find("span.badge[data-id='" + id + "']");
            var old_color = tag.data('color');
            tag.removeClass('o_tag_color_' + old_color);
            tag.data('color', color);
            tag.addClass('o_tag_color_' + color);
        });
    },
});

/**
 * Widget for (many2many field) to upload one or more file in same time and display in list.
 * The user can delete his files.
 * Options on attribute ; "blockui" {Boolean} block the UI or not during the file is uploading
 */
var FieldMany2ManyBinaryMultiFiles = AbstractManyField.extend(common.ReinitializeFieldMixin, {
    template: "FieldBinaryFileUploader",
    events: {
        'click .o_attach': function(e) {
            this.$('.o_form_input_file').click();
        },
        'change .o_form_input_file': function(event) {
            event.stopPropagation();
            var files = event.target.files,
                attachments = this.get('value');

            if(this.node.attrs.blockui){
                framework.blockUI();
            }
            _.each(files, function(file){
                var attachment = _.findWhere(_.values(this.data), {filename: file.name});
                if(attachment && !attachment.no_unlink){
                    this.ds_file.unlink([attachment.id]);
                    attachments = _.without(attachments, attachment.id);
                    this.data = _.omit(this.data, attachment.id);
                }
                this.files_uploading.push(file);
            }.bind(this));
            this.set({value: attachments});
            this.$('form.o_form_binary_form').submit();
            this.$(".oe_fileupload").hide();
            this.render_value();
        },
        'click .oe_delete': function(e) {
            e.preventDefault();
            e.stopPropagation();

            var file_id = $(e.currentTarget).data("id");
            if(file_id) {
                var files = _.without(this.get('value'), file_id);
                if(!this.data[file_id].no_unlink) {
                    this.ds_file.unlink([file_id]);
                    this.data = _.omit(this.data, file_id);
                }
                this.set({'value': files});
            }
        },
    },
    init: function(field_manager, node) {
        this._super.apply(this, arguments);
        this.session = session;
        if(this.field.type != "many2many" || this.field.relation != 'ir.attachment') {
            throw _.str.sprintf(_t("The type of the field '%s' must be a many2many field with a relation to 'ir.attachment' model."), this.field.string);
        }
        this.data = {};
        this.files_uploading = [];
        this.set_value([]);
        this.ds_file = new data.DataSetSearch(this, 'ir.attachment');
        this.fileupload_id = _.uniqueId('oe_fileupload_temp');
        $(window).on(this.fileupload_id, _.bind(this.on_file_loaded, this));
    },
    get_file_url: function(attachment) {
        return '/web/content/' + attachment.id + '?download=true';
    },
    read_name_values : function() {
        var self = this;
        // don't reset know values
        var ids = this.get('value');
        var _value = _.filter(ids, function(id) { return self.data[id] === undefined; });
        // send request for get_name
        if(_value.length) {
            return this.ds_file.call('read', [_value, ['id', 'name', 'datas_fname', 'mimetype']])
                               .then(process_data);
        } else {
            return $.when(ids);
        }

        function process_data(datas) {
            _.each(datas, function(data) {
                data.no_unlink = true;
                data.url = self.get_file_url(data);
                self.data[data.id] = data;
            });
            return ids;
        }
    },
    render_value: function() {
        var self = this;
        this.read_name_values().then(function (ids) {
            self.$('.oe_placeholder_files, .oe_attachments')
                .replaceWith($(QWeb.render('FieldBinaryFileUploader.files', {'widget': self, 'values': ids})));
            self.$(".oe_fileupload").show();

            // display image thumbnail
            self.$(".o_image[data-mimetype^='image']").each(function () {
                var $img = $(this);
                if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
                    $img.css('background-image', "url('" + $img.data('src') + "')");
                }
            });
        });
    },
    on_file_loaded: function(e, result) {
        var attachments = this.get('value'),
            files = Array.prototype.slice.call(arguments, 1);
            this.files_uploading = []; // files has been uploaded clear uploading

        if(this.node.attrs.blockui) { // unblock UI
            framework.unblockUI();
        }
        var upload_error = _.filter(files, function(attachment) {return attachment.error;});
        if (upload_error.length) {
            this.do_warn(_t('Uploading Error'), upload_error[0].error);
        }
        _.each(files, function(file){
            if(!file.error){
                attachments.push(file.id);
                file.url = this.get_file_url(file);
                this.data[file.id] = file;
            }
        }.bind(this));
        this.set({value: _.clone(attachments)});
        this.render_value();
    },
});

/*
    This type of field display a list of checkboxes. It works only with m2ms. This field will display one checkbox for each
    record existing in the model targeted by the relation, according to the given domain if one is specified. Checked records
    will be added to the relation.
*/
var FieldMany2ManyCheckBoxes = AbstractManyField.extend(common.ReinitializeFieldMixin, {
    className: "oe_form_many2many_checkboxes",
    init: function() {
        this._super.apply(this, arguments);
        this.set("records", []);
        this.field_manager.on("view_content_has_changed", this, function() {
            var domain = new data.CompoundDomain(this.build_domain()).eval();
            if (!_.isEqual(domain, this.get("domain"))) {
                this.set("domain", domain);
            }
        });
        this.records_orderer = new utils.DropMisordered();
    },
    initialize_field: function() {
        common.ReinitializeFieldMixin.initialize_field.call(this);
        this.on("change:domain", this, this.query_records);
        this.set("domain", new data.CompoundDomain(this.build_domain()).eval());
        this.on("change:records", this, this.render_value);
    },
    query_records: function() {
        var self = this;
        var model = new Model(this.field.relation);
        this.records_orderer.add(model.call("search", [this.get("domain")], {"context": this.build_context()}).then(function(record_ids) {
            return model.call("name_get", [record_ids] , {"context": self.build_context()});
        })).then(function(res) {
            self.set("records", res);
        });
    },
    render_value: function() {
        this.$el.html(QWeb.render("FieldMany2ManyCheckBoxes", {widget: this}));
        var $inputs = this.$("input");
        $inputs.change(_.bind(this.from_dom, this));
        if (this.get("effective_readonly")) {
            $inputs.attr("disabled", "true");
        }
    },
    from_dom: function() {
        var new_value = this.$("input:checked").map(function() { return +$(this).data("record-id"); }).get();
        if (!_.isEqual(new_value, this.get("value"))) {
            this.internal_set_value(new_value);
        }
    },
    is_false: function() {
        return false;
    },
});

core.form_widget_registry
    .add('many2one', FieldMany2One)
    .add('many2many', FieldMany2Many)
    .add('many2many_tags', FieldMany2ManyTags)
    .add('many2many_kanban', FieldMany2ManyKanban)
    .add('one2many', FieldOne2Many)
    .add('one2many_list', FieldOne2Many)
    .add('many2many_binary', FieldMany2ManyBinaryMultiFiles)
    .add('many2many_checkboxes', FieldMany2ManyCheckBoxes);

core.one2many_view_registry
    .add('list', One2ManyListView);

return {
    FieldMany2ManyTags: FieldMany2ManyTags,
    AbstractManyField: AbstractManyField,
    FieldMany2One: FieldMany2One,
};

});
