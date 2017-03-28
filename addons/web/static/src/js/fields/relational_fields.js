odoo.define('web.relational_fields', function (require) {
"use strict";

/**
 * Relational Fields
 *
 * In this file, we have a collection of various relational field widgets.
 * Relational field widgets are more difficult to use/manipulate, because the
 * relations add a level of complexity: a value is not a basic type, it can be
 * a collection of other records.
 *
 * Also, the way relational fields are edited is more complex.  We can change
 * the corresponding record(s), or alter some of their fields.
 */

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var config = require('web.config');
var ControlPanel = require('web.ControlPanel');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var KanbanRenderer = require('web.KanbanRenderer');
var ListRenderer = require('web.ListRenderer');
var Pager = require('web.Pager');

var _t = core._t;
var qweb = core.qweb;

//------------------------------------------------------------------------------
// Many2one widgets
//------------------------------------------------------------------------------

var M2ODialog = Dialog.extend({
    template: "M2ODialog",
    init: function (parent, name, value) {
        this.name = name;
        this.value = value;
        this._super(parent, {
            title: _.str.sprintf(_t("Create a %s"), this.name),
            size: 'medium',
            buttons: [{
                text: _t('Create'),
                classes: 'btn-primary',
                click: function () {
                    if (this.$("input").val() !== ''){
                        this.trigger_up('quick_create', { value: this.$('input').val() });
                        this.close();
                    } else {
                        this.$("input").focus();
                    }
                },
            }, {
                text: _t('Create and edit'),
                classes: 'btn-primary',
                close: true,
                click: function () {
                    this.trigger_up('search_create_popup', {
                        view_type: 'form',
                        value: this.$('input').val(),
                    });
                },
            }, {
                text: _t('Cancel'),
                close: true,
            }],
        });
    },
    start: function () {
        this.$("p").text(_.str.sprintf(_t("You are creating a new %s, are you sure it does not exist yet?"), this.name));
        this.$("input").val(this.value);
    },
});

var FieldMany2One = AbstractField.extend({
    template: 'FieldMany2One',
    custom_events: {
        'quick_create': '_onQuickCreate',
        'search_create_popup': '_onSearchCreatePopup',
    },
    events: _.extend({}, AbstractField.prototype.events, {
        'click .o_form_input': '_onInputClick',
        'focusout .o_form_input': '_onInputFocusout',
        'keyup .o_form_input': '_onInputKeyup',
        'click .o_external_button': '_onExternalButtonClick',
        'click': '_onClick',
    }),
    supported_field_types: ['many2one'],

    init: function () {
        this._super.apply(this, arguments);
        this.limit = 7;
        this.orderer = new concurrency.DropMisordered();
        this.can_create = 'can_create' in this.attrs ? this.attrs.can_create : true;
        this.can_write = 'can_write' in this.attrs ? this.attrs.can_write : true;
        this.nodeOptions = _.defaults(this.nodeOptions, {
            quick_create: true,
        });
        this.m2o_value = field_utils.format.many2one(this.value);
    },
    start: function () {
        // what is 'this.floating' for? add a comment!
        this.floating = false;

        this.$input = this.$('.o_form_input');
        this.$external_button = this.$('.o_external_button');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        this.$input.focus();
        setTimeout(this.$input.select.bind(this.$input), 0);
    },
    /**
     * Focuses the input.
     */
    focus: function () {
        if (this.mode === "edit") {
            this.$input.focus();
        }
    },
    reinitialize: function (value) {
        this.floating = false;
        this._setValue(value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindAutoComplete: function () {
        var self = this;
        this.$input.autocomplete({
            source: function (req, resp) {
                self._search(req.term).then(function (result) {
                    resp(result);
                });
            },
            select: function (event, ui) {
                var item = ui.item;
                self.floating = false;
                if (item.id) {
                    self.reinitialize({id: item.id, display_name: item.name});
                } else if (item.action) {
                    item.action();
                }
                return false;
            },
            focus: function (event) {
                event.preventDefault(); // don't automatically select values on focus
            },
            autoFocus: true,
            html: true,
            minLength: 0,
            delay: 200,
        });
        this.$input.autocomplete("option", "position", { my : "left top", at: "left bottom" });
        this.autocomplete_bound = true;
    },
    /**
     * @private
     * @param {string} [name]
     * @returns {Object}
     */
    _createContext: function (name) {
        var tmp = {};
        var field = this.nodeOptions.create_name_field;
        if (field === undefined) {
            field = "name";
        }
        if (field !== false && name && this.nodeOptions.quick_create !== false) {
            tmp["default_" + field] = name;
        }
        return tmp;
    },
    /**
     * @private
     * @returns {Array}
     */
    _getSearchBlacklist: function () {
        return [];
    },
    /**
     * @private
     * @param {string} name
     */
    _quickCreate: function (name) {
        var self = this;
        var slowCreate = this._searchCreatePopup.bind(this, "form", false, this._createContext(name));
        if (this.nodeOptions.quick_create) {
            this._rpc({
                    model: this.field.relation,
                    method: 'name_create',
                    args: [name],
                    context: this.record.getContext({fieldName: this.name})
                })
                .then(function (result) {
                    if (self.mode === "edit") {
                        self.reinitialize({id: result[0], display_name: result[1]});
                    }
                }, slowCreate);
        } else {
            slowCreate();
        }
    },
    /**
     * @private
     */
    _renderEdit: function () {
        var value = this.m2o_value;

        // this is a stupid hack necessary to support the always_reload flag.
        // the field value has been reread by the basic model.  We use it to
        // display the full address of a patner, separated by \n.  This is
        // really a bad way to do it.  Now, we need to remove the extra lines
        // and hope for the best that noone tries to uses this mechanism to do
        // something else.
        if (this.nodeOptions.always_reload) {
            value = value.split('\n')[0];
        }
        this.$input.val(value);
        if (!this.autocomplete_bound) {
            this._bindAutoComplete();
        }
        this._updateExternalButton();
    },
    /**
     * @private
     */
    _renderReadonly: function () {
        var value = _.escape((this.m2o_value || "").trim()).split("\n").join("<br/>");
        this.$el.html(value);
        if (!this.nodeOptions.no_open) {
            this.$el.attr('href', '#');
            this.$el.addClass('o_form_uri');
        }
    },
    /**
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this.m2o_value = field_utils.format.many2one(this.value);
    },
    /**
     * @private
     * @param {string} search_val
     * @returns {Deferred}
     */
    _search: function (search_val) {
        var self = this;
        var def = $.Deferred();
        this.orderer.add(def);

        var context = this.record.getContext({fieldName: this.name});
        var domain = this.record.getDomain({fieldName: this.name});

        var blacklisted_ids = this._getSearchBlacklist();
        if (blacklisted_ids.length > 0) {
            domain.push(['id', 'not in', blacklisted_ids]);
        }

        this._rpc({
            model: this.field.relation,
            method: "name_search",
            kwargs: {
                name: search_val,
                args: domain,
                operator: "ilike",
                limit: this.limit + 1,
                context: context,
            }})
            .then(function (result) {
                // possible selections for the m2o
                var values = _.map(result, function (x) {
                    x[1] = x[1].split("\n")[0];
                    return {
                        label: _.str.escapeHTML(x[1].trim()) || data.noDisplayContent,
                        value: x[1],
                        name: x[1],
                        id: x[0],
                    };
                });

                // search more... if more results than limit
                if (values.length > self.limit) {
                    values = values.slice(0, self.limit);
                    values.push({
                        label: _t("Search More..."),
                        action: function () {
                            self._rpc({
                                    model: self.field.relation,
                                    method: 'name_search',
                                    kwargs: {
                                        name: search_val,
                                        args: domain,
                                        operator: "ilike",
                                        limit: 160,
                                        context: context,
                                    },
                                })
                                .then(self._searchCreatePopup.bind(self, "search"));
                        },
                        classname: 'o_m2o_dropdown_option',
                    });
                }
                var create_enabled = self.can_create && !self.nodeOptions.no_create;
                // quick create
                var raw_result = _.map(result, function (x) { return x[1]; });
                if (create_enabled && !self.nodeOptions.no_quick_create &&
                    search_val.length > 0 && !_.contains(raw_result, search_val)) {
                    values.push({
                        label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                            $('<span />').text(search_val).html()),
                        action: self._quickCreate.bind(self, search_val),
                        classname: 'o_m2o_dropdown_option'
                    });
                }
                // create and edit ...
                if (create_enabled && !self.nodeOptions.no_create_edit) {
                    values.push({
                        label: _t("Create and Edit..."),
                        action: self._searchCreatePopup.bind(self, "form", false, self._createContext(search_val)),
                        classname: 'o_m2o_dropdown_option',
                    });
                } else if (values.length === 0) {
                    values.push({
                        label: _t("No results to show..."),
                    });
                }

                def.resolve(values);
            });

        return def;
    },
    /**
     * all search/create popup handling
     *
     * @private
     * @param {any} view
     * @param {any} ids
     * @param {any} context
     */
    _searchCreatePopup: function (view, ids, context) {
        var self = this;
        new dialogs.SelectCreateDialog(this, _.extend({}, this.nodeOptions, {
            res_model: this.field.relation,
            domain: this.record.getDomain({fieldName: this.name}),
            context: _.extend({}, this.record.getContext({fieldName: this.name}), context || {}),
            title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
            initial_ids: ids ? _.map(ids, function (x) { return x[0]; }) : undefined,
            initial_view: view,
            disable_multiple_selection: true,
            on_selected: function (element_ids) {
                self.reinitialize({id: element_ids[0]});
                self.focus();
            }
        })).open();
    },
    /**
     * @private
     */
    _updateExternalButton: function () {
        var has_external_button = !this.nodeOptions.no_open && !this.floating && this.isSet();
        this.$external_button.toggle(has_external_button);
        this.$el.toggleClass('o_with_button', has_external_button);
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        var self = this;
        if (this.mode === 'readonly' && !this.nodeOptions.no_open) {
            event.preventDefault();
            event.stopPropagation();
            this._rpc({
                    model: this.field.relation,
                    method: 'get_formview_action',
                    args: [[this.value.res_id]],
                    context: this.record.getContext({fieldName: this.name}),
                })
                .then(function (action) {
                    self.trigger_up('do_action', {action: action});
                });
        }
    },
    /**
     * @private
     */
    _onExternalButtonClick: function () {
        if (!this.value) {
            this.focus();
            return;
        }
        var self = this;
        var context = this.record.getContext({fieldName: this.name});
        this._rpc({
                model: this.field.relation,
                method: 'get_formview_id',
                args: [[this.value.res_id]],
                context: context,
            })
            .then(function (view_id) {
                new dialogs.FormViewDialog(self, {
                    res_model: self.field.relation,
                    res_id: self.value.res_id,
                    context: context,
                    title: _t("Open: ") + self.string,
                    view_id: view_id,
                    readonly: !self.can_write,
                    on_saved: function () {
                        self.trigger_up('reload', {db_id: self.value.id});
                    },
                }).open();
            });
    },
    /**
     * @private
     */
    _onInputClick: function () {
        if (this.$input.autocomplete("widget").is(":visible")) {
            this.$input.autocomplete("close");
        } else {
            this.$input.autocomplete("search", "");
        }
    },
    /**
     * @private
     */
    _onInputFocusout: function () {
        if (this.can_create && this.floating) {
            new M2ODialog(this, this.string, this.$input.val()).open();
        }
    },
    /**
     * @private
     */
    _onInputKeyup: function () {
        if (this.$input.val() === "") {
            this.reinitialize(false);
        } else if (this.m2o_value !== this.$input.val()) {
            this.floating = true;
            this._updateExternalButton();
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onSearchCreatePopup: function (event) {
        var data = event.data;
        this._searchCreatePopup(data.view_type, false, this._createContext(data.value));
    },
});

var ListFieldMany2One = FieldMany2One.extend({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this.m2o_value);
    },
});

var KanbanFieldMany2One = AbstractField.extend({
    tagName: 'span',
    init: function () {
        this._super.apply(this, arguments);
        this.m2o_value = field_utils.format.many2one(this.value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _render: function () {
        this.$el.text(this.m2o_value);
    },
});

//------------------------------------------------------------------------------
// X2Many widgets
//------------------------------------------------------------------------------

var FieldX2Many = AbstractField.extend({
    tagName: 'div',
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
        kanban_record_delete: '_onDeleteRecord',
        list_record_delete: '_onDeleteRecord',
        add_record: '_onAddRecord',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
    }),

    /**
     * useSubview is used in form view to load view of the related model of the x2many field
     */
    useSubview: true,

    /**
     * @override
     */
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.operations = [];
        this.isReadonly = this.mode === 'readonly';
        this.view = this.attrs.views.list || this.attrs.views.kanban;
        this.activeActions = {};
        var arch = this.view && this.view.arch;
        if (arch) {
            this.activeActions.create = arch.attrs.create ?
                                            JSON.parse(arch.attrs.create) :
                                            true;
            this.editable = arch.attrs.editable;
        }
    },
    /**
     * @override
     */
    start: function () {
        return this._renderControlPanel().then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instanciates or updates the adequate renderer.
     *
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        if (!this.view) {
            return this._super();
        }
        if (this.renderer) {
            this.renderer.updateState(this.value);
            this.pager.updateState({ size: this.value.count });
            return $.when();
        }
        var arch = this.view.arch;
        if (arch.tag === 'tree') {
            this.renderer = new ListRenderer(this, this.value, {
                arch: arch,
                mode: this.mode,
                addCreateLine: !this.isReadonly && this.activeActions.create,
                addTrashIcon: !this.isReadonly,
            });
        }
        if (arch.tag === 'kanban') {
            var record_options = {
                editable: false,
                deletable: false,
                read_only_mode: this.isReadonly,
            };
            this.renderer = new KanbanRenderer(this, this.value, {
                arch: arch,
                record_options: record_options
            });
        }
        return this.renderer ? this.renderer.appendTo(this.$el) : this._super();
    },
    /**
     * Instanciates a control panel with the appropriate buttons and a pager.
     * Prepends the control panel's $el to this widget's $el.
     *
     * @private
     * @returns {Deferred}
     */
    _renderControlPanel: function () {
        if (!this.view) {
            return $.when();
        }
        var self = this;
        var defs = [];
        this.control_panel = new ControlPanel(this, "X2ManyControlPanel");
        this.pager = new Pager(this, this.value.count, this.value.offset + 1, this.value.limit, {
            single_page_hidden: true,
            withAccessKey: false,
        });
        this.pager.on('pager_changed', this, function (new_state) {
            this.trigger_up('load', {
                id: this.value.id,
                limit: new_state.limit,
                offset: new_state.current_min - 1,
                on_success: function (value) {
                    self.value = value;
                    self._render();
                },
            });
        });
        this._renderButtons();
        defs.push(this.pager.appendTo($('<div>'))); // start the pager
        defs.push(this.control_panel.prependTo(this.$el));
        return $.when.apply($, defs).then(function () {
            self.control_panel.update({
                cp_content: {
                    $buttons: self.$buttons,
                    $pager: self.pager.$el,
                }
            });
        });
    },
    /**
     * Renders the buttons and sets this.$buttons.
     *
     * @private
     */
    _renderButtons: function () {
        if (!this.isReadonly && this.view.arch.tag === 'kanban') {
            var options = { create_text: this.nodeOptions.create_text };
            this.$buttons = $(qweb.render('KanbanView.buttons', options));
            this.$buttons.on('click', 'button.o-kanban-button-new', this._onAddRecord.bind(this));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the user clicks on the 'Add an item' link (list case) or the
     * 'Add' button (kanban case).
     *
     * @abstract
     * @private
     */
    _onAddRecord: function () {
        // to implement
    },
    /**
     * Removes the given record from the relation.
     * Stops the propagation of the event to prevent it from being handled again
     * by the parent controller.
     *
     * @private
     * @param   {OdooEvent}
     */
    _onDeleteRecord: function (event) {
        event.stopPropagation();
        this._setValue({
            operation: 'REMOVE',
            id: event.data.id
        });
    },
    /**
     * Updates the given record with the changes.
     *
     * @private
     * @param   {OdooEvent}
     */
    _onFieldChanged: function (event) {
        if (event.target === this) {
            return;
        }
        event.stopPropagation();
        // changes occured in an editable list
        var changes = event.data.changes;
        if (Object.keys(changes).length) {
            this._setValue({
                operation: 'UPDATE',
                id: event.data.dataPointID,
                data: changes
            });
        }
    },
    /**
     * Called when the user clicks on a relational record.
     *
     * @abstract
     * @private
     */
    _onOpenRecord: function () {
        // to implement
    },
    /**
     * Adds field name information to the event, so that the view upstream is
     * aware of which widgets it has to redraw.
     *
     * @private
     * @param   {OdooEvent}
     */
    _onToggleColumnOrder: function (event) {
        event.data.field = this.name;
    },
});

var FieldOne2Many = FieldX2Many.extend({
    className: 'o_form_field_one2many',
    supportedFieldTypes: ['one2many'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     * @param {Object} record
     * @param {OdooEvent} [event] an event that triggered the reset action
     * @returns {Deferred}
     */
    reset: function (record, event) {
        var self = this;
        if (event && event.target === this && self.view.arch.tag === 'tree' && this.editable) {
            var command = event.data.changes[this.name];
            if (command.operation === 'UPDATE') {
                var fieldsChanged = _.keys(command.data);
                // FIXME: other fields might have change with onchange
                this.renderer.confirmChange(record.data[this.name], command.id, fieldsChanged);
                return $.when();
            }
        }
        return this._super.apply(this, arguments).then(function () {
            if (event && event.target === self && self.view.arch.tag === 'tree') {
                if (event.data.changes[self.name].operation === 'CREATE') {
                    // todo: get last record if editable = bottom
                    var newID = self.value.data[0].id;
                    self.renderer.editRecord(newID);
                }
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overrides to only render the buttons if the 'create' action is available.
     *
     * @override
     * @private
     */
    _renderButtons: function () {
        if (this.activeActions.create) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @private
     * @param {Object} params
     */
    _openFormDialog: function (params) {
        this.trigger_up('open_one2many_record', _.extend(params, {
            domain: this.record.getDomain({fieldName: this.name}),
            context: this.record.getContext({fieldName: this.name}),
            field: this.field,
            fields_view: this.attrs.views && this.attrs.views.form,
            viewInfo: this.view,
        }));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens a FormViewDialog to allow creating a new record for a one2many.
     *
     * @override
     * @private
     * @param {OdooEvent|MouseEvent} event this event comes either from the 'Add
     *   record' link in the list editable renderer, or from the 'Create' button
     *   in the kanban view
     */
    _onAddRecord: function (event) {
        // we don't want interference with the components upstream.
        event.stopPropagation();

        if (this.editable) {
            this._setValue({
                operation: 'CREATE',
                position: this.editable,
            });
        } else {
            var self = this;
            this._openFormDialog({
                on_saved: function (record) {
                    self._setValue({ operation: 'ADD', id: record.id });
                },
            });
        }
    },
    /**
     * Overrides the handler to set a specific 'on_save' callback as the o2m
     * sub-records aren't saved directly when the user clicks on 'Save' in the
     * dialog. Instead, the relational record is changed in the local data, and
     * this change is saved in DB when the user clicks on 'Save' in the main
     * form view.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        // we don't want interference with the components upstream.
        event.stopPropagation();

        this._openFormDialog({
            id: event.data.id,
            on_saved: this._setValue.bind(this, { operation: 'NOOP' }),
            readonly: this.mode === 'readonly',
        });
    },
});

var FieldMany2Many = FieldX2Many.extend({
    className: 'o_form_field_many2many',
    supportedFieldTypes: ['many2many'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.nodeOptions = _.defaults(this.nodeOptions, {
            create_text: _t('Add'),
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens a SelectCreateDialog.
     *
     * @override
     * @private
     */
    _onAddRecord: function () {
        var self = this;

        var domain = this.record.getDomain({fieldName: this.name});

        new dialogs.SelectCreateDialog(this, {
            res_model: this.field.relation,
            domain: domain.concat(["!", ["id", "in", this.value.res_ids]]),
            context: this.record.getContext({fieldName: this.name}),
            title: _t("Add: ") + this.string,
            no_create: this.nodeOptions.no_create || !this.activeActions.create,
            fields_view: this.attrs.views.form,
            on_selected: function (res_ids) {
                var new_ids = _.difference(res_ids, self.value.res_ids);
                if (new_ids.length) {
                    var values = _.map(new_ids, function (id) {
                        return {id: id};
                    });
                    self._setValue({
                        operation: 'ADD_M2M',
                        ids: values
                    });
                }
            }
        }).open();
    },
    /**
     * Intercepts the 'open_record' event to edit its data and lets it bubble up
     * to the form view.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        _.extend(event.data, {
            context: this.record.getContext({fieldName: this.name}),
            domain: this.record.getDomain({fieldName: this.name}),
            fields_view: this.attrs.views && this.attrs.views.form,
            on_saved: this.trigger_up.bind(this, 'reload', {db_id: event.data.id}),
            readonly: this.mode === 'readonly',
            string: this.string,
        });
    },
});

var FieldMany2ManyTags = AbstractField.extend({
    tag_template: "FieldMany2ManyTag",
    className: "o_form_field o_form_field_many2manytags",
    replace_element: true,
    supportedFieldTypes: ['many2many'],
    custom_events: {
        field_changed: '_onFieldChanged',
        move_next: '_onMoveNext',
    },
    events: _.extend({}, AbstractField.prototype.events, {
        'click .o_delete': '_onDeleteTag',
        'keydown .o_form_field_many2one input': '_onKeyDown',
    }),

    fetchSubFields: true,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        this.many2one.focus();
    },
    isSet: function () {
        return !!this.value && this.value.count;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} data
     */
    _addTag: function (data) {
        if (!_.contains(this.value.res_ids, data.id)) {
            this._setValue({
                operation: 'ADD_M2M',
                ids: data
            });
        }
    },
    /**
     * @private
     * @param {any} id
     */
    _removeTag: function (id) {
        var record = _.findWhere(this.value.data, {res_id: id});
        this._setValue({
            operation: 'REMOVE',
            id: record.id
        });
    },
    /**
     * @private
     */
    _renderEdit: function () {
        var self = this;
        this._renderTags();
        if (this.many2one) {
            this.many2one.destroy();
        }
        this.many2one = new FieldMany2One(this, this.name, this.record, {
            idForLabel: this.idForLabel,
            mode: 'edit',
        });
        // to prevent the M2O to take the value of the M2M
        this.many2one.value = false;
        // to prevent the M2O to take the relational values of the M2M
        this.many2one.m2o_value = '';

        this.many2one.nodeOptions.no_open = true;
        this.many2one._getSearchBlacklist = function () {
            return self.value.res_ids;
        };
        this.many2one.appendTo(this.$el);
    },
    /**
     * @private
     */
    _renderReadonly: function () {
        this._renderTags();
    },
    /**
     * @private
     */
    _renderTags: function () {
        var elements = this.value ? _.pluck(this.value.data, 'data') : [];
        this.$el.html(qweb.render(this.tag_template, {
            elements: elements,
            readonly: this.mode === "readonly",
        }));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onDeleteTag: function (event) {
        this._removeTag($(event.target).parent().data('id'));
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        if (event.target === this) {
            return;
        }
        event.stopPropagation();
        var new_value = event.data.changes[this.name];
        if (new_value) {
            this._addTag(new_value);
            this.many2one.reinitialize(false);
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} event
     */
    _onKeyDown: function (event) {
        if($(event.target).val() === "" && event.which === $.ui.keyCode.BACKSPACE) {
            var $badges = this.$('.badge');
            if($badges.length) {
                this._removeTag($badges.last().data('id'));
            }
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onMoveNext: function (event) {
        if (event.target === this) {
            return;
        }
        // Intercept event triggered up by the many2one, to prevent triggering it twice
        event.stopPropagation();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreate: function (event) {
        this._quickCreate(event.data.value);
    },
});

var FormFieldMany2ManyTags = FieldMany2ManyTags.extend({
    events: _.extend({}, FieldMany2ManyTags.prototype.events, {
        'click .badge': '_onOpenColorPicker',
        'mousedown .o_colorpicker span': '_onUpdateColor',
        'focusout .o_colorpicker': '_onCloseColorPicker',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCloseColorPicker: function (){
        this.$color_picker.remove();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onOpenColorPicker: function (event) {
        var tag_id = $(event.currentTarget).data('id');
        var tag = _.findWhere(this.value.data, { res_id: tag_id });
        if (tag && 'color' in tag.data) { // if there is a color field on the related model
            this.$color_picker = $(qweb.render('FieldMany2ManyTag.colorpicker', {
                'widget': this,
                'tag_id': tag_id,
            }));

            $(event.currentTarget).append(this.$color_picker);
            this.$color_picker.dropdown('toggle');
            this.$color_picker.attr("tabindex", 1).focus();
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onUpdateColor: function (event) {
        event.preventDefault();
        var self = this;
        var color = $(event.currentTarget).data('color');
        var id = $(event.currentTarget).data('id');
        var tag = self.$("span.badge[data-id='" + id + "']");
        var current_color = tag.data('color');

        if (color === current_color) { return; }

        this.trigger_up('field_changed', {
            dataPointID: _.findWhere(this.value.data, {res_id: id}).id,
            changes: {
                color: color,
            },
            force_save: true,
        });
    },
});

var KanbanFieldMany2ManyTags = FieldMany2Many.extend({
    _render: function () {
        var self = this;
        this.$el.addClass('o_form_field_many2manytags o_kanban_tags');
        _.each(this.value.data, function (m2m) {
            // 10th color is invisible
            if ('color' in m2m.data && m2m.data.color !== 10) {
                $('<span>')
                    .addClass('o_tag o_tag_color_' + m2m.data.color)
                    .attr('title', _.str.escapeHTML(m2m.data.display_name))
                    .appendTo(self.$el);
            }
        });
    },
});

var FieldMany2ManyCheckBoxes = AbstractField.extend({
    template: 'FieldMany2ManyCheckBoxes',
    events: _.extend({}, AbstractField.prototype.events, {
        change: '_onChange',
    }),
    specialData: "_fetchSpecialRelation",
    supportedFieldTypes: ['many2many'],
    init: function () {
        this._super.apply(this, arguments);
        this.m2mValues = this.record.specialData[this.name];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _render: function () {
        var self = this;
        this._super.apply(this, arguments);
        _.each(this.value, function (id) {
            self.$('input[data-record-id="' + id + '"]').prop('checked', true);
        });
    },
    /**
     * @private
     */
    _renderReadonly: function () {
        this.$("input").prop("disabled", true);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChange: function () {
        var ids = _.map(this.$('input:checked'), function (input) {
            return $(input).data("record-id");
        });
        this._setValue({
            operation: 'REPLACE_WITH',
            ids: ids,
        });
    },
});

//------------------------------------------------------------------------------
// Widgets handling both basic and relational fields (selection and Many2one)
//------------------------------------------------------------------------------

var FieldStatus = AbstractField.extend({
    className: 'o_statusbar_status',
    events: {
        'click button:not(.dropdown-toggle)': '_onClickStage',
    },
    specialData: "_fetchSpecialStatus",
    supportedFieldTypes: ['selection', 'many2one'],
    /**
     * @override init from AbstractField
     */
    init: function () {
        this._super.apply(this, arguments);
        this._setState();
        this._onClickStage = _.debounce(this._onClickStage, 300, true); // TODO maybe not useful anymore ?
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override _reset from AbstractField
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setState();
    },
    /**
     * Prepares the rendering data from the field and record data.
     * @private
     */
    _setState: function () {
        var self = this;
        if (this.field.type === 'many2one') {
            this.status_information = _.map(this.record.specialData[this.name], function (info) {
                return _.extend({
                    selected: info.id === self.value.res_id,
                }, info);
            });
        } else {
            var selection = this.field.selection;
            if (this.attrs.statusbar_visible) {
                var restriction = this.attrs.statusbar_visible.split(",");
                selection = _.filter(selection, function (val) {
                    return _.contains(restriction, val[0]) || val[0] === self.value;
                });
            }
            this.status_information = _.map(selection, function (val) {
                return { id: val[0], display_name: val[1], selected: val[0] === self.value, fold: false };
            });
        }
    },
    /**
     * @override _render from AbstractField
     * @private
     */
    _render: function () {
        if (config.device.size_class > config.device.SIZES.XS) {
            var selections = _.partition(this.status_information, function (info) {
                return (info.selected || !info.fold);
            });
            this.$el.html(qweb.render("FieldStatus.content.desktop", {
                selection_unfolded: selections[0],
                selection_folded: selections[1],
                clickable: !!this.attrs.clickable,
            }));
        } else {
            this.$el.html(qweb.render("FieldStatus.content.mobile", {
                selection: this.status_information,
                value: _.findWhere(this.status_information, {selected: true}).display_name,
                clickable: !!this.attrs.clickable,
            }));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when on status stage is clicked -> sets the field value.
     *
     * @private
     * @param {MouseEvent} e
     */
    _onClickStage: function (e) {
        this._setValue($(e.currentTarget).data("value"));
    },
});

/**
 * The FieldSelection widget is a simple select tag with a dropdown menu to
 * allow the selection of a range of values.  It is designed to work with fields
 * of type 'selection' and 'many2one'.
 */
var FieldSelection = AbstractField.extend({
    template: 'FieldSelection',
    specialData: "_fetchSpecialRelation",
    supportedFieldTypes: ['selection', 'many2one'],
    events: _.extend({}, AbstractField.prototype.events, {
        'change': '_onChange',
    }),
    replace_element: true,
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.values = [];
        if (this.field.type === 'many2one') {
            this.values = this.record.specialData[this.name];
        } else {
            this.values = _.reject(this.field.selection, function (v) {
                return v[0] === false && v[1] === '';
            });
        }
        this.values = [[false, this.attrs.placeholder || '']].concat(this.values);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Format the value to a valid string
     *
     * @override
     * @private
     * @param {any} value
     * @returns {string}
     */
    _formatValue: function (value) {
        if (this.field.type === 'many2one') {
            var options = _.extend({}, this.nodeOptions);
            return field_utils.format.many2one(value, this.field, this.recordData, options);
        } else {
            return this._super(value);
        }
    },
    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$el.empty();
        for (var i = 0 ; i < this.values.length ; i++) {
            this.$el.append($('<option/>', {
                value: JSON.stringify(this.values[i][0]),
                html: this.values[i][1]
            }));
        }
        this.$el.val(JSON.stringify(this._parseValue(this.value)));
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.empty().html(this._formatValue(this.value));
    },
    /**
     * @override
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        if (this.field.type === 'many2one') {
            this.value = this.value.data.id;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * The small slight difficulty is that we have to set the value differently
     * depending on the field type.
     * @private
     */
    _onChange: function () {
        var res_id = JSON.parse(this.$el.val());
        if (this.field.type === 'many2one') {
            var value = _.find(this.values, function (val) {
                return val[0] === res_id;
            });
            this._setValue({id: res_id, display_name: value[1]});
        } else {
            this._setValue(res_id);
        }
    },
});

var FieldRadio = FieldSelection.extend({
    template: 'FieldRadio',
    specialData: "_fetchSpecialMany2ones",
    supportedFieldTypes: ['selection', 'many2one'],
    events: _.extend({}, AbstractField.prototype.events, {
        'click input': '_onInputClick',
    }),
    /**
     * @constructs FieldRadio
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.field.type === 'selection') {
            this.values = this.field.selection || [];
        } else if (this.field.type === 'many2one') {
            this.values = _.map(this.record.specialData[this.name], function (val) {
                return [val.id, val.display_name];
            });
        }
        this.unique_id = _.uniqueId("radio");
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {boolean} always true
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        this.$("input").prop("checked", false);
        var key;
        if (this.field.type === 'many2one') {
            key = this._parseValue(this.value);
        } else {
            key = this.value;
        }
        this.$('input[data-value="' + key  + '"]').prop('checked', true);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onInputClick: function (event) {
        var res_id = $(event.target).data('value');
        if (this.field.type === 'many2one') {
            var value = _.find(this.values, function (val) {
                return val[0] === res_id;
            });
            this._setValue({id: res_id, display_name: value[1]});
        } else {
            this._setValue(res_id);
        }
    },
});

return {
    FieldMany2One: FieldMany2One,
    KanbanFieldMany2One: KanbanFieldMany2One,
    ListFieldMany2One: ListFieldMany2One,

    FieldOne2Many: FieldOne2Many,

    FieldMany2Many: FieldMany2Many,
    FieldMany2ManyCheckBoxes: FieldMany2ManyCheckBoxes,
    FieldMany2ManyTags: FieldMany2ManyTags,
    FormFieldMany2ManyTags: FormFieldMany2ManyTags,
    KanbanFieldMany2ManyTags: KanbanFieldMany2ManyTags,

    FieldRadio: FieldRadio,
    FieldSelection: FieldSelection,
    FieldStatus: FieldStatus,
};

});
