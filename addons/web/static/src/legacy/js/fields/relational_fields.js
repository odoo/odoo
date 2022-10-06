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

return {
    FieldMany2One: FieldMany2One,
    FieldMany2ManyTags: FieldMany2ManyTags,
};

});
