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
const ControlPanelX2Many = require('web.ControlPanelX2Many');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var dialogs = require('web.view_dialogs');
var dom = require('web.dom');
const Domain = require('web.Domain');
var KanbanRecord = require('web.KanbanRecord');
var KanbanRenderer = require('web.KanbanRenderer');
var ListRenderer = require('web.ListRenderer');
const { ComponentWrapper, WidgetAdapterMixin } = require('web.OwlCompatibility');
const { sprintf, toBoolElse } = require("web.utils");
const { escape } = require("@web/core/utils/strings");

var _t = core._t;
var _lt = core._lt;
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
            title: _.str.sprintf(_t("New %s"), this.name),
            size: 'medium',
            buttons: [{
                text: _t('Create'),
                classes: 'btn-primary',
                close: true,
                click: function () {
                    this.trigger_up('quick_create', { value: this.value });
                },
            }, {
                text: _t('Discard'),
                close: true,
            }],
        });
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
    description: _lt("Many2one"),
    supportedFieldTypes: ['many2one'],
    template: 'FieldMany2One',
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        'closed_unset': '_onDialogClosedUnset',
        'field_changed': '_onFieldChanged',
        'quick_create': '_onQuickCreate',
    }),
    events: _.extend({}, AbstractField.prototype.events, {
        'click input': '_onInputClick',
        'click': '_onLinkClick',
        'focusout input': '_onInputFocusout',
        'keyup input': '_onInputKeyup',
        'click .o_external_button': '_onExternalButtonClick',
    }),
    quickEditExclusion: [
        '.o_form_uri',
    ],
    AUTOCOMPLETE_DELAY: 200,
    SEARCH_MORE_LIMIT: 320,
    isQuickEditable: true,

    /**
     * @override
     * @param {boolean} [options.noOpen=false] if true, there is no external
     *   button to open the related record in a dialog
     * @param {boolean} [options.noCreate=false] if true, the many2one does not
     *   allow to create records
     */
    init: function (parent, name, record, options) {
        options = options || {};
        this._super.apply(this, arguments);
        this.limit = 7;
        this.orderer = new concurrency.DropMisordered();

        // should normally be set, except in standalone M20
        const canCreate = 'can_create' in this.attrs ? JSON.parse(this.attrs.can_create) : true;
        this.can_create = canCreate && !this.nodeOptions.no_create && !options.noCreate;
        this.can_write = 'can_write' in this.attrs ? JSON.parse(this.attrs.can_write) : true;

        this.nodeOptions = _.defaults(this.nodeOptions, {
            quick_create: true,
        });
        this.noOpen = 'noOpen' in options ? options.noOpen : this.nodeOptions.no_open;
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

        // List of autocomplete sources
        this._autocompleteSources = [];
        // Add default search method for M20 (name_search)
        this._addAutocompleteSource(this._search, {placeholder: _t('Loading...'), order: 1});

        // list of last autocomplete suggestions
        this.suggestions = [];

        // flag used to prevent from selecting the highlighted item in the autocomplete
        // dropdown when the user leaves the many2one by pressing Tab (unless he
        // manually selected the item using UP/DOWN keys)
        this.ignoreTabSelect = false;

        // use a DropPrevious to properly handle related record quick creations,
        // and store a createDef to be able to notify the environment that there
        // is pending quick create operation
        this.dp = new concurrency.DropPrevious();
        this.createDef = undefined;
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
    /**
     * @override
     */
    destroy: function () {
        if (this._onScroll) {
            window.removeEventListener('scroll', this._onScroll, true);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to make the caller wait for potential ongoing record creation.
     * This ensures that the correct many2one value is set when the main record
     * is saved.
     *
     * @override
     * @returns {Promise} resolved as soon as there is no longer record being
     *   (quick) created
     */
    commitChanges: function () {
        return Promise.resolve(this.createDef);
    },
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
        return this._setValue(value);
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
            return Promise.resolve();
        } else {
            return this._render();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a source to the autocomplete results
     *
     * @param {function} method : A function that returns a list of results. If async source, the function should return a promise
     * @param {Object} params : Parameters containing placeholder/validation/order
     * @private
     */
    _addAutocompleteSource: function (method, params) {
        this._autocompleteSources.push({
            method: method,
            placeholder: (params.placeholder ? _t(params.placeholder) : _t('Loading...')) + '<i class="fa fa-spin fa-circle-o-notch float-end"></i>' ,
            validation: params.validation,
            loading: false,
            order: params.order || 999
        });

        this._autocompleteSources = _.sortBy(this._autocompleteSources, 'order');
    },
    /**
     * @private
     */
    _bindAutoComplete: function () {
        var self = this;
        // avoid ignoring autocomplete="off" by obfuscating placeholder, see #30439
        if ($.browser.chrome && this.$input.attr('placeholder')) {
            this.$input.attr('placeholder', function (index, val) {
                return val.split('').join('\ufeff');
            });
        }
        this.$input.autocomplete({
            source: function (req, resp) {
                self.suggestions = [];
                _.each(self._autocompleteSources, function (source) {
                    // Resets the results for this source
                    source.results = [];

                    // Check if this source should be used for the searched term
                    const search = req.term.trim();
                    if (!source.validation || source.validation.call(self, search)) {
                        source.loading = true;

                        // Wrap the returned value of the source.method with a promise
                        // So event if the returned value is not async, it will work
                        Promise.resolve(source.method.call(self, search)).then(function (results) {
                            source.results = results;
                            source.loading = false;
                            self.suggestions = self._concatenateAutocompleteResults();
                            resp(self.suggestions);
                        });
                    }
                });
            },
            select: function (event, ui) {
                // do not select anything if the input is empty and the user
                // presses Tab (except if he manually highlighted an item with
                // up/down keys)
                if (!self.floating && event.key === "Tab" && self.ignoreTabSelect) {
                    return false;
                }

                if (event.key === "Enter") {
                    // on Enter we do not want any additional effect, such as
                    // navigating to another field
                    event.stopImmediatePropagation();
                    event.preventDefault();
                }

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
                if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                    // the user manually selected an item by pressing up/down keys,
                    // so select this item if he presses tab later on
                    self.ignoreTabSelect = false;
                }
            },
            open: function (event) {
                self._onScroll = function (ev) {
                    if (ev.target !== self.$input.get(0) && self.$input.hasClass('ui-autocomplete-input')) {
                        if (ev.target.id === self.$input.autocomplete('widget').get(0).id) {
                            ev.stopPropagation();
                            return;
                        }
                        self.$input.autocomplete('close');
                    }
                };
                window.addEventListener('scroll', self._onScroll, true);
            },
            close: function (event) {
                self.ignoreTabSelect = false;
                // it is necessary to prevent ESC key from propagating to field
                // root, to prevent unwanted discard operations.
                if (event.which === $.ui.keyCode.ESCAPE) {
                    event.stopPropagation();
                }
                if (self._onScroll) {
                    window.removeEventListener('scroll', self._onScroll, true);
                }
            },
            autoFocus: true,
            html: true,
            minLength: 0,
            delay: this.AUTOCOMPLETE_DELAY,
            classes: {
                "ui-autocomplete": "dropdown-menu",
            },
            create: function() {
                $(this).data('ui-autocomplete')._renderMenu = function(ulWrapper, entries) {
                  var render = this;
                  $.each(entries, function(index, entry) {
                    render._renderItemData(ulWrapper, entry);
                  });
                  $(ulWrapper).find( "li > a" ).addClass( "dropdown-item" );
                }
            },
        });
        this.$input.autocomplete("option", "position", { my : "left top", at: "left bottom" });
        this.autocomplete_bound = true;
    },
    /**
     * Concatenate async results for autocomplete.
     *
     * @returns {Array}
     * @private
     */
    _concatenateAutocompleteResults: function () {
        var results = [];
        _.each(this._autocompleteSources, function (source) {
            if (source.results && source.results.length) {
                results = results.concat(source.results);
            } else if (source.loading) {
                results.push({
                    label: source.placeholder
                });
            }
        });
        return results;
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
     * @override
     */
    _quickEdit: function () {
        this._super(...arguments);
        this._toggleAutoComplete();
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
     * Prepares and returns options for SelectCreateDialog
     *
     * @private
     */
    _getSearchCreatePopupOptions: function(view, ids, context, dynamicFilters) {
        var self = this;
        return {
            res_model: this.field.relation,
            domain: this.record.getDomain({fieldName: this.name}),
            context: _.extend({}, this.record.getContext(this.recordParams), context || {}),
            _createContext: this._createContext.bind(this),
            dynamicFilters: dynamicFilters || [],
            title: _.str.sprintf((view === 'search' ? _t("Search: %s") : _t("Create: %s")), this.string),
            initial_ids: ids,
            initial_view: view,
            disable_multiple_selection: true,
            no_create: !self.can_create,
            kanban_view_ref: this.attrs.kanban_view_ref,
            on_selected: function (records) {
                self.reinitialize(records[0]);
            },
            on_closed: function () {
                self.activate();
            },
        };
    },
    /**
     * @private
     * @param {Object} values
     * @param {string} search_val
     * @param {Object} domain
     * @param {Object} context
     * @returns {Object}
     */
    _manageSearchMore: function (values, search_val, domain, context) {
        var self = this;
        values = values.slice(0, this.limit);
        values.push({
            label: _t("Search More..."),
            action: function () {
                var prom;
                if (search_val !== '') {
                    prom = self._rpc({
                        model: self.field.relation,
                        method: 'name_search',
                        kwargs: {
                            name: search_val,
                            args: domain,
                            operator: "ilike",
                            limit: self.SEARCH_MORE_LIMIT,
                            context: context,
                        },
                    });
                }
                Promise.resolve(prom).then(function (results) {
                    var dynamicFilters;
                    if (results) {
                        var ids = _.map(results, function (x) {
                            return x[0];
                        });
                        dynamicFilters = [{
                            description: _.str.sprintf(_t('Quick search: %s'), search_val),
                            domain: [['id', 'in', ids]],
                        }];
                    }
                    self._searchCreatePopup("search", false, {}, dynamicFilters);
                });
            },
            classname: 'o_m2o_dropdown_option',
        });
        return values;
    },
    /**
     * @private
     */
    _toggleAutoComplete: function () {
        if (this.$input.autocomplete("widget").is(":visible")) {
            this.$input.autocomplete("close");
        } else if (this.floating) {
            this.$input.autocomplete("search"); // search with the input's content
        } else {
            this.$input.autocomplete("search", ''); // search with the empty string
        }
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
     * @returns {Promise} resolved after the name_create or when the slowcreate
     *                     modal is closed.
     */
    _quickCreate: function (name) {
        var self = this;
        var createDone;

        var def = new Promise(function (resolve, reject) {
            self.createDef = new Promise(function (innerResolve) {
                // called when the record has been quick created, or when the dialog has
                // been closed (in the case of a 'slow' create), meaning that the job is
                // done
                createDone = function () {
                    innerResolve();
                    resolve();
                    self.createDef = undefined;
                };
            });

            // called if the quick create is disabled on this many2one, or if the
            // quick creation failed (probably because there are mandatory fields on
            // the model)
            var slowCreate = function () {
                var dialog = self._searchCreatePopup("form", false, self._createContext(name));
                dialog.on('closed', self, createDone);
            };
            if (self.nodeOptions.quick_create) {
                const prom = self.reinitialize({id: false, display_name: name});
                prom.guardedCatch(reason => {
                    reason.event.preventDefault();
                    slowCreate();
                });
                self.dp.add(prom).then(createDone).guardedCatch(reject);
            } else {
                slowCreate();
            }
        });

        return def;
    },
    /**
     * @private
     */
    _renderEdit: function () {
        var value = this.m2o_value;

        this.$('.o_field_many2one_extra').html(this._renderValueLines(false));

        // this is a stupid hack necessary to support the always_reload flag.
        // the field value has been reread by the basic model.  We use it to
        // display the full address of a partner, separated by \n.  This is
        // really a bad way to do it.  Now, we need to remove the extra lines
        // and hope for the best that no one tries to uses this mechanism to do
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
     * @param {boolean} needFirstLine
     * @returns {string} escaped html of value lines
     */
    _renderValueLines: function (needFirstLine) {
        const escapedValue = _.escape((this.m2o_value || "").trim());
        const lines = escapedValue.split('\n');
        if (!needFirstLine) {
            lines.shift();
        }
        return lines.map((line) => `<span>${line}</span>`).join('<br/>');
    },
    /**
     * @private
     */
    _renderReadonly: function () {
        this.$el.html(this._renderValueLines(true));
        if (!this.noOpen && this.value) {
            this.$el.attr('href', _.str.sprintf('#id=%s&model=%s', this.value.res_id, this.field.relation));
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
     * Executes a 'name_search' and returns a list of formatted objects meant to
     * be displayed in the autocomplete widget dropdown. These items are either:
     * - a formatted version of a 'name_search' result
     * - an option meant to display additional information or perform an action
     *
     * @private
     * @param {string} [searchValue=""]
     * @returns {Promise<{
     *      label: string,
     *      id?: number,
     *      name?: string,
     *      value?: string,
     *      classname?: string,
     *      action?: () => Promise<any>,
     * }[]>}
     */
    _search: async function (searchValue = "") {
        const value = searchValue.trim();
        const domain = this.record.getDomain(this.recordParams);
        const context = Object.assign(
            this.record.getContext(this.recordParams),
            this.additionalContext
        );

        // Exclude black-listed ids from the domain
        const blackListedIds = this._getSearchBlacklist();
        if (blackListedIds.length) {
            domain.push(['id', 'not in', blackListedIds]);
        }

        const nameSearch = this._rpc({
            model: this.field.relation,
            method: "name_search",
            kwargs: {
                name: value,
                args: domain,
                operator: "ilike",
                limit: this.limit + 1,
                context,
            }
        });
        const results = await this.orderer.add(nameSearch);

        // Format results to fit the options dropdown
        let values = results.map((result) => {
            const [id, fullName] = result;
            const displayName = this._getDisplayName(fullName).trim();
            result[1] = displayName;
            return {
                id,
                label: escape(displayName) || data.noDisplayContent,
                value: displayName,
                name: displayName,
            };
        });

        // Add "Search more..." option if results count is higher than the limit
        if (this.limit < values.length) {
            values = this._manageSearchMore(values, value, domain, context);
        }

        // Additional options...
        const canQuickCreate = this.can_create && !this.nodeOptions.no_quick_create;
        const canCreateEdit = this.can_create && !this.nodeOptions.no_create_edit;
        if (value.length) {
            // "Quick create" option
            const nameExists = results.some((result) => result[1] === value);
            if (canQuickCreate && !nameExists) {
                values.push({
                    label: sprintf(
                        _t(`Create "<strong>%s</strong>"`),
                        escape(value)
                    ),
                    action: () => this._quickCreate(value),
                    classname: 'o_m2o_dropdown_option'
                });
            }
            // "Create and Edit" option
            if (canCreateEdit) {
                const valueContext = this._createContext(value);
                values.push({
                    label: _t("Create and Edit..."),
                    action: () => {
                        // Input value is cleared and the form popup opens
                        this.el.querySelector(':scope input').value = "";
                        return this._searchCreatePopup('form', false, valueContext);
                    },
                    classname: 'o_m2o_dropdown_option',
                });
            }
            // "No results" option
            if (!values.length) {
                values.push({
                    label: _t("No records"),
                    classname: 'o_m2o_no_result',
                });
            }
        } else if (!this.value && (canQuickCreate || canCreateEdit)) {
            // "Start typing" option
            values.push({
                label: _t("Start typing..."),
                classname: 'o_m2o_start_typing',
            });
        }

        return values;
    },
    /**
     * all search/create popup handling
     *
     * TODO: ids argument is no longer used, remove it in master (as well as
     * initial_ids param of the dialog)
     *
     * @private
     * @param {any} view
     * @param {any} ids
     * @param {any} context
     * @param {Object[]} [dynamicFilters=[]] filters to add to the search view
     *   in the dialog (each filter has keys 'description' and 'domain')
     */
    _searchCreatePopup: function (view, ids, context, dynamicFilters) {
        var options = this._getSearchCreatePopupOptions(view, ids, context, dynamicFilters);
        return new dialogs.SelectCreateDialog(this, _.extend({}, this.nodeOptions, options)).open();
    },
    /**
     * @private
     */
    _updateExternalButton: function () {
        var has_external_button = !this.noOpen && !this.floating && this.isSet();
        this.$external_button.toggle(has_external_button);
        this.$el.toggleClass('o_with_button', has_external_button); // Should not be required anymore but kept for compatibility
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onLinkClick: function (event) {
        var self = this;
        if (this.mode === 'readonly') {
            event.preventDefault();
            if (!this.noOpen) {
                event.stopPropagation();
                this._rpc({
                    model: this.field.relation,
                    method: 'get_formview_action',
                    args: [[this.value.res_id]],
                    context: this.record.getContext(this.recordParams),
                }).then(function (action) {
                    self.trigger_up('do_action', {action: action});
                });
            }
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
                            const _setValue = self._setValue.bind(self, self.value.data, {
                                forceChange: true,
                            });
                            self.trigger_up('reload', {
                                db_id: self.value.id,
                                onSuccess: _setValue,
                                onFailure: _setValue,
                            });
                        }
                    },
                }).open();
            });
    },
    /**
     * @private
     */
    _onInputClick: function () {
        if (this.autocomplete_bound && !this.$input.autocomplete("widget").is(":visible")) {
            this.ignoreTabSelect = true;
        }
        this._toggleAutoComplete();
    },
    /**
     * @private
     */
    _onInputFocusout: function () {
        if (!this.floating) {
            return;
        }
        const firstValue = this.suggestions.find(s => s.id);
        if (firstValue) {
            this.reinitialize({ id: firstValue.id, display_name: firstValue.name });
        } else if (this.can_create) {
            new M2ODialog(this, this.string, this.$input.val()).open();
        } else {
            this.$input.val("");
        }
    },
    /**
     * @private
     *
     * @param {OdooEvent} ev
     */
    _onInputKeyup: function (ev) {
        const $autocomplete = this.$input.autocomplete("widget");
        // close autocomplete if no autocomplete item is selected and user presses TAB
        // s.t. we properly move to the next field in this case
        if (ev.which === $.ui.keyCode.TAB &&
                $autocomplete.is(":visible") &&
                !$autocomplete.find('.ui-menu-item .ui-state-active').length) {
            this.$input.autocomplete("close");
        }
        if (ev.which === $.ui.keyCode.ENTER || ev.which === $.ui.keyCode.TAB) {
            // If we pressed enter or tab, we want to prevent _onInputFocusout from
            // executing since it would open a M2O dialog to request
            // confirmation that the many2one is not properly set.
            // It's a case that is already handled by the autocomplete lib.
            return;
        }
        this.isDirty = true;
        if (this.$input.val() === "") {
            if (ev.key === "Backspace" || ev.key === "Delete") { // Backspace or Delete
                this.ignoreTabSelect = true;
            }
            this.reinitialize(false);
        } else if (this._getDisplayName(this.m2o_value) !== this.$input.val()) {
            this.floating = true;
            this._updateExternalButton();
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreate: function (event) {
        this._quickCreate(event.data.value);
    },
});

var Many2oneBarcode = FieldMany2One.extend({
    // We don't require this widget to be displayed in studio sidebar in
    // non-debug mode hence just extended it from its original widget, so that
    // description comes from parent and hasOwnProperty based condition fails
});

var ListFieldMany2One = FieldMany2One.extend({
    events: _.extend({}, FieldMany2One.prototype.events, {
        'focusin input': '_onInputFocusin',
    }),

    /**
     * Should never be allowed to be opened while in readonly mode in a list
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // when we empty the input, we delay the setValue to prevent from
        // triggering the 'fieldChanged' event twice when the user wants set
        // another m2o value ; the following attribute is used to determine when
        // we skipped the setValue, s.t. we can perform it later on if the user
        // didn't select another value
        this.mustSetValue = false;
        this.m2oDialogFocused = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * If in readonly, will never be considered as an active widget.
     *
     * @override
     */
    activate: function () {
        if (this.mode === 'readonly') {
            return false;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    reinitialize: function () {
        this.mustSetValue = false;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this.m2o_value);
    },
    /**
     * @override
     * @private
     */
    _searchCreatePopup: function () {
        this.m2oDialogFocused = true;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInputFocusin: function () {
        this.m2oDialogFocused = false;
    },
    /**
     * In case the focus is lost from a mousedown, we want to prevent the click occuring on the
     * following mouseup since it might trigger some unwanted list functions.
     * If it's not the case, we want to remove the added handler on the next mousedown.
     * @see list_editable_renderer._onWindowClicked()
     *
     * Also, in list views, we don't want to try to trigger a fieldChange when the field
     * is being emptied. Instead, it will be triggered as the user leaves the field
     * while it is empty.
     *
     * @override
     * @private
     */
    _onInputFocusout: function () {
        if (this.can_create && this.floating) {
            // In case the focus out is due to a mousedown, we want to prevent the next click
            var attachedEvents = ['click', 'mousedown'];
            var stopNextClick = (function (ev) {
                ev.stopPropagation();
                attachedEvents.forEach(function (eventName) {
                    window.removeEventListener(eventName, stopNextClick, true);
                });
            }).bind(this);
            attachedEvents.forEach(function (eventName) {
                window.addEventListener(eventName, stopNextClick, true);
            });
        }
        this._super.apply(this, arguments);
        if (!this.m2oDialogFocused && this.$input.val() === "" && this.mustSetValue) {
            this.reinitialize(false);
        }
    },
    /**
     * Prevents the triggering of an immediate _onFieldChanged when emptying the field.
     *
     * @override
     * @private
     */
    _onInputKeyup: function () {
        if (this.$input.val() !== "") {
            this._super.apply(this, arguments);
        } else {
            this.mustSetValue = true;
        }
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

/**
 * Widget Many2OneAvatar is only supported on many2one fields pointing to a
 * model which inherits from 'image.mixin'. In readonly, it displays the
 * record's image next to the display_name. In edit, it behaves exactly like a
 * regular many2one widget.
 */
const Many2OneAvatar = FieldMany2One.extend({
    _template: 'web.Many2OneAvatar',

    init() {
        this._super.apply(this, arguments);
        if (this.mode === 'readonly') {
            this.template = null;
            this.tagName = 'div';
            // disable the redirection to the related record on click, in readonly
            this.noOpen = true;
        }
    },
    start() {
        this.el.classList.add('o_field_many2one_avatar');
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds avatar image to before many2one value.
     *
     * @override
     */
    _render() {
        const m2oAvatar = qweb.render(this._template, {
            url: `/web/image/${this.field.relation}/${this.value.res_id}/avatar_128`,
            value: this.m2o_value,
            widget: this,
        });
        if (this.mode === 'edit') {
            this._super(...arguments);
            if (this.el.querySelector('.o_m2o_avatar')) {
                this.el.querySelector('.o_m2o_avatar').remove();
            }
            dom.prepend(this.$('.o_field_many2one_selection'), m2oAvatar);
        }
        if (this.mode === 'readonly') {
            this.$el.empty();
            dom.append(this.$el, m2oAvatar);
        }
    },
});

//------------------------------------------------------------------------------
// X2Many widgets
//------------------------------------------------------------------------------

var FieldX2Many = AbstractField.extend(WidgetAdapterMixin, {
    tagName: 'div',
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        add_record: '_onAddRecord',
        discard_changes: '_onDiscardChanges',
        edit_line: '_onEditLine',
        field_changed: '_onFieldChanged',
        open_record: '_onOpenRecord',
        kanban_record_delete: '_onRemoveRecord',
        list_record_remove: '_onRemoveRecord',
        resequence_records: '_onResequenceRecords',
        save_line: '_onSaveLine',
        toggle_column_order: '_onToggleColumnOrder',
        activate_next_widget: '_onActiveNextWidget',
        navigation_move: '_onNavigationMove',
        save_optional_fields: '_onSaveOrLoadOptionalFields',
        load_optional_fields: '_onSaveOrLoadOptionalFields',
    }),

    // We need to trigger the reset on every changes to be aware of the parent changes
    // and then evaluate the 'column_invisible' modifier in case a evaluated value
    // changed.
    resetOnAnyFieldChange: true,

    /**
     * useSubview is used in form view to load view of the related model of the x2many field
     */
    useSubview: true,
    isQuickEditable: true,
    quickEditExclusion: [
        '.o_x2m_control_panel',
        'thead',
        '.o_widget',
    ],

    /**
     * @override
     */
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.createText = this.attrs['add-label'] || _t('Add');
        this.operations = [];
        this.isReadonly = this.mode === 'readonly';
        this.view = this.attrs.views[this.attrs.mode];
        this.isMany2Many = this.field.type === 'many2many' || this.attrs.widget === 'many2many';
        this.activeActions = {};
        this.recordParams = {fieldName: this.name, viewType: this.viewType};
        // The limit is fixed so it cannot be changed by adding/removing lines in
        // the widget. It will only change through a hard reload or when manually
        // changing the pager (see _onPagerChanged).
        this.pagingState = {
            currentMinimum: this.value.offset + 1,
            limit: this.value.limit,
            size: this.value.count,
            validate: () => {
                // TODO: we should have some common method in the basic renderer...
                return this.view.arch.tag === 'tree' ?
                    this.renderer.unselectRow() :
                    Promise.resolve();
            },
            withAccessKey: false,
            onPagerChanged: this._onPagerChanged.bind(this),
        };
        var arch = this.view && this.view.arch;
        if (arch) {
            this.activeActions.create = arch.attrs.create ?
                                            !!JSON.parse(arch.attrs.create) :
                                            true;
            this.activeActions.delete = arch.attrs.delete ?
                                            !!JSON.parse(arch.attrs.delete) :
                                            true;
            this.editable = arch.attrs.editable;
            this._canQuickEdit = arch.tag === 'tree';
        } else {
            this._canQuickEdit = false;
        }
        this._computeAvailableActions(record);
        if (this.attrs.columnInvisibleFields) {
            this._processColumnInvisibleFields();
        }
    },
    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        if (this.view) {
            this._renderButtons();
            this._controlPanelWrapper = new ComponentWrapper(this,
                this._getControlPanelComponent(),
                this._getControlPanelContext(),
            );
            await this._controlPanelWrapper.mount(this.el, { position: 'first-child' });
        }
        return _super(...arguments);
    },
    destroy: function () {
        WidgetAdapterMixin.destroy.call(this);
        this._super();
    },
    /**
     * For the list renderer to properly work, it must know if it is in the DOM,
     * and be notified when it is attached to the DOM.
     */
    on_attach_callback: function () {
        this.isInDOM = true;
        WidgetAdapterMixin.on_attach_callback.call(this);
        if (this.renderer) {
            this.renderer.on_attach_callback();
        }
    },
    /**
     * For the list renderer to properly work, it must know if it is in the DOM.
     */
    on_detach_callback: function () {
        this.isInDOM = false;
        WidgetAdapterMixin.on_detach_callback.call(this);
        if (this.renderer) {
            this.renderer.on_detach_callback();
        }
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
     * @returns {Promise}
     */
    commitChanges: function () {
        var self = this;
        var inEditionRecordID =
            this.renderer &&
            this.renderer.viewType === "list" &&
            this.renderer.getEditableRecordID();
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
     * @returns {Promise}
     */
    reset: function (record, ev, fieldChanged) {
        // re-evaluate available actions
        const oldCanCreate = this.canCreate;
        const oldCanDelete = this.canDelete;
        const oldCanLink = this.canLink;
        const oldCanUnlink = this.canUnlink;
        this._computeAvailableActions(record);
        const actionsChanged =
            this.canCreate !== oldCanCreate ||
            this.canDelete !== oldCanDelete ||
            this.canLink !== oldCanLink ||
            this.canUnlink !== oldCanUnlink;

        // If 'fieldChanged' is false, it means that the reset was triggered by
        // the 'resetOnAnyFieldChange' mechanism. If it is the case, if neither
        // the modifiers (so the visible columns) nor the available actions
        // changed, the reset is skipped.
        if (!fieldChanged && !actionsChanged) {
            var newEval = this._evalColumnInvisibleFields();
            if (_.isEqual(this.currentColInvisibleFields, newEval)) {
                this._reset(record, ev); // update the internal state, but do not re-render
                return Promise.resolve();
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
            if (command && command.operation === 'UPDATE' && command.data) {
                var state = record.data[this.name];
                var fieldNames = state.getFieldNames({ viewType: 'list' });
                this._reset(record, ev);
                return this.renderer.confirmUpdate(state, command.id, fieldNames, ev.initialEvent);
            }
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     * @returns {jQuery}
     */
    getFocusableElement: function () {
       return (this.mode === 'edit' && this.$input) || this.$el;
    },

    /**
     * @override
     * @param {Object|undefined} [options={}]
     * @param {boolean} [options.noAutomaticCreate=false]
     */
    activate: function (options) {
        if (!this.activeActions.create || this.isReadonly || !this.$el.is(":visible")) {
            return false;
        }
        if (this.view.type === 'kanban') {
            this.$buttons.find(".o-kanban-button-new").focus();
        }
        if (this.view.arch.tag === 'tree') {
            if (options && options.noAutomaticCreate) {
                this.renderer.$('.o_field_x2many_list_row_add a:first').focus();
            } else {
                this.renderer.$('.o_field_x2many_list_row_add a:first').click();
            }
        }
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} record
     */
    _computeAvailableActions: function (record) {
        const evalContext = record.evalContext;
        this.canCreate = 'create' in this.nodeOptions ?
            new Domain(this.nodeOptions.create, evalContext).compute(evalContext) :
            true;
        this.canDelete = 'delete' in this.nodeOptions ?
            new Domain(this.nodeOptions.delete, evalContext).compute(evalContext) :
            true;
        this.canLink = 'link' in this.nodeOptions ?
            new Domain(this.nodeOptions.link, evalContext).compute(evalContext) :
            true;
        this.canUnlink = 'unlink' in this.nodeOptions ?
            new Domain(this.nodeOptions.unlink, evalContext).compute(evalContext) :
            true;
    },
    /**
     * @private
     * @override
     * @param {Object} extraInfo
     * @param {string} [extraInfo.type]
     * @param {string} [extraInfo.row]
     * @param {string} [extraInfo.subFieldName]
     * @param {number} [extraInfo.recordId]
     */
    _quickEdit: function (extraInfo) {
        if (extraInfo.type === 'remove') {
            this._removeRecord(extraInfo.recordId);
        } else if (extraInfo.type === 'edit') {
            const parts = [];
            if (extraInfo.row) {
                parts.push(`.o_data_row[data-id="${extraInfo.row}"]`);
            }
            if (extraInfo.subFieldName) {
                parts.push(`[name="${extraInfo.subFieldName}"]`);
            }

            if (parts.length) {
                const el = this.el.querySelector(parts.join(' '));
                if (el) {
                    el.click();
                }
            }
        }
    },
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
     * Returns qweb context to render buttons.
     *
     * @private
     * @returns {Object}
     */
    _getButtonsRenderingContext() {
        return {
            btnClass: 'btn-secondary',
            create_text: this.createText,
        };
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} ev
     * @returns {Object}
     */
    _getQuickEditExtraInfo: function (ev) {
        const row = ev.target.closest('.o_data_row');
        const field = ev.target.closest('.o_data_row .o_field_widget') ||
            ev.target.closest('.o_field_cell');

        return {
            type: 'edit',
            row: row && row.dataset.id,
            subFieldName: row && field && field.getAttribute('name'),
        };
    },
    /**
     * Computes the default renderer to use depending on the view type.
     * We create this as a method so we can override it if we want to use
     * another renderer instead (eg. section_and_note_one2many).
     *
     * @private
     * @returns {Object} The renderer to use
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return ListRenderer;
        }
        if (this.view.arch.tag === 'kanban') {
            return KanbanRenderer;
        }
    },
    /**
     * Provides a way to override the control panel component to be used.
     *
     * @private
     * @returns {Component} The component to use.
     */
    _getControlPanelComponent: function () {
        return ControlPanelX2Many;
    },
    /**
     * @private
     * @returns {Object} The context that will be passed to the control panel.
     */
    _getControlPanelContext: function () {
        return {
            cp_content: { $buttons: this.$buttons },
            pager: this.pagingState,
        };
    },
    /**
     * @private
     * @returns {boolean} true iff the list should contain a 'create' line.
     */
    _hasCreateLine: function () {
        return !this.hasReadonlyModifier && (
            (!this.isMany2Many && this.activeActions.create && this.canCreate) ||
            (this.isMany2Many && this.canLink)
        );
    },
    /**
     * @private
     * @returns {boolean} true iff the list should add a trash icon on each row.
     */
    _hasTrashIcon: function () {
        return !this.hasReadonlyModifier && (
            (!this.isMany2Many && this.activeActions.delete && this.canDelete) ||
            (this.isMany2Many && this.canUnlink)
        );
    },
    /**
     * Removes the given record from the relation.
     *
     * @private
     * @param {number} recordId
     */
    _removeRecord: function (recordId) {
        this._setValue({
            operation: this.isMany2Many ? 'FORGET' : 'DELETE',
            ids: [recordId],
        });
    },
    /**
     * Instanciates or updates the adequate renderer.
     *
     * @override
     * @private
     * @returns {Promise|undefined}
     */
    _render: function () {
        var self = this;
        if (!this.view) {
            return this._super();
        }

        if (this.renderer) {
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            return this.renderer.updateState(this.value, {
                addCreateLine: this._hasCreateLine(),
                addTrashIcon: this._hasTrashIcon(),
                columnInvisibleFields: this.currentColInvisibleFields,
                keepWidths: true,
            }).then(() => {
                return this._updateControlPanel({ size: this.value.count });
            });
        }
        var arch = this.view.arch;
        var viewType;
        var rendererParams = {
            arch: arch,
        };

        if (arch.tag === 'tree') {
            viewType = 'list';
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            _.extend(rendererParams, {
                editable: this.mode === 'edit' && arch.attrs.editable,
                addCreateLine: this._hasCreateLine(),
                addTrashIcon: this._hasTrashIcon(),
                isMany2Many: this.isMany2Many,
                no_open: ((this.isReadonly && !this.hasReadonlyModifier) &&
                    this._canQuickEdit) || toBoolElse(arch.attrs.no_open || '', false),
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
            if (('action' in arch.attrs) && ('type' in arch.attrs)) {
                record_options.openAction = {
                    action: arch.attrs.action,
                    type: arch.attrs.type
                };
            }
            _.extend(rendererParams, {
                record_options: record_options,
                readOnlyMode: this.isReadonly,
            });
        }

        _.extend(rendererParams, {
            viewType: viewType,
        });
        var Renderer = this._getRenderer();
        this.renderer = new Renderer(this, this.value, rendererParams);

        this.$el.addClass('o_field_x2many o_field_x2many_' + viewType);
        if (this.renderer) {
            return this.renderer.appendTo(document.createDocumentFragment()).then(function () {
                dom.append(self.$el, self.renderer.$el, {
                    in_DOM: self.isInDOM,
                    callbacks: [{widget: self.renderer}],
                });
            });
        } else {
            return this._super();
        }
    },
    /**
     * Renders the buttons and sets this.$buttons.
     *
     * @private
     */
    _renderButtons: function () {
        if (!this.isReadonly && this.view.arch.tag === 'kanban') {
            const renderingContext = this._getButtonsRenderingContext();
            this.$buttons = $(qweb.render('KanbanView.buttons', renderingContext));
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
     * @returns {Promise} resolved if the line was properly saved or discarded.
     *                     rejected if the line could not be saved and the user
     *                     did not agree to discard.
     */
    _saveLine: function (recordID) {
        var self = this;
        return new Promise(function (resolve, reject) {
            var fieldNames = self.renderer.canBeSaved(recordID);
            if (fieldNames.length) {
                self.trigger_up('discard_changes', {
                    recordID: recordID,
                    onSuccess: resolve,
                    onFailure: reject,
                });
            } else {
                self.renderer.setRowMode(recordID, 'readonly').then(resolve);
            }
        }).then(async function () {
            self._updateControlPanel({ size: self.value.count });
            var newEval = self._evalColumnInvisibleFields();
            if (!_.isEqual(self.currentColInvisibleFields, newEval)) {
                self.currentColInvisibleFields = newEval;
                self.renderer.updateState(self.value, {
                    columnInvisibleFields: self.currentColInvisibleFields,
                });
            }
        });
    },
    /**
     * Re-renders buttons and updates the control panel. This method is called
     * when the widget is reset, as the available buttons might have changed.
     * The only mutable element in X2Many fields will be the pager.
     *
     * @private
     */
    _updateControlPanel: function (pagingState) {
        if (this._controlPanelWrapper) {
            this._renderButtons();
            const pagerProps = Object.assign(this.pagingState, pagingState, {
                // sometimes, we temporarily want to increase the pager limit
                // (for instance, when we add a new record on a page that already
                // contains the maximum number of records)
                limit: Math.max(this.value.limit, this.value.data.length),
            });
            const newProps = {
                cp_content: { $buttons: this.$buttons },
                pager: pagerProps,
            };
            return this._controlPanelWrapper.update(newProps);
        }
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
     * Called when the user clicks on the 'Add a line' link (list case) or the
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
    _onRemoveRecord: function (ev) {
        ev.stopPropagation();
        if (this._canQuickEdit && this.isReadonly) {
            this.trigger_up('quick_edit', {
                fieldName: this.name,
                target: this.el,
                extraInfo: {
                    type: 'remove',
                    recordId: ev.data.id,
                },
            });
        } else {
            this._removeRecord(ev.data.id);
        }
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
        if (ev.target !== this) {
            ev.stopPropagation();
            this.trigger_up('discard_changes', _.extend({}, ev.data, {fieldName: this.name}));
        }
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
        this.trigger_up('edited_list', { id: this.value.id });
        this.renderer.setRowMode(ev.data.recordId, 'edit')
            .then(ev.data.onSuccess);
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
            }).then(function () {
                if (ev.data.onSuccess) {
                    ev.data.onSuccess();
                }
            }).guardedCatch(function (reason) {
                if (ev.data.onFailure) {
                    ev.data.onFailure(reason);
                }
            });
        }
    },
    /**
     * Override to handle the navigation inside editable list controls
     *
     * @override
     * @private
     */
    _onNavigationMove: function (ev) {
        if (this.view.arch.tag === 'tree') {
            var $curControl = this.renderer.$('.o_field_x2many_list_row_add a:focus');
            if ($curControl.length) {
                var $nextControl;
                if (ev.data.direction === 'right') {
                    $nextControl = $curControl.next('a');
                } else if (ev.data.direction === 'left') {
                    $nextControl = $curControl.prev('a');
                }
                if ($nextControl && $nextControl.length) {
                    ev.stopPropagation();
                    $nextControl.focus();
                    return;
                }
            }
        }
        this._super.apply(this, arguments);
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
     * We re-render the pager immediately with the new event values to allow
     * it to request another pager change while another one is still ongoing.
     * @see field_manager_mixin for concurrency handling.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPagerChanged: function ({ currentMinimum, limit }) {
        this._updateControlPanel({ currentMinimum, limit });
        this.trigger_up('load', {
            id: this.value.id,
            limit,
            offset: currentMinimum - 1,
            on_success: value => {
                this.value = value;
                this.pagingState.limit = value.limit;
                this.pagingState.size = value.count;
                this._render();
            },
        });
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
        this.renderer.commitChanges(ev.data.recordID).then(function () {
            self.trigger_up('mutexify', {
                action: function () {
                    return self._saveLine(ev.data.recordID)
                        .then(ev.data.onSuccess)
                        .guardedCatch(ev.data.onFailure);
                },
            });
        });
    },
    /**
     * Add necessary key parts for the basic controller to compute the local
     * storage key. The event will be properly handled by the basic controller.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onSaveOrLoadOptionalFields: function (ev) {
        ev.data.keyParts.relationalField = this.name;
        ev.data.keyParts.subViewId = this.view.view_id;
        ev.data.keyParts.subViewType = this.view.type;
    },
    /**
     * Forces a resequencing of the records.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string[]} ev.data.recordIds
     * @param {integer} ev.data.offset
     * @param {string} ev.data.handleField
     */
    _onResequenceRecords: function (ev) {
        ev.stopPropagation();
        var self = this;
        if (this.view.arch.tag === 'tree') {
            this.trigger_up('edited_list', { id: this.value.id });
        }
        var handleField = ev.data.handleField;
        var offset = ev.data.offset;
        var recordIds = ev.data.recordIds.slice();
        // trigger an update of all records but the last one with option
        // 'notifyChanges' set to false, and once all those changes have been
        // validated by the model, trigger the change on the last record
        // (without the option, s.t. the potential onchange on parent record
        // is triggered)
        var recordId = recordIds.pop();
        var proms = recordIds.map(function (recordId, index) {
            var data = {};
            data[handleField] = offset + index;
            return self._setValue({
                operation: 'UPDATE',
                id: recordId,
                data: data,
            }, {
                notifyChange: false,
            });
        });
        Promise.all(proms).then(function () {
            function always() {
                if (self.view.arch.tag === 'tree') {
                    self.trigger_up('toggle_column_order', {
                        id: self.value.id,
                        name: handleField,
                    });
                }
            }
            var data = {};
            data[handleField] = offset + recordIds.length;
            self._setValue({
                operation: 'UPDATE',
                id: recordId,
                data: data,
            }).then(always).guardedCatch(always);
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
    /*
    * Move to next widget.
    *
    * @private
    */
    _onActiveNextWidget: function (e) {
        e.stopPropagation();
        this.renderer.unselectRow();
        this.trigger_up('navigation_move', {
            direction: e.data.direction || 'next',
        });
    },
});

var One2ManyKanbanRecord = KanbanRecord.extend({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply same logic as in the ListRenderer: buttons with type="object"
     * are disabled for no saved yet records, as calling the python method
     * with no id would make no sense.
     *
     * To avoid to expose this logic inside all Kanban views, we define
     * a specific KanbanRecord Class for the One2many case.
     *
     * This could be refactored to prevent from duplicating this logic in
     * list and kanban views.
     *
     * @private
     */
    _postProcessObjectButtons: function () {
        var self = this;
        // if the res_id is defined, it's already correctly handled by the Kanban record global event click
        if (!this.state.res_id) {
            this.$('.oe_kanban_action[data-type=object]').each(function (index, button) {
                var $button = $(button);
                if ($button.attr('warn')) {
                    $button.on('click', function (e) {
                        e.stopPropagation();
                        self.displayNotification({ message: _t('Please click on the "save" button first'), type: 'danger' });
                    });
                } else {
                    $button.attr('disabled', 'disabled');
                }
            });
        }
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._postProcessObjectButtons();
        });
    },
});

var One2ManyKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: One2ManyKanbanRecord,
    }),
});

var FieldOne2Many = FieldX2Many.extend({
    description: _lt("One2many"),
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
     * @returns {Promise}
     */
    reset: function (record, ev) {
        var self = this;
        return this._super.apply(this, arguments).then(() => {
            if (ev && ev.target === self && ev.data.changes && self.view.arch.tag === 'tree') {
                if (ev.data.changes[self.name] && ev.data.changes[self.name].operation === 'CREATE') {
                    var index = 0;
                    if (self.editable !== 'top') {
                        index = self.value.data.length - 1;
                    }
                    var newID = self.value.data[index].id;
                    return self.renderer.editRecord(newID);
                }
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {*} data
     */
    _addCreateRecordRow(data) {
        const self = this;
        if (this.editable || data.forceEditable) {
            if (!this.activeActions.create) {
                if (data.onFail) {
                    data.onFail();
                }
            } else if (!this.creatingRecord) {
                this.creatingRecord = true;
                this.trigger_up('edited_list', { id: this.value.id });
                this._setValue({
                    operation: 'CREATE',
                    position: this.editable || data.forceEditable,
                    context: data.context,
                }, {
                    allowWarning: data.allowWarning
                }).then(function () {
                    self.creatingRecord = false;
                }).then(function (){
                    if (data.onSuccess){
                        data.onSuccess();
                    }
                }).guardedCatch(function() {
                    self.creatingRecord = false;
                });
            }
        } else {
            this._openFormDialog({
                context: data.context && data.context[0],
                disable_multiple_selection: data.disable_multiple_selection,
                on_saved: function (record) {
                    self._setValue({ operation: 'ADD', id: record.id });
                },
            });
        }
    },
    /**
     * @private
     * @override
     * @param {Object} extraInfo
     * @param {string} [extraInfo.type]
     * @param {Object} [extraInfo.data]
     */
    _quickEdit: function (extraInfo) {
        if (extraInfo.type === 'add') {
            this._addCreateRecordRow(extraInfo.data);
        } else {
            this._super(...arguments);
        }
    },
    /**
     * @override
     * @private
     */
    _getButtonsRenderingContext() {
        const renderingContext = this._super(...arguments);
        renderingContext.noCreate = !this.canCreate;
        return renderingContext;
    },
    /**
      * @override
      * @private
      */
    _getRenderer: function () {
        if (this.view.arch.tag === 'kanban') {
            return One2ManyKanbanRenderer;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to only render the buttons if the 'create' action is available.
     *
     * @override
     * @private
     */
    _renderButtons: function () {
        if (this.activeActions.create) {
            return this._super(...arguments);
        }
    },
    /**
     * Trigger the event to open a dialog containing the corresponding Form view for the current record.
     * If the options 'no_open' is specified, the dialog will not be opened.
     *
     * @private
     * @param {Object} params
     * @param {Object} [params.context] We allow additional context, this is
     *   used for example to define default values when adding new lines to
     *   a one2many with control/create tags.
     */
    _openFormDialog: function (params) {
        var context = this.record.getContext(_.extend({},
            this.recordParams,
            { additionalContext: params.context }
        ));

        if (this.nodeOptions.no_open) {
            return;
        }

        this.trigger_up('open_one2many_record', _.extend(params, {
            domain: this.record.getDomain(this.recordParams),
            context: context,
            field: this.field,
            fields_view: this.attrs.views && this.attrs.views.form,
            parentID: this.value.id,
            viewInfo: this.view,
            deletable: this.activeActions.delete && params.deletable && this.canDelete,
            editable: !this.hasReadonlyModifier,
            disable_multiple_selection: params.disable_multiple_selection,
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
     * @param {Array} ev.data.context additional context for the added records,
     *   if several contexts are provided, multiple records will be added
     *   (form dialog will only use the context at index 0 if provided)
     * @param {boolean} ev.data.forceEditable this is used to bypass the dialog opening
     *   in case you want to add record(s) to a list
     * @param {function} ev.data.onSuccess called when the records are correctly created
     *   (not supported by form dialog)
     * @param {boolean} ev.data.allowWarning defines if the records can be added
     *   to the list even if warnings are triggered (e.g: stock warning for product availability)
     */
    _onAddRecord: function (ev) {
        const data = ev.data || {};

        // we don't want interference with the components upstream.
        ev.stopPropagation();

        if (this._canQuickEdit && this.isReadonly) {
            this.trigger_up('quick_edit', {
                fieldName: this.name,
                target: this.el,
                extraInfo: { type: 'add', data },
            });
        } else {
            this._addCreateRecordRow(data);
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
        var self = this;
        ev.stopPropagation();

        var id = ev.data.id;
        var onSaved = function (record) {
            if (_.some(self.value.data, {id: record.id})) {
                // the record already exists in the relation, so trigger an
                // empty 'UPDATE' operation when the user clicks on 'Save' in
                // the dialog, to notify the main record that a subrecord of
                // this relational field has changed (those changes will be
                // already stored on that subrecord, thanks to the 'Save').
                self._setValue({ operation: 'UPDATE', id: record.id });
            } else {
                // the record isn't in the relation yet, so add it ; this can
                // happen if the user clicks on 'Save & New' in the dialog (the
                // opened record will be updated, and other records will be
                // created)
                self._setValue({ operation: 'ADD', id: record.id });
            }
        };
        this._openFormDialog({
            id: id,
            on_saved: onSaved,
            on_remove: function () {
                self._setValue({operation: 'DELETE', ids: [id]});
            },
            deletable: this.activeActions.delete && this.view.arch.tag !== 'tree' && this.canDelete,
            readonly: this.mode === 'readonly',
        });
    },
});

var FieldMany2Many = FieldX2Many.extend({
    description: _lt("Many2many"),
    className: 'o_field_many2many',
    supportedFieldTypes: ['many2many'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Opens a SelectCreateDialog
     */
    onAddRecordOpenDialog: function () {
        var self = this;
        var domain = this.record.getDomain({fieldName: this.name});

        new dialogs.SelectCreateDialog(this, {
            res_model: this.field.relation,
            domain: domain.concat(["!", ["id", "in", this.value.res_ids]]),
            context: this.record.getContext(this.recordParams),
            title: _t("Add: ") + this.string,
            no_create: this.nodeOptions.no_create || !this.activeActions.create || !this.canCreate,
            fields_view: this.attrs.views.form,
            kanban_view_ref: this.attrs.kanban_view_ref,
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getButtonsRenderingContext() {
        const renderingContext = this._super(...arguments);
        renderingContext.noCreate = !this.canLink;
        return renderingContext;
    },
    /**
     * @private
     * @override
     * @param {Object} extraInfo
     * @param {string} [extraInfo.type]
     */
    _quickEdit: function (extraInfo) {
        if (extraInfo.type === 'add') {
            this.onAddRecordOpenDialog();
        } else {
            this._super(...arguments);
        }
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
        ev.stopPropagation();

        if (this._canQuickEdit && this.isReadonly) {
            this.trigger_up('quick_edit', {
                fieldName: this.name,
                target: this.el,
                extraInfo: { type: 'add' },
            });
        } else {
            this.onAddRecordOpenDialog();
        }
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
                self._setValue({operation: 'TRIGGER_ONCHANGE'}, {forceChange: true})
                    .then(function () {
                        self.trigger_up('reload', {db_id: ev.data.id});
                    });
            },
            on_remove: function () {
                self._setValue({operation: 'FORGET', ids: [ev.data.id]});
            },
            readonly: this.mode === 'readonly',
            deletable: this.activeActions.delete && this.view.arch.tag !== 'tree' && this.canDelete,
            string: this.string,
        });
    },
});

/**
 * Widget to upload or delete one or more files at the same time.
 */
var FieldMany2ManyBinaryMultiFiles = AbstractField.extend({
    template: "FieldBinaryFileUploader",
    template_files: "FieldBinaryFileUploader.files",
    supportedFieldTypes: ['many2many'],
    fieldsToFetch: {
        name: {type: 'char'},
        mimetype: {type: 'char'},
    },
    events: {
        'click .o_attach': '_onAttach',
        'click .o_attachment_delete': '_onDelete',
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
        this.accepted_file_extensions = (this.nodeOptions && this.nodeOptions.accepted_file_extensions) || this.accepted_file_extensions || '*';
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
        this.$('.oe_placeholder_files, .o_attachments')
            .replaceWith($(qweb.render(this.template_files, {
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

        // Don't create an attachment if the upload window is cancelled.
        if(files.length === 0)
            return;

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
        ev.target.value = "";
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
                self.displayNotification({ title: _t('Uploading Error'), message: file.error, type: 'danger' });
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
    description: _lt("Tags"),
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
    limit: 1000,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        if (this.mode === 'edit') {
            this.className += ' o_input';
        }

        this.colorField = this.nodeOptions.color_field;
        this.hasDropdown = false;

        this._computeAvailableActions(this.record);
        // have listen to react to other fields changes to re-evaluate 'create' option
        this.resetOnAnyFieldChange = this.resetOnAnyFieldChange || 'create' in this.nodeOptions;
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
        var self = this;
        this._computeAvailableActions(record);
        return this._super.apply(this, arguments).then(function () {
            if (event && event.target === self) {
                self.activate();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} data
     * @returns {Promise}
     */
    _addTag: function (data) {
        if (!_.contains(this.value.res_ids, data.id)) {
            return this._setValue({
                operation: 'ADD_M2M',
                ids: data
            });
        }
        return Promise.resolve();
    },
    /**
     * @private
     * @param {Object} record
     */
    _computeAvailableActions: function (record) {
        const evalContext = record.evalContext;
        this.canCreate = 'create' in this.nodeOptions ?
            new Domain(this.nodeOptions.create, evalContext).compute(evalContext) :
            true;
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
            hasDropdown: this.hasDropdown,
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
            noOpen: true,
            noCreate: !this.canCreate,
            viewType: this.viewType,
            attrs: this.attrs,
        });
        // to prevent the M2O to take the value of the M2M
        this.many2one.value = false;
        // to prevent the M2O to take the relational values of the M2M
        this.many2one.m2o_value = '';

        this.many2one._getSearchBlacklist = function () {
            return self.value.res_ids;
        };
        var _getSearchCreatePopupOptions = this.many2one._getSearchCreatePopupOptions;
        this.many2one._getSearchCreatePopupOptions = function (view, ids, context, dynamicFilters) {
            var options = _getSearchCreatePopupOptions.apply(this, arguments);
            var domain = this.record.getDomain({fieldName: this.name});
            var m2mRecords = [];
            return _.extend({}, options, {
                domain: domain.concat(["!", ["id", "in", self.value.res_ids]]),
                disable_multiple_selection: false,
                on_selected: function (records) {
                    m2mRecords.push(...records);
                },
                on_closed: function () {
                    self.many2one.reinitialize(m2mRecords);
                },
            });
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
        event.preventDefault();
        event.stopPropagation();
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
            this._addTag(newValue)
                .then(ev.data.onSuccess || function () {})
                .guardedCatch(ev.data.onFailure || function () {});
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

var FieldMany2ManyTagsAvatar = FieldMany2ManyTags.extend({
    tag_template: 'FieldMany2ManyTagAvatar',
    className: 'o_field_many2manytags avatar',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getRenderTagsContext: function () {
        var result = this._super.apply(this, arguments);
        result.avatarModel = this.nodeOptions.avatarModel || this.field.relation;
        result.avatarField = this.nodeOptions.avatarField || 'avatar_128';
        return result;
    },
});


// Remove event handlers on this widget to ensure that the kanban 'global
// click' opens the clicked record
const M2MAvatarMixinEvents = { ...AbstractField.prototype.events };
delete M2MAvatarMixinEvents.click;
const M2MAvatarMixin = {
    visibleAvatarCount: 3, // number of visible avatar
    events: M2MAvatarMixinEvents,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Open tooltip on empty avatar clicked
     *
     * @private
     */
    _bindPopover(ev) {
        this.$('.o_m2m_avatar_empty').popover({
            container: this.$el,
            trigger: 'hover',
            html: true,
            placement: 'auto',
            content: () => {
                const elements = this.value ? _.pluck(this.value.data, 'data') : [];
                return qweb.render('Many2ManyTagAvatarPopover', {
                    elements: elements.slice(this.visibleAvatarCount - 1),
                });
            },
        });
    },
    /**
     * @override
     */
    _getRenderTagsContext() {
        const result = this._super(...arguments);
        result['widget'] = this;
        return result;
    },
    /**
     * @override
     */
    _renderReadonly() {
        this.$el.addClass('o_field_many2manytags_multi');
        return this._super(...arguments);
    },
    /**
     * Override to bind popover
     *
     * @override
     */
    _renderTags() {
        this._super(...arguments);
        this._bindPopover();
    },
}

const KanbanMany2ManyTagsAvatar = FieldMany2ManyTagsAvatar.extend(M2MAvatarMixin, {
    tag_template: 'KanbanMany2ManyTagAvatar',
});

const ListMany2ManyTagsAvatar = FieldMany2ManyTagsAvatar.extend(M2MAvatarMixin, {
    tag_template: 'ListMany2ManyTagAvatar',
    visibleAvatarCount: 5,
});

var FormFieldMany2ManyTags = FieldMany2ManyTags.extend({
    events: _.extend({}, FieldMany2ManyTags.prototype.events, {
        'click .dropdown-toggle': '_onOpenColorPicker',
        'mousedown .o_colorpicker a': '_onUpdateColor',
        'mousedown .o_colorpicker .o_hide_in_kanban': '_onUpdateColor',
    }),
    isQuickEditable: true,
    quickEditExclusion: ['.dropdown-toggle'],
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.hasDropdown = !!this.colorField;
        this._canQuickEdit = !this.nodeOptions.no_edit_color;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _quickEdit: function () {
        this._super(...arguments);
        this.many2one.$input.click();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onOpenColorPicker: function (ev) {
        ev.preventDefault();
        if (this.nodeOptions.no_edit_color) {
            ev.stopPropagation();
            return;
        }
        var tagID = $(ev.currentTarget).parent().data('id');
        var tagColor = $(ev.currentTarget).parent().data('color');
        var tag = _.findWhere(this.value.data, { res_id: tagID });
        if (tag && this.colorField in tag.data) { // if there is a color field on the related model
            // Manual initialize dropdown and show (once)
            if (ev.currentTarget.dataset.bsToggle !== 'dropdown') {
                this.$color_picker = $(qweb.render('FieldMany2ManyTag.colorpicker', {
                    'widget': this,
                    'tag_id': tagID,
                }));

                $(ev.currentTarget).after(this.$color_picker);
                ev.currentTarget.setAttribute('data-bs-toggle', 'dropdown');
                const dropdownToggle = new Dropdown(ev.currentTarget);
                dropdownToggle.show();
            }
            this.$color_picker.attr("tabindex", 1).focus();
            if (!tagColor) {
                this.$('.form-check input').prop('checked', true);
            }
        }
    },
    /**
     * Update color based on target of ev
     * either by clicking on a color item or
     * by toggling the 'Hide in Kanban' checkbox.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onUpdateColor: function (ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        var color = $target.data('color');
        var id = $target.data('id');
        var $tag = this.$(".badge[data-id='" + id + "']");
        var currentColor = $tag.data('color');
        var changes = {};

        if ($target.is('.o_hide_in_kanban')) {
            var $checkbox = $('.o_hide_in_kanban .form-check input');
            $checkbox.prop('checked', !$checkbox.prop('checked')); // toggle checkbox
            this.prevColors = this.prevColors ? this.prevColors : {};
            if ($checkbox.is(':checked')) {
                this.prevColors[id] = currentColor;
            } else {
                color = this.prevColors[id] ? this.prevColors[id] : 1;
            }
        } else if ($target.is('[class^="o_tag_color"]')) { // $target.is('o_tag_color_')
            if (color === currentColor) { return; }
        }

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
    events: _.omit(AbstractField.prototype.events, 'click'),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;

        if (this.$el) {
            this.$el.empty().addClass('o_field_many2manytags o_kanban_tags');
        }

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
    description: _lt("Checkboxes"),
    template: 'FieldMany2ManyCheckBoxes',
    events: _.extend({}, AbstractField.prototype.events, {
        change: '_onChange',
    }),
    specialData: "_fetchSpecialRelation",
    supportedFieldTypes: ['many2many'],
    isQuickEditable: true,
    // set an arbitrary high limit to ensure that all data returned by the server
    // are processed by the BasicModel (otherwise it would be 40)
    limit: 100000,
    init: function () {
        this._super.apply(this, arguments);
        this.m2mValues = this.record.specialData[this.name];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {jQuery}
     */
    getFocusableElement: function () {
        return this.$el;
    },
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {MouseEvent} e
     * @returns {Object}
     */
    _getQuickEditExtraInfo(e) {
        const ids = new Set(this.value.res_ids);

        let input = $(e.target);
        if (e.target.matches('label')) {
            input = this.$(`input#${e.target.getAttribute('for')}`);
        }
        const id = input.data('record-id');
        if (ids.has(id)) {
            ids.delete(id);
        } else {
            ids.add(id);
        }

        return {
            ids: Array.from(ids),
        };
    },
    /**
     * @override
     * @private
     * @param {Object} extraInfo
     * @param {number[]} [extraInfo.ids]
     */
    _quickEdit(extraInfo) {
        if (extraInfo.hasOwnProperty('ids')) {
            this._setValue({
                operation: 'REPLACE_WITH',
                ids: extraInfo.ids,
            });
        }
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.m2mValues = this.record.specialData[this.name];
        this.$el.html(qweb.render(this.template, {widget: this}));
        _.each(this.value.res_ids, function (id) {
            self.$('input[data-record-id="' + id + '"]').prop('checked', true);
        });
        this.$("input").prop("disabled", this.hasReadonlyModifier);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChange: function () {
        if (this.mode !== 'readonly') {
            // Get the list of selected ids
            var ids = _.map(this.$('input:checked'), function (input) {
                return $(input).data("record-id");
            });
            // The number of displayed checkboxes is limited to 100 (name_search
            // limit, server-side), to prevent extreme cases where thousands of
            // records are fetched/displayed. If not all values are displayed, it may
            // happen that some values that are in the relation aren't available in the
            // widget. In this case, when the user (un)selects a value, we don't
            // want to remove those non displayed values from the relation. For that
            // reason, we manually add those values to the list of ids.
            const displayedIds = this.m2mValues.map(v => v[0]);
            const idsInRelation = this.value.res_ids;
            ids = ids.concat(idsInRelation.filter(a => !displayedIds.includes(a)));
            this._setValue({
                operation: 'REPLACE_WITH',
                ids: ids,
            });
        }
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

        // Retro-compatibility: clickable used to be defined in the field attrs
        // instead of options.
        // If not set, the statusbar is not clickable.
        try {
            this.isClickable = !!JSON.parse(this.attrs.clickable);
        } catch (_) {
            this.isClickable = !!this.nodeOptions.clickable;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns false to force the statusbar to be always visible (even the field
     * it not set).
     *
     * @override
     * @returns {boolean} always false
     */
    isEmpty: function () {
        return false;
    },
    /**
     * Set the legacy command for statusbar to CommandPalette.
     *
     * @override
     */
    on_attach_callback() {
        if (this.isClickable && this.viewType === 'form') {
            const provide = () => {
                return this.status_information.map((value) => ({
                    name: value['display_name'],
                    action: () => {
                        this._setValue(value['id']);
                    }
                }));
            };
            const statusLabel = sprintf(_t(`Move to %s...`), escape(this.string));
            const getCommandDefinition = (env) => ({
                name: statusLabel,
                options: {
                    activeElement: env.services.ui.getActiveElementOf(this.el),
                    category: "smart_action",
                    hotkey: "alt+shift+x",
                },
                action() {
                    return {
                        placeholder: statusLabel,
                        providers: [{ provide }],
                    }                },
            });
            core.bus.trigger("set_legacy_command", "web.FieldStatus.moveToStage", getCommandDefinition);
        }
    },
    /**
     * Remove the legacy command from CommandPalette.
     *
     * @override
     */
    on_detach_callback() {
        core.bus.trigger("remove_legacy_command", "web.FieldStatus.moveToStage");
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
            clickable: this.isClickable,
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
    description: _lt("Selection"),
    template: 'web.Legacy.FieldSelection',
    specialData: "_fetchSpecialRelation",
    supportedFieldTypes: ['selection'],
    events: _.extend({}, AbstractField.prototype.events, {
        'change': '_onChange',
    }),
    isQuickEditable: true,
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
        return this.$el && this.$el.is('select') ? this.$el : $();
    },
    /**
     * @override
     */
    isSet: function () {
        return this.value !== false;
    },
    /**
     * Listen to modifiers updates to hide/show the falsy value in the dropdown
     * according to the required modifier.
     *
     * @override
     */
    updateModifiersValue: function () {
        this._super.apply(this, arguments);
        if (!this.attrs.modifiersValue.invisible && this.mode !== 'readonly') {
            this._setValues();
            this._render();
        }
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
        var required = this.attrs.modifiersValue && this.attrs.modifiersValue.required;
        for (var i = 0 ; i < this.values.length ; i++) {
            var disabled = required && this.values[i][0] === false;

            this.$el.append($('<option/>', {
                value: JSON.stringify(this.values[i][0]),
                text: this.values[i][1],
                style: disabled ? "display: none" : "",
            }));
        }
        this.$el.val(JSON.stringify(this._getRawValue()));
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.empty().text(this._formatValue(this.value));
        this.$el.attr('raw-value', this._getRawValue());
    },
    _getRawValue: function() {
        var raw_value = this.value;
        if (this.field.type === 'many2one' && raw_value) {
            raw_value = raw_value.data.id;
        }
        return raw_value;
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
    description: _lt("Radio"),
    template: null,
    className: 'o_field_radio',
    tagName: 'div',
    specialData: "_fetchSpecialMany2ones",
    supportedFieldTypes: ['selection', 'many2one'],
    events: _.extend({}, AbstractField.prototype.events, {
        'click input': '_onInputClick',
    }),
    isQuickEditable: true,
    /**
     * @constructs FieldRadio
     */
    init: function () {
        this._super.apply(this, arguments);
        this.className += this.nodeOptions.horizontal ? ' o_horizontal' : ' o_vertical';
        this.unique_id = _.uniqueId("radio");
        this._setValues();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the currently-checked radio button, or the first one if no radio
     * button is checked.
     *
     * @override
     */
    getFocusableElement: function () {
        var checked = this.$("[checked='true']");
        return checked.length ? checked : this.$("[data-index='0']");
    },

    /**
     * Associates the 'for' attribute to the radiogroup, instead of the selected
     * radio button.
     *
     * @param {string} id
     */
    setIDForLabel: function (id) {
        this.$el.attr('id', id);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Object}
     */
    _getQuickEditExtraInfo: function (ev) {
        // can be either the input or the label
        const $target = ev.target.nodeName === 'INPUT'
            ? $(ev.target)
            : $(ev.target).siblings('input');

        const index = $target.data('index');
        const value = this.values[index];
        return {value};
    },

    /**
     * @private
     * @override
     * @params {Object} extraInfo
     */
    _quickEdit: function (extraInfo) {
        if (extraInfo.value) {
            this._saveValue(extraInfo.value);
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @private
     * @override
     */
    _render: function () {
        var self = this;
        var currentValue;
        if (this.field.type === 'many2one') {
            currentValue = this.value && this.value.data.id;
        } else {
            currentValue = this.value;
        }
        this.$el.empty();
        this.$el.attr('role', 'radiogroup')
            .attr('aria-label', this.string);
        _.each(this.values, function (value, index) {
            self.$el.append(qweb.render('FieldRadio.button', {
                checked: value[0] === currentValue,
                id: self.unique_id + '_' + value[0],
                index: index,
                name: self.unique_id,
                value: value,
                disabled: self.hasReadonlyModifier && self.mode != 'edit',
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

    /**
     * @private
     * @param {Array} new value, [value] for a selection field,
     *                           [id, display_name] for a Many2One
     */
    _saveValue: function (value) {
        if (this.field.type === 'many2one') {
            this._setValue({id: value[0], display_name: value[1]});
        } else {
            this._setValue(value[0]);
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
        if (this.mode === 'readonly') {
            this._onClick(...arguments);
        } else {
            const index = $(event.currentTarget).data('index');
            const value = this.values[index];
            this._saveValue(value);
        }
    },
});


var FieldSelectionBadge = FieldSelection.extend({
    description: _lt("Badges"),
    template: null,
    className: 'o_field_selection_badge',
    tagName: 'span',
    specialData: "_fetchSpecialMany2ones",
    events: _.extend({}, AbstractField.prototype.events, {
        'click span.o_selection_badge': '_onBadgeClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        this.currentValue = this.value;

        if (this.field.type === 'many2one') {
            this.currentValue = this.value && this.value.data.id;
        }
        this.$el.empty();
        this.$el.html(qweb.render('FieldSelectionBadge', {'values': this.values, 'current_value': this.currentValue}));
    },
    /**
     * Sets the possible field values. If the field is a many2one, those values
     * may change during the life cycle of the widget if the domain change (an
     * onchange may change the domain).
     *
     * @private
     * @override
     */
    _setValues: function () {
        // Note: We can make abstract widget for common code in radio and selection badge
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
    _onBadgeClicked: function (event) {
        var index = $(event.target).data('index');
        var value = this.values[index];
        if (value[0] !== this.currentValue) {
            if (this.field.type === 'many2one') {
                this._setValue({id: value[0], display_name: value[1]});
            } else {
                this._setValue(value[0]);
            }
        } else {
            this._setValue(false);
        }
    },
});

var FieldSelectionFont = FieldSelection.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Changes CSS for all options according to their value.
     * Also removes empty labels.
     *
     * @private
     * @override
     */
    _renderEdit: function () {
        this._super.apply(this, arguments);

        this.$('option').each(function (i, option) {
            if (! option.label) {
                $(option).remove();
            }
            $(option).css('font-family', option.value);
        });
        this.$el.css('font-family', this.value);
    },
});

/**
 * The FieldReference is a combination of a select (for the model) and
 * a FieldMany2one for its value.
 * Its intern representation is similar to the many2one (a datapoint with a
 * `name_get` as data).
 * Note that there is some logic to support char field because of one use in our
 * codebase, but this use should be removed along with this note.
 */
var FieldReference = FieldMany2One.extend({
    specialData: "_fetchSpecialReference",
    supportedFieldTypes: ['reference'],
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

        this.resetOnAnyFieldChange = this.resetOnAnyFieldChange || this.nodeOptions.model_field;
        this._setState(false);
    },
    /**
     * @override
     */
    start: function () {
        this.modelName = this.field.relation;
        if (this.el.querySelector('select')) {
            this.el.querySelector('select').value = this.modelName;
        }
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
        if (this.mode === 'edit' && !this.field.relation) {
            return this.$('select');
        }
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
     * Apply the model contained in the option model_field
     * and re-initialize the record if the model change.
     * @param {boolean} initRecord :true, re-initialize the record if the model changes.
     *                              Necessary for wizards.
     */
    _applyModelField: function (initRecord) {
        let resourceRef = this.record.specialData[this.name];
        if (resourceRef) {
            if (initRecord && resourceRef.hasChanged && resourceRef.modelName !== this.modelName) {
                this.reinitialize(false);
            }
            this.modelName = resourceRef.modelName;
        }
    },
    /**
     * Add a select in edit mode (for the model).
     *
     * @override
     */
    _renderEdit: function () {
        this._super.apply(this, arguments);

        if (this.modelName) {
            this.$('.o_input_dropdown').show();
            if (!this.nodeOptions.model_field) {
                // this class is used to display the two components (select & input) on the same line
                if (this.nodeOptions.hide_model) {
                    this.$el.addClass('o_row');
                }
                this.$el.find('.o_field_many2one_selection').addClass('o_row');
            }
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
        this._super.apply(this, arguments);
        this._setState(true);
        if (this.el.querySelector('select')) {
            this.el.querySelector('select').value = this.modelName;
        }
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
    _setState: function (initRecord) {
        if (this.field.type === 'char') {
            // in this case, the value is stored in specialData instead
            this.value = this.record.specialData[this.name];
        }
        if (this.nodeOptions.model_field) {
            this._applyModelField(initRecord);
        }
        if (this.value && this.value.model) {
            this.modelName = this.value.model;
        }
        if (this.modelName) {
            this._setRelation(this.modelName);
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
        value.model = this.modelName;
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
        this.modelName = this.el.querySelector('select').value || '';
        this.reinitialize(false);
        this._setRelation(this.modelName);
    },
});

return {
    FieldMany2One: FieldMany2One,
    Many2oneBarcode: Many2oneBarcode,
    KanbanFieldMany2One: KanbanFieldMany2One,
    ListFieldMany2One: ListFieldMany2One,
    Many2OneAvatar: Many2OneAvatar,

    FieldX2Many: FieldX2Many,
    FieldOne2Many: FieldOne2Many,

    FieldMany2Many: FieldMany2Many,
    FieldMany2ManyBinaryMultiFiles: FieldMany2ManyBinaryMultiFiles,
    FieldMany2ManyCheckBoxes: FieldMany2ManyCheckBoxes,
    FieldMany2ManyTags: FieldMany2ManyTags,
    FieldMany2ManyTagsAvatar: FieldMany2ManyTagsAvatar,
    KanbanMany2ManyTagsAvatar: KanbanMany2ManyTagsAvatar,
    ListMany2ManyTagsAvatar: ListMany2ManyTagsAvatar,
    FormFieldMany2ManyTags: FormFieldMany2ManyTags,
    KanbanFieldMany2ManyTags: KanbanFieldMany2ManyTags,

    FieldRadio: FieldRadio,
    FieldSelectionBadge: FieldSelectionBadge,
    FieldSelection: FieldSelection,
    FieldStatus: FieldStatus,
    FieldSelectionFont: FieldSelectionFont,

    FieldReference: FieldReference,
};

});
