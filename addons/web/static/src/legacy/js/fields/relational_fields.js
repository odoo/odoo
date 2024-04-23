/** @odoo-module alias=web.relational_fields **/

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

import AbstractField from "web.AbstractField";
import concurrency from "web.concurrency";
import core from "web.core";
import Dialog from "web.Dialog";
import dom from "web.dom";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import Domain from "web.Domain";
import { escape, sprintf } from "@web/core/utils/strings";
import { uniqueId } from "@web/core/utils/functions";
import { sortBy } from "@web/core/utils/arrays";

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
            title: sprintf(_t("New %s"), this.name),
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
    custom_events: Object.assign({}, AbstractField.prototype.custom_events, {
        'closed_unset': '_onDialogClosedUnset',
        'field_changed': '_onFieldChanged',
        'quick_create': '_onQuickCreate',
    }),
    events: Object.assign({}, AbstractField.prototype.events, {
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

        this.nodeOptions = Object.assign(
            {
                quick_create: true,
            },
            this.nodeOptions
        );
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

        this._autocompleteSources = sortBy(this._autocompleteSources, 'order');
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
                self._autocompleteSources.forEach((source) => {
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
        this._autocompleteSources.forEach((source) => {
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
            resModel: this.field.relation,
            domain: this.record.getDomain(this.recordParams),
            context: Object.assign({}, this.record.getContext(this.recordParams), context || {}),
            dynamicFilters: dynamicFilters || [],
            title: sprintf((view === 'search' ? _t("Search: %s") : _t("Create: %s")), this.string),
            multiSelect: false,
            noCreate: !self.can_create,
            onSelected: function (records) {
                self.reinitialize({ id: records[0] });
            },
            onClose: function () {
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
                        var ids = results.map((x) => x[0]);
                        dynamicFilters = [{
                            description: sprintf(_t('Quick search: %s'), search_val),
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
                owl.Component.env.services.dialog.add(FormViewDialog, {
                    title: _t("Create: ") + self.string,
                    resModel: self.field.relation,
                    context: self._createContext(name),
                    onRecordSaved: (record) => {
                        self.reinitialize({
                            id: record.resId,
                            display_name: record.data.display_name || record.data.name,
                        });
                    },
                }, { onClose: createDone });
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
        const escapedValue = escape((this.m2o_value || "").trim());
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
            this.$el.attr('href', `#id=${this.value.res_id}&model=${this.field.relation}`);
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

        if (this.lastNameSearch) {
            this.lastNameSearch.catch((reason) => {
                // the last rpc name_search will be aborted, so we want to ignore its rejection
                reason.event.preventDefault();
            })
            this.lastNameSearch.abort(false)
        }
        this.lastNameSearch = this._rpc({
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
        const results = await this.orderer.add(this.lastNameSearch);

        // Format results to fit the options dropdown
        let values = results.map((result) => {
            const [id, fullName] = result;
            const displayName = this._getDisplayName(fullName).trim();
            result[1] = displayName;
            // ℹ️ `_t` can only be inlined directly inside JS template literals
            // after Babel has been updated to version 2.12.
            const translatedText = _t("Unnamed");
            return {
                id,
                label:
                    escape(displayName) ||
                    `<em class="text-warning">${escape(translatedText)}</em>`,
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
                        owl.Component.env.services.dialog.add(FormViewDialog, {
                            title: _t("Create: ") + this.string,
                            resModel: this.field.relation,
                            context: { ...this.record.getContext(this.recordParams), ...valueContext },
                            onRecordSaved: (record) => {
                                this.reinitialize({
                                    id: record.resId,
                                    display_name: record.data.display_name || record.data.name,
                                });
                            },
                        });
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
    _searchCreatePopup: function (view, ids, context, dynamicFilters, onClose) {
        const props = this._getSearchCreatePopupOptions(view, ids, context, dynamicFilters);
        if (onClose) {
            const _onClose = onClose;
            onClose = () => {
                _onClose();
                props.onClose();
            }
        } else {
            onClose = props.onClose;
        }
        delete props.onClose;
        owl.Component.env.services.dialog.add(SelectCreateDialog, props, { onClose });
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
                owl.Component.env.services.dialog.add(FormViewDialog, {
                    title: _t("Open: ") + self.string,
                    resModel: self.field.relation,
                    viewId: view_id,
                    resId: self.value.res_id,
                    mode: self.can_write ? "edit" : "readonly",
                    preventEdit: !self.can_write,
                    preventCreate: !self.can_create,
                    context,
                    onRecordSaved: function () {
                        const _setValue = self._setValue.bind(self, self.value.data, {
                            forceChange: true,
                        });
                        self.trigger_up('reload', {
                            db_id: self.value.id,
                            onSuccess: _setValue,
                            onFailure: _setValue,
                        });
                    },
                });
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
        if (!this.floating || this.$input.val() === "") {
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

var FieldMany2ManyTags = AbstractField.extend({
    description: _lt("Tags"),
    tag_template: "FieldMany2ManyTag",
    className: "o_field_many2manytags",
    supportedFieldTypes: ['many2many'],
    custom_events: Object.assign({}, AbstractField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: Object.assign({}, AbstractField.prototype.events, {
        'click .o_delete': '_onDeleteTag',
    }),
    relatedFields: {
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
        if (!this.value.res_ids.includes(data.id)) {
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
        var elements = this.value ? this.value.data.map((d) => d.data) : [];
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
        var record = this.value.data.find((val) => val.res_id === id);
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
            return Object.assign({}, options, {
                domain: domain.concat(["!", ["id", "in", self.value.res_ids]]),
                multiSelect: true,
                onSelected: function (recordIds) {
                    m2mRecords.push(...recordIds.map((id) => { return { id } }));
                },
                onClose: function () {
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
                const elements = this.value ? this.value.data.map((d) => d.data) : [];
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
    events: Object.assign({}, FieldMany2ManyTags.prototype.events, {
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
        var tag = this.value.data.find((val) => val.res_id === tagID);
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
            dataPointID: this.value.data.find((val) => val.res_id === id).id,
            changes: changes,
            force_save: true,
        });
    },
});

//------------------------------------------------------------------------------
// Widgets handling both basic and relational fields (selection and Many2one)
//------------------------------------------------------------------------------

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
    events: Object.assign({}, AbstractField.prototype.events, {
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
            this.values = this.field.selection.filter(v => !(v[0] === false && v[1] === ''));
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
            var value = this.values.find(val => val[0] === res_id);
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
    events: Object.assign({}, AbstractField.prototype.events, {
        'click input': '_onInputClick',
    }),
    isQuickEditable: true,
    /**
     * @constructs FieldRadio
     */
    init: function () {
        this._super.apply(this, arguments);
        this.className += this.nodeOptions.horizontal ? ' o_horizontal' : ' o_vertical';
        this.unique_id = uniqueId("radio");
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
        this.values.forEach((value, index) => {
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
            this.values = this.record.specialData[this.name].map((val) => {
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

export default {
    FieldMany2One: FieldMany2One,
    Many2OneAvatar: Many2OneAvatar,
    FieldMany2ManyTags: FieldMany2ManyTags,
    FieldMany2ManyTagsAvatar: FieldMany2ManyTagsAvatar,
    KanbanMany2ManyTagsAvatar: KanbanMany2ManyTagsAvatar,
    ListMany2ManyTagsAvatar: ListMany2ManyTagsAvatar,
    FormFieldMany2ManyTags: FormFieldMany2ManyTags,
    FieldRadio: FieldRadio,
    FieldSelection: FieldSelection,
};
