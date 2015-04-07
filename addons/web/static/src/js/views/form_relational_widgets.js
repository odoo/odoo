odoo.define('web.form_relational', function (require) {
"use strict";

var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var common = require('web.form_common');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var Model = require('web.Model');
var session = require('web.session');
var utils = require('web.utils');
var ViewManager = require('web.ViewManager');


var _t = core._t;
var QWeb = core.qweb;
var commands = common.commands;
var list_widget_registry = core.list_widget_registry;

var M2ODialog = Dialog.extend({
    template: "M2ODialog",
    init: function(parent) {
        this.name = parent.string;
        this._super(parent, {
            title: _.str.sprintf(_t("Create a %s"), parent.string),
            size: 'medium',
        });
    },
    start: function() {
        var self = this;
        var text = _.str.sprintf(_t("You are creating a new %s, are you sure it does not exist yet?"), self.name);
        this.$("p").text( text );
        this.$buttons.html(QWeb.render("M2ODialog.buttons"));
        this.$("input").val(this.getParent().$input.val());
        this.$buttons.find(".oe_form_m2o_qc_button").click(function(e){
            if (self.$("input").val() !== ''){
                self.getParent()._quick_create(self.$("input").val());
                self.destroy();
            } else{
                e.preventDefault();
                self.$("input").focus();
            }
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
        this.set({'value': false});
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
        if (!this.get("effective_readonly"))
            this.render_editable();
    },
    destroy_content: function () {
        if (this.$drop_down) {
            this.$drop_down.off('click');
            delete this.$drop_down;
        }
        if (this.$input) {
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
            var pop = new common.FormOpenPopup(self);
            var context = self.build_context().eval();
            var model_obj = new Model(self.field.relation);
            model_obj.call('get_formview_id', [self.get("value"), context]).then(function(view_id){
                pop.show_element(
                    self.field.relation,
                    self.get("value"),
                    self.build_context(),
                    {
                        title: _t("Open: ") + self.string,
                        view_id: view_id,
                        readonly: !self.can_write
                    }
                );
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
        this.$drop_down.click(function() {
            self.$input.focus();
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
            if (used && self.get("value") === false && ! self.no_ed && ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                self.ed_def.reject();
                self.uned_def.reject();
                self.ed_def = $.Deferred();
                self.ed_def.done(function() {
                    self.can_create && self.show_error_displayer();
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
                    return child instanceof common.AbstractFormPopup;
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
            delay: 200,
        });
        var appendTo = this.$input.parents('.oe-view-manager-content:visible, .modal-dialog:visible').last();
        if (appendTo.length === 0) {
            appendTo = '.oe_application > *:visible:last';
        }
        this.$input.autocomplete({
            appendTo: appendTo
        });
        // set position for list of suggestions box
        this.$input.autocomplete( "option", "position", { my : "left top", at: "left bottom" } );
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
            var dataset = new data.DataSetStatic(this, this.field.relation, self.build_context());
            var def = this.alive(dataset.name_get([self.get("value")])).done(function(data) {
                if (!data[0]) {
                    self.do_warn(_t("Render"), _t("No value found for the field "+self.field.string+" for value "+self.get("value")));
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
                    var context = self.build_context().eval();
                    var model_obj = new Model(self.field.relation);
                    model_obj.call('get_formview_action', [self.get("value"), context]).then(function(action){
                        self.do_action(action);
                    });
                    return false;
                 });
            $(".oe_form_m2o_follow", this.$el).html(follow);
        }
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
    set_dimensions: function (height, width) {
        this._super(height, width);
        if (!this.get("effective_readonly") && this.$input)
            this.$input.css('height', height);
    }
});

var Many2OneButton = common.AbstractField.extend({
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
        this.popup =  new common.FormOpenPopup(this);
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
        if (value_ instanceof Array) {
            value_ = value_[0];
        }
        value_ = value_ || false;
        this.set('value', value_);
        this.set_button();
     },
});

/**
 * Abstract-ish ListView.List subclass adding an "Add an item" row to replace
 * the big ugly button in the header.
 *
 * Requires the implementation of a ``is_readonly`` method (usually a proxy to
 * the corresponding field's readonly or effective_readonly property) to
 * decide whether the special row should or should not be inserted.
 *
 * Optionally an ``_add_row_class`` attribute can be set for the class(es) to
 * set on the insertion row.
 */
var AddAnItemList = ListView.List.extend({
    pad_table_to: function (count) {
        if (!this.view.is_action_enabled('create') || this.is_readonly()) {
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
            'class': this._add_row_class || ''
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
            this.$current.append($newrow);
        }
    }
});

/**
 * A Abstract field for one2many and many2many field
 * init: add dataset
 * set_value: compute comands list into ids
 */
var AbstractManyField = common.AbstractField.extend({
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.dataset = new One2ManyDataSet(this, this.field.relation);
        this.dataset.o2m = this;
        this.dataset.parent_view = this.view;
        this.dataset.child_name = this.name;
        this.dataset.on('dataset_changed', this, function() {
            self.dataset_changed();
        });
    },
    dataset_changed: function() {
        this.trigger('changed_value');
    },
    /**
     * Set value use command to convert tuple of commands in id list
     */
    set_value: function(value_) {
        this.dataset.reset_ids([]);
        var ids = this.get_ids_from_command(value_);
        this._super(ids);
        this.dataset.reset_ids(ids);
        if (this.dataset.index === null && this.dataset.ids.length > 0) {
            this.dataset.index = 0;
        }
        this.dataset_changed();
    },

    // return id for this commands instead of the object ('ALL' to activate all conversion)
    get_ids_from_command_list: ['LINK_TO', 'REPLACE_WITH'],
    get_ids_from_command: function (value_) {
        var self = this;
        var ids;
        var command_list = [];
        if (this.get_ids_from_command_list && this.get_ids_from_command_list !== 'ALL') {
            for (var i=0; i<this.get_ids_from_command_list.length; i++) {
                command_list[i] = commands[this.get_ids_from_command_list[i]];
            }
        }

        value_ = value_ || [];
        if(value_.length >= 1 && value_[0] instanceof Array) {
            ids = [];
            _.each(value_, function(command) {
                var obj = {values: command[2]};
                if (command_list.length && command.indexOf(command_list) === -1) {
                    ids.push(obj);
                }
                switch (command[0]) {
                    case commands.CREATE:
                        obj.id = _.uniqueId(self.dataset.virtual_id_prefix);
                        obj.defaults = {};
                        self.dataset.to_create.push(obj);
                        self.dataset.cache.push(_.extend(_.clone(obj), {values: _.clone(command[2])}));
                        ids.push(obj.id);
                        return;
                    case commands.UPDATE:
                        obj.id = command[1];
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
                    case commands.REPLACE_WITH:
                        ids = command[2];
                        return;
                }
            });
            return ids;
        } else if (value_.length >= 1 && typeof(value_[0]) === "object") {
            ids = [];
            this.dataset.delete_all = true;
            _.each(value_, function(command) {
                var obj = {values: command};
                obj.id = _.uniqueId(self.dataset.virtual_id_prefix);
                obj.defaults = {};
                self.dataset.to_create.push(obj);
                self.dataset.cache.push(_.clone(obj));
                ids.push(obj.id);
            });
            return ids;
        } else {
            return value_;
        }
    }
});


var FieldOne2Many = AbstractManyField.extend({
    multi_selection: false,
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        
        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;
        this.form_last_update = $.Deferred();
        this.init_form_last_update = this.form_last_update;
        this.is_started = false;
        this.set_value([]);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('oe_form_field oe_form_field_one2many');

        var self = this;

        self.load_views();
        var destroy = function() {
            self.is_loaded = self.is_loaded.then(function() {
                self.viewmanager.destroy();
                return $.when(self.load_views()).done(function() {
                    self.reload_current_view();
                });
            });
        };
        this.is_loaded.done(function() {
            self.on("change:effective_readonly", self, destroy);
        });
        this.view.on("on_button_cancel", self, destroy);
        this.is_started = true;
        this.reload_current_view();
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

        this.viewmanager = new One2ManyViewManager(this, this.dataset, views, {});
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
                        if (!(column instanceof list_widget_registry.get('field.handle'))) {
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
                self.reload_current_view();
            }
            def.resolve();
        });
        this.viewmanager.on("switch_mode", self, function(n_mode) {
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
        self.is_loaded = self.is_loaded.then(function() {
            var view = self.get_active_view();
            if (view.type === "list") {
                return view.controller.reload_content();
            } else if (view.type === "form") {
                if (self.dataset.index === null && self.dataset.ids.length >= 1) {
                    self.dataset.index = 0;
                }
                var act = function() {
                    return view.controller.do_show();
                };
                self.form_last_update = self.form_last_update.then(act, act);
                return self.form_last_update;
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
    get_ids_from_command_list: 'ALL',
    set_value: function(value_) {
        this._super(value_);
        if (this.is_started && !this.no_rerender) {
            return this.reload_current_view();
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
        var view = this.get_active_view();
        if (view) {
            if (this.viewmanager.active_view.type === "form") {
                if (view.controller.is_initialized.state() !== 'resolved') {
                    return $.when(false);
                }
                return $.when(view.controller.save());
            } else if (this.viewmanager.active_view.type === "list") {
                return $.when(view.controller.ensure_saved());
            }
        }
        return $.when(false);
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
});

var One2ManyDataSet = data.BufferedDataSet.extend({
    get_context: function() {
        this.context = this.o2m.build_context();
        return this.context;
    }
});

var One2ManyListView = ListView.extend({
    _template: 'One2Many.listview',
    init: function (parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, _.extend(options || {}, {
            GroupsType: One2ManyGroups,
            ListType: One2ManyList
        }));
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));

        this.records
            .bind('add', this.proxy("changed_records"))
            .bind('remove', this.proxy("changed_records"));
        this.on('save:after', this, this.proxy("changed_records"));
    },
    start: function () {
        var ret = this._super();
        this.$el
            .off('mousedown.handleButtons')
            .on('mousedown.handleButtons', 'table button, div a.oe_m2o_cm_button', this.proxy('_button_down'));
        return ret;
    },
    changed_records: function () {
        this.o2m.dataset_changed();
    },
    is_valid: function () {
        var self = this;
        if (!this.fields_view || !this.editable()){
            return true;
        }
        if (_.isEmpty(this.records.records)){
            return true;
        }
        var current_values = {};
        _.each(this.editor.form.fields, function(field){
            field._inhibit_on_change_flag = true;
            field.no_rerender = true;
            current_values[field.name] = field.get('value');
        });
        var valid = _.every(this.records.records, function(record){
            _.each(self.editor.form.fields, function(field){
                field.set_value(record.attributes[field.name]);
            });
            return _.every(self.editor.form.fields, function(field){
                field.process_modifiers();
                field._check_css_flags();
                return field.is_valid();
            });
        });
        _.each(this.editor.form.fields, function(field){
            field.set('value', current_values[field.name]);
            field._inhibit_on_change_flag = false;
            field.no_rerender = false;
        });
        return valid;
    },
    do_add_record: function () {
        if (this.editable()) {
            this._super.apply(this, arguments);
        } else {
            var self = this;
            var pop = new common.SelectCreatePopup(this);
            pop.select_element(
                self.o2m.field.relation,
                {
                    title: _t("Create: ") + self.o2m.string,
                    initial_view: "form",
                    alternative_form_view: self.o2m.field.views ? self.o2m.field.views.form : undefined,
                    create_function: function(data, options) {
                        return self.o2m.dataset.create(data, options).done(function(r) {
                            self.o2m.dataset.set_ids(self.o2m.dataset.ids.concat([r]));
                            self.o2m.dataset.trigger("dataset_changed", r);
                        });
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
        var pop = new common.FormOpenPopup(self);
        pop.show_element(self.o2m.field.relation, id, self.o2m.build_context(), {
            title: _t("Open: ") + self.o2m.string,
            write_function: function(id, data) {
                return self.o2m.dataset.write(id, data, {}).done(function() {
                    self.o2m.reload_current_view();
                });
            },
            alternative_form_view: self.o2m.field.views ? self.o2m.field.views.form : undefined,
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
            core.bus.trigger('display_notification_warning', 
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
            var ds = self.o2m.dataset;
            var cached_records = _.any([ds.to_create, ds.to_delete, ds.to_write], function(value) {
                return value.length;
            });
            if (!self.o2m.options.reload_on_button && !cached_records) {
                self.handle_button(name, id, callback);
            }else {
                self.handle_button(name, id, function(){
                    self.o2m.view.reload();
                });
            }
        });
    },

    _after_edit: function () {
        this.__ignore_blur = false;
        this.editor.form.on('blurred', this, this._on_form_blur);

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
    keypress_ENTER: function () {
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
    },
    reload_record: function (record, options) {
        if (!options || !options.do_not_evict) {
            // Evict record.id from cache to ensure it will be reloaded correctly
            this.dataset.evict_record(record.get('id'));
        }

        return this._super(record);
    }
});

var One2ManyGroups = ListView.Groups.extend({
    setup_resequence_rows: function () {
        if (!this.view.o2m.get('effective_readonly')) {
            this._super.apply(this, arguments);
        }
    }
});

var One2ManyList = AddAnItemList.extend({
    _add_row_class: 'oe_form_field_one2many_list_row_add',
    is_readonly: function () {
        return this.view.o2m.get('effective_readonly');
    },
});

var One2ManyFormView = FormView.extend({
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

var One2ManyViewManager = ViewManager.extend({
    init: function(parent, dataset, views, flags) {
        // By default, render buttons and pager in O2M fields, but no sidebar
        var flags = _.extend({}, flags, {
            headless: false,
            search_view: false,
            action_buttons: true,
            pager: true,
            sidebar: false,
        });
        this.control_panel = new ControlPanel(parent, "One2ManyControlPanel");
        this.set_cp_bus(this.control_panel.get_bus());
        this._super(parent, dataset, views, flags);
        this.registry = core.view_registry.extend({
            list: One2ManyListView,
            form: One2ManyFormView,
        });
        this.__ignore_blur = false;
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
        var id = self.o2m.dataset.index !== null ? self.o2m.dataset.ids[self.o2m.dataset.index] : null;
        var pop = new common.FormOpenPopup(this);
        pop.show_element(self.o2m.field.relation, id, self.o2m.build_context(), {
            title: _t("Open: ") + self.o2m.string,
            create_function: function(data, options) {
                return self.o2m.dataset.create(data, options).done(function(r) {
                    self.o2m.dataset.set_ids(self.o2m.dataset.ids.concat([r]));
                    self.o2m.dataset.trigger("dataset_changed", r);
                });
            },
            write_function: function(id, data, options) {
                return self.o2m.dataset.write(id, data, {}).done(function() {
                    self.o2m.reload_current_view();
                });
            },
            alternative_form_view: self.o2m.field.views ? self.o2m.field.views.form : undefined,
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

var FieldMany2ManyTags = AbstractManyField.extend(common.CompletionFieldMixin, common.ReinitializeFieldMixin, {
    template: "FieldMany2ManyTags",
    tag_template: "FieldMany2ManyTag",
    init: function() {
        this._super.apply(this, arguments);
        common.CompletionFieldMixin.init.call(this);
        this.set({"value": []});
        this._display_orderer = new utils.DropMisordered();
        this._drop_shown = false;
    },
    initialize_texttext: function(){
        var self = this;
        return {
            plugins : 'tags arrow autocomplete',
            autocomplete: {
                render: function(suggestion) {
                    return $('<span class="text-label"/>').
                             data('index', suggestion.index).html(suggestion.label);
                }
            },
            ext: {
                autocomplete: {
                    selectFromDropdown: function() {
                        this.trigger('hideDropdown');
                        var index = Number(this.selectedSuggestionElement().children().children().data('index'));
                        var data = self.search_result[index];
                        if (data.id) {
                            self.add_id(data.id);
                        } else {
                            self.ignore_blur = true;
                            data.action();
                        }
                        this.trigger('setSuggestions', {result : []});
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
                        if (data === '') {
                            this._plugins.autocomplete._suggestions = null;
                        }
                        this.input().val(data);
                    },
                },
            },
        };
    },
    initialize_content: function() {
        if (this.get("effective_readonly"))
            return;
        var self = this;
        self.ignore_blur = false;
        self.$text = this.$("textarea");
        self.$text.textext(self.initialize_texttext()).bind('getSuggestions', function(e, data) {
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
                self.ignore_blur = false;
            })
            .focusout(function() {
                self.$text.trigger("setInputData", "");
                if (!self.ignore_blur) {
                    self.trigger('blurred');
                }
            }).keydown(function(e) {
                if (e.which === $.ui.keyCode.TAB && self._drop_shown) {
                    self.$text.textext()[0].autocomplete().selectFromDropdown();
                }
            });
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
    map_tag: function(data){
        return _.map(data, function(el) {return {name: el[1], id:el[0]};});
    },
    get_render_data: function(ids){
        var self = this;
        var dataset = new data.DataSetStatic(this, this.field.relation, self.build_context());
        return dataset.name_get(ids);
    },
    render_tag: function(data) {
        var self = this;
        if (! self.get("effective_readonly")) {
            self.tags.containerElement().children().remove();
            self.$('textarea').css("padding-left", "3px");
            self.tags.addTags(self.map_tag(data));
        } else {
            self.$el.html(QWeb.render(self.tag_template, {elements: data}));
        }
    },
    render_value: function() {
        var self = this;
        var dataset = new data.DataSetStatic(this, this.field.relation, self.build_context());
        var values = self.get("value");
        var handle_names = function(data) {
            if (self.isDestroyed())
                return;
            var indexed = {};
            _.each(data, function(el) {
                indexed[el[0]] = el;
            });
            data = _.map(values, function(el) { return indexed[el]; });
            self.render_tag(data);
        };
        if (! values || values.length > 0) {
            return this._display_orderer.add(self.get_render_data(values)).done(handle_names);
        } else {
            handle_names([]);
        }
    },
    add_id: function(id) {
        this.set({'value': _.uniq(this.get('value').concat([id]))});
    },
    focus: function () {
        var input = this.$text && this.$text[0];
        return input ? input.focus() : false;
    },
    set_dimensions: function (height, width) {
        this._super(height, width);        
        this.$("textarea").css({
            width: width,
            minHeight: height
        });
    },    
    _search_create_popup: function() {
        this.ignore_blur = true;
        return common.CompletionFieldMixin._search_create_popup.apply(this, arguments);
    },
});

/**
    widget options:
    - reload_on_button: Reload the whole form view if click on a button in a list view.
        If you see this options, do not use it, it's basically a dirty hack to make one
        precise o2m to behave the way we want.
*/
var FieldMany2Many = AbstractManyField.extend(common.ReinitializeFieldMixin, {
    multi_selection: false,
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.is_loaded = $.Deferred();
        this.set_value([]);
        this.list_dm = new utils.DropMisordered();
        this.render_value_dm = new utils.DropMisordered();
    },
    initialize_content: function() {
        var self = this;

        this.$el.addClass('oe_form_field oe_form_field_many2many');

        this.list_view = new Many2ManyListView(this, this.dataset, false, {
                    'addable': null,
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

var Many2ManyDataSet = data.DataSetStatic.extend({
    get_context: function() {
        this.context = this.m2m.build_context();
        return this.context;
    }
});

/**
 * @class
 * @extends instance.web.ListView
 */
var Many2ManyListView = ListView.extend(/** @lends instance.web.form.Many2ManyListView# */{
    init: function (parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, _.extend(options || {}, {
            ListType: Many2ManyList,
        }));
    },
    do_add_record: function () {
        var pop = new common.SelectCreatePopup(this);
        pop.select_element(
            this.model,
            {
                title: _t("Add: ") + this.m2m_field.string,
                alternative_form_view: this.m2m_field.field.views ? this.m2m_field.field.views.form : undefined,
                no_create: this.m2m_field.options.no_create,
            },
            new data.CompoundDomain(this.m2m_field.build_domain(), ["!", ["id", "in", this.m2m_field.dataset.ids]]),
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
        var pop = new common.FormOpenPopup(this);
        pop.show_element(this.dataset.model, id, this.m2m_field.build_context(), {
            title: _t("Open: ") + this.m2m_field.string,
            alternative_form_view: this.m2m_field.field.views ? this.m2m_field.field.views.form : undefined,
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
    is_action_enabled: function () { return true; },
});
var Many2ManyList = AddAnItemList.extend({
    _add_row_class: 'oe_form_field_many2many_list_row_add',
    is_readonly: function () {
        return this.view.m2m_field.get('effective_readonly');
    }
});

var FieldMany2ManyKanban = AbstractManyField.extend(common.CompletionFieldMixin, {
    disable_utility_classes: true,
    init: function(field_manager, node) {
        this._super(field_manager, node);
        common.CompletionFieldMixin.init.call(this);
        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;
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
    get_value: function() {
        return [commands.replace_with(this.get('value'))];
    },
    load_view: function() {
        var self = this;
        var Many2ManyKanbanView = core.view_registry.get('many2many_kanban');
        this.kanban_view = new Many2ManyKanbanView(this, this.dataset, false, {
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
        var pop;
        if (this.dataset.index === null) {
            pop = new common.SelectCreatePopup(this);
            pop.select_element(
                this.field.relation,
                {
                    title: _t("Add: ") + this.string
                },
                new data.CompoundDomain(this.build_domain(), ["!", ["id", "in", this.dataset.ids]]),
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
            pop = new common.FormOpenPopup(this);
            pop.show_element(self.field.relation, id, self.build_context(), {
                title: _t("Open: ") + self.string,
                write_function: function(id, data, options) {
                    return self.dataset.write(id, data, {}).done(function() {
                        self.render_value();
                    });
                },
                alternative_form_view: self.field.views ? self.field.views.form : undefined,
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

/**
 * Widget for (many2many field) to upload one or more file in same time and display in list.
 * The user can delete his files.
 * Options on attribute ; "blockui" {Boolean} block the UI or not
 * during the file is uploading
 */
var FieldMany2ManyBinaryMultiFiles = AbstractManyField.extend(common.ReinitializeFieldMixin, {
    template: "FieldBinaryFileUploader",
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.field_manager = field_manager;
        this.node = node;
        this.session = session;
        if(this.field.type != "many2many" || this.field.relation != 'ir.attachment') {
            throw _.str.sprintf(_t("The type of the field '%s' must be a many2many field with a relation to 'ir.attachment' model."), this.field.string);
        }
        this.data = {};
        this.set_value([]);
        this.ds_file = new data.DataSetSearch(this, 'ir.attachment');
        this.fileupload_id = _.uniqueId('oe_fileupload_temp');
        $(window).on(this.fileupload_id, _.bind(this.on_file_loaded, this));
    },
    initialize_content: function() {
        this.$el.on('change', 'input.oe_form_binary_file', this.on_file_change );
    },
    get_value: function() {
        return [commands.replace_with(this.get("value"))];
    },
    get_file_url: function (attachment) {
        return this.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname', id: attachment.id});
    },
    read_name_values : function () {
        var self = this;
        // don't reset know values
        var ids = this.get('value');
        var _value = _.filter(ids, function (id) { return typeof self.data[id] == 'undefined'; } );
        // send request for get_name
        if (_value.length) {
            return this.ds_file.call('read', [_value, ['id', 'name', 'datas_fname']]).then(function (datas) {
                _.each(datas, function (data) {
                    data.no_unlink = true;
                    data.url = self.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname', id: data.id});
                    self.data[data.id] = data;
                });
                return ids;
            });
        } else {
            return $.when(ids);
        }
    },
    render_value: function () {
        var self = this;
        this.read_name_values().then(function (ids) {
            var render = $(QWeb.render('FieldBinaryFileUploader.files', {'widget': self, 'values': ids}));
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
            // don't uplode more of one file in same time
            if (self.data[0] && self.data[0].upload ) {
                return false;
            }
            for (var id in this.get('value')) {
                // if the files exits, delete the file before upload (if it's a new file)
                if (self.data[id] && (self.data[id].filename || self.data[id].name) == filename && !self.data[id].no_unlink ) {
                    self.ds_file.unlink([id]);
                }
            }

            // block UI or not
            if(this.node.attrs.blockui>0) {
                framework.blockUI();
            }

            // TODO : unactivate send on wizard and form

            // submit file
            this.$('form.oe_form_binary_form').submit();
            this.$(".oe_fileupload").hide();
            // add file on data result
            this.data[0] = {
                'id': 0,
                'name': filename,
                'filename': filename,
                'url': '',
                'upload': true
            };
        }
    },
    on_file_loaded: function (event, result) {
        var files = this.get('value');

        // unblock UI
        if(this.node.attrs.blockui>0) {
            framework.unblockUI();
        }

        if (result.error || !result.id ) {
            this.do_warn( _t('Uploading Error'), result.error);
            delete this.data[0];
        } else {
            if (this.data[0] && this.data[0].filename == result.filename && this.data[0].upload) {
                delete this.data[0];
                this.data[result.id] = {
                    'id': result.id,
                    'name': result.name,
                    'filename': result.filename,
                    'url': this.get_file_url(result)
                };
            } else {
                this.data[result.id] = {
                    'id': result.id,
                    'name': result.name,
                    'filename': result.filename,
                    'url': this.get_file_url(result)
                };
            }
            var values = _.clone(this.get('value'));
            values.push(result.id);
            this.set({'value': values});
        }
        this.render_value();
    },
    on_file_delete: function (event) {
        event.stopPropagation();
        var file_id=$(event.target).data("id");
        if (file_id) {
            var files = _.filter(this.get('value'), function (id) {return id != file_id;});
            if(!this.data[file_id].no_unlink) {
                this.ds_file.unlink([file_id]);
            }
            this.set({'value': files});
        }
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
        this.set("value", {});
        this.set("records", []);
        this.field_manager.on("view_content_has_changed", this, function() {
            var domain = new data.CompoundDomain(this.build_domain()).eval();
            if (! _.isEqual(domain, this.get("domain"))) {
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
        this.$().html(QWeb.render("FieldMany2ManyCheckBoxes", {widget: this, selected: this.get("value")}));
        var inputs = this.$("input");
        inputs.change(_.bind(this.from_dom, this));
        if (this.get("effective_readonly"))
            inputs.attr("disabled", "true");
    },
    from_dom: function() {
        var new_value = {};
        this.$("input").each(function() {
            var elem = $(this);
            new_value[elem.data("record-id")] = elem.is(":checked") ? true : undefined;
        });
        if (! _.isEqual(new_value, this.get("value")))
            this.internal_set_value(new_value);
    },
    set_value: function(value_) {
        var value_ = this.get_ids_from_command(value_);
        var formatted = {};
        _.each(value_, function(el) {
            formatted[JSON.stringify(el)] = true;
        });
        this.set({'value': formatted});
    },
    get_value: function() {
        var value = _.filter(_.keys(this.get("value")), function(el) {
            return this.get("value")[el];
        }, this);
        value = _.map(value, function(el) {
            return JSON.parse(el);
        });
        return [commands.replace_with(value)];
    },
});

/**
    This field can be applied on many2many and one2many. It is a read-only field that will display a single link whose name is
    "<number of linked records> <label of the field>". When the link is clicked, it will redirect to another act_window
    action on the model of the relation and show only the linked records.

    Widget options:

    * views: The views to display in the act_window action. Must be a list of tuples whose first element is the id of the view
      to display (or False to take the default one) and the second element is the type of the view. Defaults to
      [[false, "tree"], [false, "form"]] .
*/
var X2ManyCounter = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    className: "oe_form_x2many_counter",
    init: function() {
        this._super.apply(this, arguments);
        this.set("value", []);
        _.defaults(this.options, {
            "views": [[false, "tree"], [false, "form"]],
        });
    },
    render_value: function() {
        var text = _.str.sprintf("%d %s", this.val().length, this.string);
        this.$().html(QWeb.render("X2ManyCounter", {text: text}));
        this.$("a").click(_.bind(this.go_to, this));
    },
    go_to: function() {
        return this.view.recursive_save().then(_.bind(function() {
            var val = this.val();
            var context = {};
            if (this.field.type === "one2many") {
                context["default_" + this.field.relation_field] = this.view.datarecord.id;
            }
            var domain = [["id", "in", val]];
            return this.do_action({
                type: 'ir.actions.act_window',
                name: this.string,
                res_model: this.field.relation,
                views: this.options.views,
                target: 'current',
                context: context,
                domain: domain,
            });
        }, this));
    },
    val: function() {
        var value = this.get("value") || [];
        if (value.length >= 1 && value[0] instanceof Array) {
            value = value[0][2];
        }
        return value;
    }
});



core.form_widget_registry
    .add('many2one', FieldMany2One)
    .add('many2onebutton', Many2OneButton)
    .add('many2many', FieldMany2Many)
    .add('many2many_tags', FieldMany2ManyTags)
    .add('many2many_kanban', FieldMany2ManyKanban)
    .add('one2many', FieldOne2Many)
    .add('one2many_list', FieldOne2Many)
    .add('many2many_binary', FieldMany2ManyBinaryMultiFiles)
    .add('many2many_checkboxes', FieldMany2ManyCheckBoxes)
    .add('x2many_counter', X2ManyCounter);

return {
    FieldMany2ManyTags: FieldMany2ManyTags,
    AbstractManyField: AbstractManyField,
};

});

odoo.define('web_kanban.Many2ManyKanbanView', function (require) {
    "use strict";
    // This code has a dependency on the addon web_kanban.  This is a weird dependency issue.  To fix it,
    // we should either move this code into web_kanban, or move web_kanban into the web client.

    var core = require('web.core'),
        KanbanView = require('web_kanban.KanbanView'),
        Widget = require('web.Widget');

    var Many2ManyQuickCreate = Widget.extend({
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
                                 data('index', suggestion.index).html(suggestion.label);
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

    var Many2ManyKanbanView = KanbanView.extend({
        get_quick_create_class: function () {
            return Many2ManyQuickCreate;
        },
        _is_quick_create_enabled: function() {
            return this._super() && ! this.group_by;
        },
    });

    core.view_registry.add('many2many_kanban', Many2ManyKanbanView);

});
