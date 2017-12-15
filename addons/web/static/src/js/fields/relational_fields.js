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
var basicFields = require('web.basic_fields');
var concurrency = require('web.concurrency');
var ControlPanel = require('web.ControlPanel');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
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
                        this.close(true);
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
    /**
     * @override
     * @param {boolean} isSet
     */
    close: function (isSet) {
        this.isSet = isSet;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        if (!this.isSet) {
            this.trigger_up('closed_unset');
        }
        this._super.apply(this, arguments);
    },
});

var FieldMany2One = AbstractField.extend({
    supportedFieldTypes: ['many2one'],
    template: 'FieldMany2One',
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        'closed_unset': '_onDialogClosedUnset',
        'field_changed': '_onFieldChanged',
        'quick_create': '_onQuickCreate',
        'search_create_popup': '_onSearchCreatePopup',
    }),
    events: _.extend({}, AbstractField.prototype.events, {
        'click input': '_onInputClick',
        'focusout input': '_onInputFocusout',
        'keyup input': '_onInputKeyup',
        'click .o_external_button': '_onExternalButtonClick',
        'click': '_onClick',
    }),
    AUTOCOMPLETE_DELAY: 200,

    init: function () {
        this._super.apply(this, arguments);
        this.limit = 7;
        this.orderer = new concurrency.DropMisordered();

        // should normally also be set, except in standalone M20
        this.can_create = ('can_create' in this.attrs ? JSON.parse(this.attrs.can_create) : true) &&
            !this.nodeOptions.no_create;
        this.can_write = 'can_write' in this.attrs ? JSON.parse(this.attrs.can_write) : true;

        this.nodeOptions = _.defaults(this.nodeOptions, {
            quick_create: true,
        });
        this.m2o_value = this._formatValue(this.value);
        // 'recordParams' is a dict of params used when calling functions
        // 'getDomain' and 'getContext' on this.record
        this.recordParams = {fieldName: this.name, viewType: this.viewType};
        // We need to know if the widget is dirty (i.e. if the user has changed
        // the value, and those changes haven't been acknowledged yet by the
        // environment), to prevent erasing that new value on a reset (e.g.
        // coming by an onchange on another field)
        this.isDirty = false;
        this.lastChangeEvent = undefined;
    },
    start: function () {
        // booleean indicating that the content of the input isn't synchronized
        // with the current m2o value (for instance, the user is currently
        // typing something in the input, and hasn't selected a value yet).
        this.floating = false;

        this.$input = this.$('input');
        this.$external_button = this.$('.o_external_button');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {jQuery}
     */
    getFocusableElement: function () {
        return this.mode === 'edit' && this.$input || this.$el;
    },
    /**
     * TODO
     */
    reinitialize: function (value) {
        this.isDirty = false;
        this.floating = false;
        this._setValue(value);
    },
    /**
     * Re-renders the widget if it isn't dirty. The widget is dirty if the user
     * changed the value, and that change hasn't been acknowledged yet by the
     * environment. For example, another field with an onchange has been updated
     * and this field is updated before the onchange returns. Two '_setValue'
     * are done (this is sequential), the first one returns and this widget is
     * reset. However, it has pending changes, so we don't re-render.
     *
     * @override
     */
    reset: function (record, event) {
        this._reset(record, event);
        if (!event || event === this.lastChangeEvent) {
            this.isDirty = false;
        }
        if (this.isDirty) {
            return $.when();
        } else {
            return this._render();
        }
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
                // we do not want the select event to trigger any additional
                // effect, such as navigating to another field.
                event.stopImmediatePropagation();
                event.preventDefault();

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
            close: function (event) {
                // it is necessary to prevent ESC key from propagating to field
                // root, to prevent unwanted discard operations.
                if (event.which === $.ui.keyCode.ESCAPE) {
                    event.stopPropagation();
                }
            },
            autoFocus: true,
            html: true,
            minLength: 0,
            delay: this.AUTOCOMPLETE_DELAY,
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
    * Returns the display_name from a string which contains it but was altered
    * as a result of the show_address option using a horrible hack.
    *
    * @private
    * @param {string} value
    * @returns {string} display_name without show_address mess
    */
    _getDisplayName: function (value) {
        return value.split('\n')[0];
    },
    /**
     * Listens to events 'field_changed' to keep track of the last event that
     * has been trigerred. This allows to detect that all changes have been
     * acknowledged by the environment.
     *
     * @param {OdooEvent} event 'field_changed' event
     */
    _onFieldChanged: function (event) {
        this.lastChangeEvent = event;
    },
    /**
     * @private
     * @param {string} name
     * @returns {Deferred} resolved after the name_create or when the slowcreate
     *                     modal is closed.
     */
    _quickCreate: function (name) {
        var self = this;
        var def = $.Deferred();
        var slowCreate = function () {
            var dialog = self._searchCreatePopup("form", false, self._createContext(name));
            dialog.on('closed', self, def.resolve.bind(def));
        };
        if (this.nodeOptions.quick_create) {
            this.trigger_up('mutexify', {
                action: function () {
                    return self._rpc({
                        model: self.field.relation,
                        method: 'name_create',
                        args: [name],
                        context: self.record.getContext(self.recordParams),
                    }).then(function (result) {
                        if (self.mode === "edit") {
                            self.reinitialize({id: result[0], display_name: result[1]});
                        }
                        def.resolve();
                    }).fail(function (error, event) {
                        event.preventDefault();
                        slowCreate();
                    });
                },
            });
        } else {
            slowCreate();
        }
        return def;
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
            value = this._getDisplayName(value);
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
        this.floating = false;
        this.m2o_value = this._formatValue(this.value);
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

        var context = this.record.getContext(this.recordParams);
        var domain = this.record.getDomain(this.recordParams);

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
                    x[1] = self._getDisplayName(x[1]);
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
                    var createAndEditAction = function () {
                        // Clear the value in case the user clicks on discard
                        self.$('input').val('');
                        return self._searchCreatePopup("form", false, self._createContext(search_val));
                    };
                    values.push({
                        label: _t("Create and Edit..."),
                        action: createAndEditAction,
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
        return new dialogs.SelectCreateDialog(this, _.extend({}, this.nodeOptions, {
            res_model: this.field.relation,
            domain: this.record.getDomain({fieldName: this.name}),
            context: _.extend({}, this.record.getContext(this.recordParams), context || {}),
            title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
            initial_ids: ids ? _.map(ids, function (x) { return x[0]; }) : undefined,
            initial_view: view,
            disable_multiple_selection: true,
            on_selected: function (records) {
                self.reinitialize(records[0]);
                self.activate();
            }
        })).open();
    },
    /**
     * @private
     */
    _updateExternalButton: function () {
        var has_external_button = !this.nodeOptions.no_open && !this.floating && this.isSet();
        this.$external_button.toggle(has_external_button);
        this.$el.toggleClass('o_with_button', has_external_button); // Should not be required anymore but kept for compatibility
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
                    context: this.record.getContext(this.recordParams),
                })
                .then(function (action) {
                    self.trigger_up('do_action', {action: action});
                });
        }
    },

    /**
     * Reset the input as dialog has been closed without m2o creation.
     *
     * @private
     */
    _onDialogClosedUnset: function () {
        this.isDirty = false;
        this.floating = false;
        this._render();
    },
    /**
     * @private
     */
    _onExternalButtonClick: function () {
        if (!this.value) {
            this.activate();
            return;
        }
        var self = this;
        var context = this.record.getContext(this.recordParams);
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
                    on_saved: function (record, changed) {
                        if (changed) {
                            self._setValue(self.value.data, {forceChange: true});
                            self.trigger_up('reload', {db_id: self.value.id});
                        }
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
        } else if (this.floating) {
            this.$input.autocomplete("search"); // search with the input's content
        } else {
            this.$input.autocomplete("search", ''); // search with the empty string
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
     *
     * @param {OdooEvent} ev
     */
    _onInputKeyup: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            // If we pressed enter, we want to prevent _onInputFocusout from
            // executing since it would open a M2O dialog to request
            // confirmation that the many2one is not properly set.
            return;
        }
        this.isDirty = true;
        if (this.$input.val() === "") {
            this.reinitialize(false);
        } else if (this._getDisplayName(this.m2o_value) !== this.$input.val()) {
            this.floating = true;
            this._updateExternalButton();
        }
    },
    /**
     * @override
     * @private
     */
    _onKeydown: function () {
        this.floating = false;
        this._super.apply(this, arguments);
    },
    /**
     * Stops the left/right navigation move event if the cursor is not at the
     * start/end of the input element. Stops any navigation move event if the
     * user is selecting text.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        // TODO Maybe this should be done in a mixin or, better, the m2o field
        // should be an InputField (but this requires some refactoring).
        basicFields.InputField.prototype._onNavigationMove.apply(this, arguments);
        if (this.mode === 'edit' && $(this.$input.autocomplete('widget')).is(':visible')) {
            ev.stopPropagation();
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreate: function (event) {
        this._quickCreate(event.data.value);
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
        this.m2o_value = this._formatValue(this.value);
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
        add_record: '_onAddRecord',
        discard_changes: '_onDiscardChanges',
        edit_line: '_onEditLine',
        field_changed: '_onFieldChanged',
        kanban_record_delete: '_onDeleteRecord',
        list_record_delete: '_onDeleteRecord',
        open_record: '_onOpenRecord',
        save_line: '_onSaveLine',
        resequence: '_onResequence',
        toggle_column_order: '_onToggleColumnOrder',
    }),

    // We need to trigger the reset on every changes to be aware of the parent changes
    // and then evaluate the 'column_invisible' modifier in case a evaluated value
    // changed.
    resetOnAnyFieldChange: true,

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
        this.view = this.attrs.views[this.attrs.mode];
        this.activeActions = {};
        this.recordParams = {fieldName: this.name, viewType: this.viewType};
        var arch = this.view && this.view.arch;
        if (arch) {
            this.activeActions.create = arch.attrs.create ?
                                            JSON.parse(arch.attrs.create) :
                                            true;
            this.activeActions.delete = arch.attrs.delete ?
                                            JSON.parse(arch.attrs.delete) :
                                            true;
            this.editable = arch.attrs.editable;
        }
        if (this.attrs.columnInvisibleFields) {
            this._processColumnInvisibleFields();
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
     * A x2m field can only be saved if it finished the edition of all its rows.
     * On parent view saving, we have to ask the x2m fields to commit their
     * changes, that is confirming the save of the in-edition row or asking the
     * user if he wants to discard it if necessary.
     *
     * @override
     * @returns {Deferred}
     */
    commitChanges: function () {
        var self = this;
        var inEditionRecordID =
            this.renderer
            && this.renderer.viewType === "list"
            && this.renderer.getEditableRecordID();
        if (inEditionRecordID) {
            return this.renderer.commitChanges(inEditionRecordID).then(function () {
                return self._saveLine(inEditionRecordID);
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    isSet: function () {
        return true;
    },
    /**
     * @override
     * @param {Object} record
     * @param {OdooEvent} [ev] an event that triggered the reset action
     * @param {Boolean} [fieldChanged] if true, the widget field has changed
     * @returns {Deferred}
     */
    reset: function (record, ev, fieldChanged) {
        // If 'fieldChanged' is false, it means that the reset was triggered by
        // the 'resetOnAnyFieldChange' mechanism. If it is the case the
        // modifiers are evaluated and if there is no change in the modifiers
        // values, the reset is skipped.
        if (!fieldChanged) {
           var newEval = this._evalColumnInvisibleFields();
           if (_.isEqual(this.currentColInvisibleFields, newEval)) {
               return $.when();
           }
        } else if (ev && ev.target === this && ev.data.changes && this.view.arch.tag === 'tree') {
            var command = ev.data.changes[this.name];
            // Here, we only consider 'UPDATE' commands with data, which occur
            // with editable list view. In order to keep the current line in
            // edition, we call confirmUpdate which will try to reset the widgets
            // of the line being edited, and rerender the rest of the list.
            // 'UPDATE' commands with no data can be ignored: they occur in
            // one2manys when the record is updated from a dialog and in this
            // case, we can re-render the whole subview.
            if (command.operation === 'UPDATE' && command.data) {
                var state = record.data[this.name];
                var fieldNames = state.getFieldNames();
                this._reset(record, ev);
                return this.renderer.confirmUpdate(state, command.id, fieldNames, ev.initialEvent);
            }
        }
        return this._super.apply(this, arguments);
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Evaluates the 'column_invisible' modifier for the parent record.
     *
     * @return {Object} Object containing fieldName as key and the evaluated
     *                         column_invisible modifier
     */
    _evalColumnInvisibleFields: function () {
        var self = this;
        return _.mapObject(this.columnInvisibleFields, function (domains) {
            return self.record.evalModifiers({
                column_invisible: domains,
             }).column_invisible;
        });
    },
    /**
     * Instanciates or updates the adequate renderer.
     *
     * @override
     * @private
     * @returns {Deferred|undefined}
     */
    _render: function () {
        if (!this.view) {
            return this._super();
        }
        if (this.renderer) {
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer.updateState(this.value, {'columnInvisibleFields': this.currentColInvisibleFields});
            this.pager.updateState({ size: this.value.count });
            return $.when();
        }
        var arch = this.view.arch;
        var viewType;
        if (arch.tag === 'tree') {
            viewType = 'list';
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer = new ListRenderer(this, this.value, {
                arch: arch,
                editable: this.mode === 'edit' && arch.attrs.editable,
                addCreateLine: !this.isReadonly && this.activeActions.create,
                addTrashIcon: !this.isReadonly && this.activeActions.delete,
                viewType: viewType,
                columnInvisibleFields: this.currentColInvisibleFields,
            });
        }
        if (arch.tag === 'kanban') {
            viewType = 'kanban';
            var record_options = {
                editable: false,
                deletable: false,
                read_only_mode: this.isReadonly,
            };
            this.renderer = new KanbanRenderer(this, this.value, {
                arch: arch,
                record_options: record_options,
                viewType: viewType,
            });
        }
        this.$el.addClass('o_field_x2many o_field_x2many_' + viewType);
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
    /**
     * Saves the line associated to the given recordID. If the line is valid,
     * it only has to be switched to readonly mode as all the line changes have
     * already been notified to the model so that they can be saved in db if the
     * parent view is actually saved. If the line is not valid, the line is to
     * be discarded if the user agrees (this behavior is not a list editable
     * one but a x2m one as it is made to replace the "discard" button which
     * exists for list editable views).
     *
     * @private
     * @param {string} recordID
     * @returns {Deferred} resolved if the line was properly saved or discarded.
     *                     rejected if the line could not be saved and the user
     *                     did not agree to discard.
     */
    _saveLine: function (recordID) {
        var def = $.Deferred();
        var fieldNames = this.renderer.canBeSaved(recordID);
        if (fieldNames.length) {
            this.trigger_up('discard_changes', {
                recordID: recordID,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
            });
        } else {
            this.renderer.setRowMode(recordID, 'readonly').done(def.resolve.bind(def));
        }
        return def;
    },
    /**
     * Parses the 'columnInvisibleFields' attribute to search for the domains
     * containing the key 'parent'. If there are such domains, the string
     * 'parent.field' is replaced with 'field' in order to be evaluated
     * with the right field name in the parent context.
     *
     * @private
     */
    _processColumnInvisibleFields: function () {
        var columnInvisibleFields = {};
        _.each(this.attrs.columnInvisibleFields, function (domains, fieldName) {
            if (_.isArray(domains)) {
                columnInvisibleFields[fieldName] = _.map(domains, function (domain) {
                    // We check if the domain is an array to avoid processing
                    // the '|' and '&' cases
                    if (_.isArray(domain)) {
                        return [domain[0].split('.')[1]].concat(domain.slice(1));
                    }
                    return domain;
                });
            }
        });
        this.columnInvisibleFields = columnInvisibleFields;
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
     * @param {OdooEvent} ev
     */
    _onDeleteRecord: function (ev) {
        ev.stopPropagation();
        var shouldForget = this.attrs.widget === 'many2many' || this.field.type === 'many2many';
        var operation = shouldForget ? 'FORGET' : 'DELETE';
        this._setValue({
            operation: operation,
            ids: [ev.data.id],
        });
    },
    /**
     * When the discard_change event go through this field, we can just decorate
     * the data with the name of the field.  The origin field ignore this
     * information (it is a subfield in a o2m), and the controller will need to
     * know which field needs to be handled.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardChanges: function (ev) {
        ev.data.fieldName = this.name;
    },
    /**
     * Called when the renderer asks to edit a line, in that case simply tells
     * him back to toggle the mode of this row.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditLine: function (ev) {
        ev.stopPropagation();
        var editedRecord = this.value.data[ev.data.index];
        this.renderer.setRowMode(editedRecord.id, 'edit')
            .done(ev.data.onSuccess);
    },
    /**
     * Updates the given record with the changes.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onFieldChanged: function (ev) {
        if (ev.target === this) {
            ev.initialEvent = this.lastInitialEvent;
            return;
        }
        ev.stopPropagation();
        // changes occured in an editable list
        var changes = ev.data.changes;
        // save the initial event triggering the field_changed, as it will be
        // necessary when the field triggering this event will be reset (to
        // prevent it from re-rendering itself, formatting its value, loosing
        // the focus... while still being edited)
        this.lastInitialEvent = undefined;
        if (Object.keys(changes).length) {
            this.lastInitialEvent = ev;
            this._setValue({
                operation: 'UPDATE',
                id: ev.data.dataPointID,
                data: changes,
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
     * Called when the renderer ask to save a line (the user tries to leave it)
     * -> Nothing is to "save" here, the model was already notified of the line
     * changes; if the row could be saved, we make the row readonly. Otherwise,
     * we trigger a new event for the view to tell it to discard the changes
     * made to that row.
     * Note that we do that in the controller mutex to ensure that the check on
     * the row (whether or not it can be saved) is done once all potential
     * onchange RPCs are done (those RPCs being executed in the same mutex).
     * This particular handling is done in this handler, instead of in the
     * _saveLine function directly, because _saveLine is also called from
     * the controller (via commitChanges), and in this case, it is already
     * executed in the mutex.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.recordID
     * @param {function} ev.onSuccess success callback (see '_saveLine')
     * @param {function} ev.onFailure fail callback (see '_saveLine')
     */
    _onSaveLine: function (ev) {
        var self = this;
        ev.stopPropagation();
        this.trigger_up('mutexify', {
            action: function () {
                return self.renderer.commitChanges(ev.data.recordID).then(function () {
                    self.trigger_up('mutexify', {
                        action: function () {
                            return self._saveLine(ev.data.recordID)
                                .done(ev.data.onSuccess)
                                .fail(ev.data.onFailure);
                        },
                    });
                });
            },
        });
    },
    /**
     * Forces a resequencing of the records.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onResequence: function (event) {
        var self = this;
        var rowIDs = event.data.rowIDs.slice();
        var rowID = rowIDs.pop();
        var defs = _.map(rowIDs, function (rowID, index) {
            var data = {};
            data[event.data.handleField] = event.data.offset + index;
            return self._setValue({
                operation: 'UPDATE',
                id: rowID,
                data: data,
            }, {
                notifyChange: false,
            });
        });
        $.when.apply($, defs).then(function () {
            // trigger only once the onchange for parent record
            self._setValue({
                operation: 'UPDATE',
                id: rowID,
                data: _.object([event.data.handleField], [event.data.offset + rowIDs.length]),
            });
        });
    },
    /**
     * Adds field name information to the event, so that the view upstream is
     * aware of which widgets it has to redraw.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onToggleColumnOrder: function (ev) {
        ev.data.field = this.name;
    },
});

var FieldOne2Many = FieldX2Many.extend({
    className: 'o_field_one2many',
    supportedFieldTypes: ['one2many'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        // boolean used to prevent concurrent record creation
        this.creatingRecord = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     * @param {Object} record
     * @param {OdooEvent} [ev] an event that triggered the reset action
     * @returns {Deferred}
     */
    reset: function (record, ev) {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (ev && ev.target === self && ev.data.changes && self.view.arch.tag === 'tree') {
                if (ev.data.changes[self.name].operation === 'CREATE') {
                    var index = self.editable === 'top' ? 0 : self.value.data.length - 1;
                    var newID = self.value.data[index].id;
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
            domain: this.record.getDomain(this.recordParams),
            context: this.record.getContext(this.recordParams),
            field: this.field,
            fields_view: this.attrs.views && this.attrs.views.form,
            parentID: this.value.id,
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
     * @param {OdooEvent|MouseEvent} ev this event comes either from the 'Add
     *   record' link in the list editable renderer, or from the 'Create' button
     *   in the kanban view
     */
    _onAddRecord: function (ev) {
        var self = this;
        // we don't want interference with the components upstream.
        ev.stopPropagation();

        if (this.editable) {
            if (!this.activeActions.create) {
                if (ev.data.onFail) {
                    ev.data.onFail();
                }
            } else if (!this.creatingRecord) {
                this.creatingRecord = true;
                this._setValue({
                    operation: 'CREATE',
                    position: this.editable,
                }).always(function () {
                    self.creatingRecord = false;
                });
            }
        } else {
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
     * @param {OdooEvent} ev
     */
    _onOpenRecord: function (ev) {
        // we don't want interference with the components upstream.
        ev.stopPropagation();

        var id = ev.data.id;
        // trigger an empty 'UPDATE' operation when the user clicks on 'Save' in
        // the dialog, to notify the main record that a subrecord of this
        // relational field has changed (those changes will be already stored on
        // that subrecord, thanks to the 'Save').
        var onSaved = this._setValue.bind(this, { operation: 'UPDATE', id: id }, {});
        this._openFormDialog({
            id: id,
            on_saved: onSaved,
            readonly: this.mode === 'readonly',
        });
    },
});

var FieldMany2Many = FieldX2Many.extend({
    className: 'o_field_many2many',
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
     * @param {OdooEvent|MouseEvent} ev this event comes either from the 'Add
     *   record' link in the list editable renderer, or from the 'Create' button
     *   in the kanban view
     */
    _onAddRecord: function (ev) {
        var self = this;
        ev.stopPropagation();

        var domain = this.record.getDomain({fieldName: this.name});

        new dialogs.SelectCreateDialog(this, {
            res_model: this.field.relation,
            domain: domain.concat(["!", ["id", "in", this.value.res_ids]]),
            context: this.record.getContext(this.recordParams),
            title: _t("Add: ") + this.string,
            no_create: this.nodeOptions.no_create || !this.activeActions.create,
            fields_view: this.attrs.views.form,
            on_selected: function (records) {
                var resIDs = _.pluck(records, 'id');
                var newIDs = _.difference(resIDs, self.value.res_ids);
                if (newIDs.length) {
                    var values = _.map(newIDs, function (id) {
                        return {id: id};
                    });
                    self._setValue({
                        operation: 'ADD_M2M',
                        ids: values,
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
     * @param {OdooEvent} ev
     */
    _onOpenRecord: function (ev) {
        var self = this;
        _.extend(ev.data, {
            context: this.record.getContext(this.recordParams),
            domain: this.record.getDomain(this.recordParams),
            fields_view: this.attrs.views && this.attrs.views.form,
            on_saved: function () {
                self._setValue({operation: 'TRIGGER_ONCHANGE'}, {forceChange: true});
                self.trigger_up('reload', {db_id: ev.data.id});
            },
            readonly: this.mode === 'readonly',
            string: this.string,
        });
    },
});

/**
 * Widget to upload or delete one or more files at the same time.
 */
var FieldMany2ManyBinaryMultiFiles = AbstractField.extend({
    template: "FieldBinaryFileUploader",
    supportedFieldTypes: ['many2many'],
    fieldsToFetch: {
        name: {type: 'char'},
        datas_fname: {type: 'char'},
        mimetype: {type: 'char'},
    },
    events: {
        'click .o_attach': '_onAttach',
        'click .oe_delete': '_onDelete',
        'change .o_input_file': '_onFileChanged',
    },
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        if (this.field.type !== 'many2many' || this.field.relation !== 'ir.attachment') {
            var msg = _t("The type of the field '%s' must be a many2many field with a relation to 'ir.attachment' model.");
            throw _.str.sprintf(msg, this.field.string);
        }

        this.uploadedFiles = {};
        this.uploadingFiles = [];
        this.fileupload_id = _.uniqueId('oe_fileupload_temp');
        $(window).on(this.fileupload_id, this._onFileLoaded.bind(this));

        this.metadata = {};
    },

    destroy: function () {
        this._super();
        $(window).off(this.fileupload_id);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute the URL of an attachment.
     *
     * @private
     * @param {Object} attachment
     * @returns {string} URL of the attachment
     */
    _getFileUrl: function (attachment) {
        return '/web/content/' + attachment.id + '?download=true';
    },
    /**
     * Process the field data to add some information (url, etc.).
     *
     * @private
     */
    _generatedMetadata: function () {
        var self = this;
        _.each(this.value.data, function (record) {
            // tagging `allowUnlink` ascertains if the attachment was user
            // uploaded or was an existing or system generated attachment
            self.metadata[record.id] = {
                allowUnlink: self.uploadedFiles[record.data.id] || false,
                url: self._getFileUrl(record.data),
            };
        });
    },
    /**
     * @private
     * @override
     */
    _render: function () {
        // render the attachments ; as the attachments will changes after each
        // _setValue, we put the rendering here to ensure they will be updated
        this._generatedMetadata();
        this.$('.oe_placeholder_files, .oe_attachments')
            .replaceWith($(qweb.render('FieldBinaryFileUploader.files', {
                widget: this,
            })));
        this.$('.oe_fileupload').show();

        // display image thumbnail
        this.$('.o_image[data-mimetype^="image"]').each(function () {
            var $img = $(this);
            if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
                $img.css('background-image', "url('" + $img.data('src') + "')");
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAttach: function () {
        // This widget uses a hidden form to upload files. Clicking on 'Attach'
        // will simulate a click on the related input.
        this.$('.o_input_file').click();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDelete: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var fileID = $(ev.currentTarget).data('id');
        var record = _.findWhere(this.value.data, {res_id: fileID});
        if (record) {
            this._setValue({
                operation: 'FORGET',
                ids: [record.id],
            });
            var metadata = this.metadata[record.id];
            if (!metadata || metadata.allowUnlink) {
                this._rpc({
                    model: 'ir.attachment',
                    method: 'unlink',
                    args: [record.res_id],
                });
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFileChanged: function (ev) {
        var self = this;
        ev.stopPropagation();

        var files = ev.target.files;
        var attachment_ids = this.value.res_ids;

        _.each(files, function (file) {
            var record = _.find(self.value.data, function (attachment) {
                return attachment.data.name === file.name;
            });
            if (record) {
                var metadata = self.metadata[record.id];
                if (!metadata || metadata.allowUnlink) {
                    // there is a existing attachment with the same name so we
                    // replace it
                    attachment_ids = _.without(attachment_ids, record.res_id);
                    self._rpc({
                        model: 'ir.attachment',
                        method: 'unlink',
                        args: [record.res_id],
                    });
                }
            }
            self.uploadingFiles.push(file);
        });

        this._setValue({
            operation: 'REPLACE_WITH',
            ids: attachment_ids,
        });

        this.$('form.o_form_binary_form').submit();
        this.$('.oe_fileupload').hide();
    },
    /**
     * @private
     */
    _onFileLoaded: function () {
        var self = this;
        // the first argument isn't a file but the jQuery.Event
        var files = Array.prototype.slice.call(arguments, 1);
        // files has been uploaded, clear uploading
        this.uploadingFiles = [];

        var attachment_ids = this.value.res_ids;
        _.each(files, function (file) {
            if (file.error) {
                self.do_warn(_t('Uploading Error'), file.error);
            } else {
                attachment_ids.push(file.id);
                self.uploadedFiles[file.id] = true;
            }
        });

        this._setValue({
            operation: 'REPLACE_WITH',
            ids: attachment_ids,
        });
    },
});

var FieldMany2ManyTags = AbstractField.extend({
    tag_template: "FieldMany2ManyTag",
    className: "o_field_many2manytags",
    supportedFieldTypes: ['many2many'],
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: _.extend({}, AbstractField.prototype.events, {
        'click .o_delete': '_onDeleteTag',
    }),
    fieldsToFetch: {
        display_name: {type: 'char'},
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        if (this.mode === 'edit') {
            this.className += ' o_input';
        }

        this.colorField = this.nodeOptions.color_field;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    activate: function () {
        return this.many2one ? this.many2one.activate() : false;
    },
    /**
     * @override
     * @returns {jQuery}
     */
    getFocusableElement: function () {
        return this.many2one ? this.many2one.getFocusableElement() : $();
    },
    /**
     * @override
     * @returns {boolean}
     */
    isSet: function () {
        return !!this.value && this.value.count;
    },
    /**
     * Reset the focus on this field if it was the origin of the onchange call.
     *
     * @override
     */
    reset: function (record, event) {
        this._super.apply(this, arguments);
        if (event && event.target === this) {
            this.activate();
        }
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
     * Get the QWeb rendering context used by the tag template; this computation
     * is placed in a separate function for other tags to override it.
     *
     * @private
     * @returns {Object}
     */
    _getRenderTagsContext: function () {
        var elements = this.value ? _.pluck(this.value.data, 'data') : [];
        return {
            colorField: this.colorField,
            elements: elements,
            readonly: this.mode === "readonly",
        };
    },
    /**
     * @private
     * @param {any} id
     */
    _removeTag: function (id) {
        var record = _.findWhere(this.value.data, {res_id: id});
        this._setValue({
            operation: 'FORGET',
            ids: [record.id],
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
            mode: 'edit',
            viewType: this.viewType,
        });
        // to prevent the M2O to take the value of the M2M
        this.many2one.value = false;
        // to prevent the M2O to take the relational values of the M2M
        this.many2one.m2o_value = '';

        this.many2one.nodeOptions.no_open = true;
        this.many2one._getSearchBlacklist = function () {
            return self.value.res_ids;
        };
        return this.many2one.appendTo(this.$el);
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
        this.$el.html(qweb.render(this.tag_template, this._getRenderTagsContext()));
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
     * Controls the changes made in the internal m2o field.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onFieldChanged: function (ev) {
        if (ev.target !== this.many2one) {
            return;
        }
        ev.stopPropagation();
        var newValue = ev.data.changes[this.name];
        if (newValue) {
            this._addTag(newValue);
            this.many2one.reinitialize(false);
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.BACKSPACE && this.$('input').val() === "") {
            var $badges = this.$('.badge');
            if ($badges.length) {
                this._removeTag($badges.last().data('id'));
                return;
            }
        }
        this._super.apply(this, arguments);
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
        'mousedown .o_colorpicker a': '_onUpdateColor',
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
        if (tag && this.colorField in tag.data) { // if there is a color field on the related model
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

        var changes = {};
        changes[this.colorField] = color;
        this.trigger_up('field_changed', {
            dataPointID: _.findWhere(this.value.data, {res_id: id}).id,
            changes: changes,
            force_save: true,
        });
    },
});

var KanbanFieldMany2ManyTags = FieldMany2ManyTags.extend({
    // Remove event handlers on this widget to ensure that the kanban 'global
    // click' opens the clicked record, even if the click is done on a tag
    // This is necessary because of the weird 'global click' logic in
    // KanbanRecord, which should definitely be cleaned.
    // Anyway, those handlers are only necessary in Form and List views, so we
    // can removed them here.
    events: AbstractField.prototype.events,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.$el.empty().addClass('o_field_many2manytags o_kanban_tags');
        _.each(this.value.data, function (m2m) {
            if (self.colorField in m2m.data && !m2m.data[self.colorField]) {
                // When a color field is specified and that color is the default
                // one, the kanban tag is not rendered.
                return;
            }

            $('<span>', {
                class: 'o_tag o_tag_color_' + (m2m.data[self.colorField] || 0),
                text: m2m.data.display_name,
            })
            .prepend('<span>')
            .appendTo(self.$el);
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
        _.each(this.value.res_ids, function (id) {
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
        var selections = _.partition(this.status_information, function (info) {
            return (info.selected || !info.fold);
        });
        this.$el.html(qweb.render("FieldStatus.content", {
            selection_unfolded: selections[0],
            selection_folded: selections[1],
            clickable: !!this.attrs.clickable,
        }));
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
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._setValues();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {jQuery}
     */
    getFocusableElement: function () {
        return this.$el.is('select') ? this.$el : $();
    },
    /**
     * @override
     */
    isSet: function () {
        return this.value !== false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$el.empty();
        for (var i = 0 ; i < this.values.length ; i++) {
            this.$el.append($('<option/>', {
                value: JSON.stringify(this.values[i][0]),
                text: this.values[i][1]
            }));
        }
        var value = this.value;
        if (this.field.type === 'many2one' && value) {
            value = value.data.id;
        }
        this.$el.val(JSON.stringify(value));
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.empty().text(this._formatValue(this.value));
    },
    /**
     * @override
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setValues();
    },
    /**
     * Sets the possible field values. If the field is a many2one, those values
     * may change during the lifecycle of the widget if the domain change (an
     * onchange may change the domain).
     *
     * @private
     */
    _setValues: function () {
        if (this.field.type === 'many2one') {
            this.values = this.record.specialData[this.name];
            this.formatType = 'many2one';
        } else {
            this.values = _.reject(this.field.selection, function (v) {
                return v[0] === false && v[1] === '';
            });
        }
        this.values = [[false, this.attrs.placeholder || '']].concat(this.values);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * The small slight difficulty is that we have to set the value differently
     * depending on the field type.
     *
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
    template: null,
    className: 'o_field_radio',
    tagName: 'span',
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
        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += this.nodeOptions.horizontal ? ' o_horizontal' : ' o_vertical';
        }
        this.unique_id = _.uniqueId("radio");
        this._setValues();
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
        var self = this;
        var currentValue;
        if (this.field.type === 'many2one') {
            currentValue = this.value && this.value.data.id;
        } else {
            currentValue = this.value;
        }
        this.$el.empty();
        _.each(this.values, function (value, index) {
            self.$el.append(qweb.render('FieldRadio.button', {
                checked: value[0] === currentValue,
                id: self.unique_id + '_' + value[0],
                index: index,
                value: value,
            }));
        });
    },
    /**
     * @override
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setValues();
    },
    /**
     * Sets the possible field values. If the field is a many2one, those values
     * may change during the lifecycle of the widget if the domain change (an
     * onchange may change the domain).
     *
     * @private
     */
    _setValues: function () {
        if (this.field.type === 'selection') {
            this.values = this.field.selection || [];
        } else if (this.field.type === 'many2one') {
            this.values = _.map(this.record.specialData[this.name], function (val) {
                return [val.id, val.display_name];
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onInputClick: function (event) {
        var index = $(event.target).data('index');
        var value = this.values[index];
        if (this.field.type === 'many2one') {
            this._setValue({id: value[0], display_name: value[1]});
        } else {
            this._setValue(value[0]);
        }
    },
});

/**
 * The FieldReference is a combination of a select (for the model) and
 * a FieldMany2one for its value.
 * Its intern representation is similar to the many2one (a datapoint with a
 * `name_get` as data).
 */
var FieldReference = FieldMany2One.extend({
    specialData: "_fetchSpecialReference",
    supportedFieldTypes: ['char', 'reference'],
    template: 'FieldReference',
    events: _.extend({}, FieldMany2One.prototype.events, {
        'change select': '_onSelectionChange',
    }),
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        // needs to be copied as it is an unmutable object
        this.field = _.extend({}, this.field);

        this._setState();
    },
    /**
     * @override
     */
    start: function () {
        this.$('select').val(this.field.relation);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the encompassing record's display_name
     *
     * @override
     */
    _formatValue: function () {
        var value;
        if (this.field.type === 'char') {
            value = this.record.specialData[this.name];
        } else {
            value = this.value;
        }
        return value && value.data && value.data.display_name || '';
    },

    /**
     * Add a select in edit mode (for the model).
     *
     * @override
     */
    _renderEdit: function () {
        this._super.apply(this, arguments);

        if (this.$('select').val()) {
            this.$('.o_input_dropdown').show();
            this.$el.addClass('o_row'); // this class is used to display the two
                                        // components (select & input) on the same line
        } else {
            // hide the many2one if the selection is empty
            this.$('.o_input_dropdown').hide();
        }

    },
    /**
     * @override
     * @private
     */
    _reset: function () {
        var value = this.$('select').val();
        this._setState();
        this._super.apply(this, arguments);
        this.$('select').val(this.value && this.value.model || value);
    },
    /**
     * Set `relation` key in field properties.
     *
     * @private
     * @param {string} model
     */
    _setRelation: function (model) {
        // used to generate the search in many2one
        this.field.relation = model;
    },
    /**
     * @private
     */
    _setState: function () {
        if (this.field.type === 'char') {
            // in this case, the value is stored in specialData instead
            this.value = this.record.specialData[this.name];
        }

        if (this.value) {
            this._setRelation(this.value.model);
        }
    },
    /**
     * @override
     * @private
     */
    _setValue: function (value, options) {
        value = value || {};
        // we need to specify the model for the change in basic_model
        // the value is then now a dict with id, display_name and model
        value.model = this.$('select').val();
        return this._super(value, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When the selection (model) changes, the many2one is reset.
     *
     * @private
     */
    _onSelectionChange: function () {
        var value = this.$('select').val();
        this.reinitialize(false);
        this._setRelation(value);
    },
});

return {
    FieldMany2One: FieldMany2One,
    KanbanFieldMany2One: KanbanFieldMany2One,
    ListFieldMany2One: ListFieldMany2One,

    FieldOne2Many: FieldOne2Many,

    FieldMany2Many: FieldMany2Many,
    FieldMany2ManyBinaryMultiFiles: FieldMany2ManyBinaryMultiFiles,
    FieldMany2ManyCheckBoxes: FieldMany2ManyCheckBoxes,
    FieldMany2ManyTags: FieldMany2ManyTags,
    FormFieldMany2ManyTags: FormFieldMany2ManyTags,
    KanbanFieldMany2ManyTags: KanbanFieldMany2ManyTags,

    FieldRadio: FieldRadio,
    FieldSelection: FieldSelection,
    FieldStatus: FieldStatus,

    FieldReference: FieldReference,
};

});
