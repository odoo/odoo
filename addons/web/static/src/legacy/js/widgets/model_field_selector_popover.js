odoo.define("web.ModelFieldSelectorPopover", function (require) {
"use strict";

var core = require("web.core");
var Widget = require("web.Widget");
const { fuzzyLookup } = require('@web/core/utils/search');

var _t = core._t;

/**
 * Field Selector Cache - TODO Should be improved to use external cache ?
 * - Stores fields per model used in field selector
 * @see ModelFieldSelector._getModelFieldsFromCache
 */
var modelFieldsCache = {
    cache: {},
    cacheDefs: {},
};

core.bus.on('clear_cache', null, function () {
    modelFieldsCache.cache = {};
    modelFieldsCache.cacheDefs = {};
});
/**
 * The ModelFieldSelector widget can be used to display/select a particular
 * field chain from a given model.
 */
var ModelFieldSelectorPopover = Widget.extend({
    baseTemplate: "ModelFieldSelector",
    template: "ModelFieldSelector.popover",
    events: {
        // Handle popover opening and closing
        "focusin": "_onFocusIn",
        "focusout": "_onFocusOut",
        "click .o_field_selector_close": "_onCloseClick",

        // Handle popover field navigation
        "click .o_field_selector_prev_page": "_onPrevPageClick",
        "click .o_field_selector_next_page": "_onNextPageClick",
        "click li.o_field_selector_select_button": "_onLastFieldClick",

        // Handle a direct change in the debug input
        "change input.o_field_selector_debug": "_onDebugInputChange",

        // Handle a change in the search input
        "keyup .o_field_selector_search > input": "_onSearchInputChange",
        // Handle a change in the default value input
        "keyup .o_field_selector_default_value_input > input": "_onDefaultValueChange",

        // Handle keyboard and mouse navigation to build the field chain
        "mouseover li.o_field_selector_item": "_onItemHover",
        "keydown": "_onKeydown",
    },
    /**
     * @constructor
     * The ModelFieldSelector requires a model and a field chain to work with.
     *
     * @param parent
     * @param {string} model - the model name (e.g. "res.partner")
     * @param {string[]} chain - list of the initial field chain parts
     * @param {Object} [options] - some key-value options
     * @param {string} [options.order='string']
     *                 an ordering key for displayed fields
     * @param {function} [options.filter]
     *                 a function to filter the fetched fields
     * @param {Object} [options.filters]
     *                 some key-value options to filter the fetched fields
     * @param {boolean} [options.filters.searchable=true]
     *                  true if only the searchable fields have to be used
     * @param {Object[]} [options.fields=null]
     *                   the list of fields info to use when no relation has
     *                   been followed (null indicates the widget has to request
     *                   the fields itself)
     * @param {boolean|function} [options.followRelations=true]
     *                  true if can follow relation when building the chain
     * @param {boolean} [options.showSearchInput=true]
     *                  false to hide a search input to filter displayed fields
     * @param {boolean} [options.needDefaultValue=false]
     *                  true if a default value can be entered after the selected chain
     * @param {boolean} [options.cancelOnEscape=false]
     *                  true if a the chain selected should be ignored when the user hit ESC
     * @param {boolean} [options.debugMode=false]
     *                  true if the widget is in debug mode, false otherwise
     */
    init: function (parent, model, chain, options) {
        this._super.apply(this, arguments);

        this.model = model;
        this.chain = chain;
        this.options = _.extend({
            order: 'string',
            filters: {},
            fields: null,
            filter: () => true,
            followRelations: true,
            debugMode: false,
            showSearchInput: true,
            needDefaultValue: false,
            cancelOnEscape: false,
            chainedTitle: false
        }, options || {});
        this.options.filters = _.extend({
            searchable: true,
        }, this.options.filters);

        if (typeof this.options.followRelations !== 'function') {
            this.options.followRelations = this.options.followRelations ?
                (() => true) :
                (() => false);
        }

        this.pages = [];
        this.titlesNames = {};
        this.dirty = false;
        this.searchValue = '';
        this.defaultValue = '';
    },
    /**
     * @see Widget.willStart()
     * @returns {Promise}
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this.prefill()
        ]);
    },
    /**
     * @see Widget.start
     * @returns {Promise}
     */
    start: function () {
        this.$input = this.$el.find(".o_field_selector_popover_footer > input");
        this.$searchInput = this.$el.find(".o_field_selector_search > input");
        this.$defaultValueInput = this.$el.find(".o_field_selector_default_value_input > input");

        this._render();
        return this._super.apply(this, arguments).then(() => {
            this.trigger_up("field_selector_started");
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the field information selected by the field chain.
     *
     * @returns {Object}
     */
    getSelectedField: function () {
        return _.findWhere(this.pages[this.chain.length - 1], {name: _.last(this.chain)});
    },
    /**
     * Saves a new field chain (array) and re-render.
     *
     * @param {string[]} chain - the new field chain
     * @returns {Promise} resolved once the re-rendering is finished
     */
    setChain: function (chain) {
        if (_.isEqual(chain, this.chain)) {
            return Promise.resolve();
        }

        this.chain = chain;
        return this.prefill().then(this._render.bind(this));
    },

    /**
     * Manualy open the popover and force the chain
     *
     * @param {string[]} chain - the new field chain
     * @param {boolean} focus - force the focus in the search field
     * @returns {Promise} resolved once the re-rendering is finished
     */
    open: async function (chain = [], focus = false) {
        clearTimeout(this._hidePopoverTimeout);

        this.$searchInput.val('');
        await this.setChain(chain);
        this._showPopover();

        if (focus) {
            this.$searchInput.focus();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a field name to the current field chain and marks it as dirty.
     *
     * @private
     * @param {string} fieldName - the new field name to add at the end of the
     *                           current field chain
     */
    _addChainNode: function (fieldName) {
        this.dirty = true;
        this.chain = this.chain.slice(0, this.pages.length - 1);
        this.chain.push(fieldName);

        this.searchValue = '';
        this.$searchInput.val('');
    },
    /**
     * Searches a field in the last page by its name.
     *
     * @private
     * @param {string} name - the name of the field to find
     * @returns {Object} the field data found in the last popover page thanks
     *                   to its name
     /*/
    _getLastPageField: function (name) {
        return _.findWhere(_.last(this.pages), {
            name: name,
        });
    },
    /**
     * Searches the cache for the given model fields, according to the given
     * filter. If the cache does not know about the model, the cache is updated.
     *
     * @private
     * @param {string} model
     * @param {Object} filters @see ModelFieldSelector.init.options.filters
     * @returns {Object[]} a list of the model fields info, sorted by field
     *                     non-technical names
     */
    _getModelFieldsFromCache: function (model, filters) {
        var self = this;
        var def = modelFieldsCache.cacheDefs[model];
        if (!def) {
            def = modelFieldsCache.cacheDefs[model] = this._rpc({
                model: model,
                method: 'fields_get',
                args: [
                    false,
                    ["store", "searchable", "type", "string", "relation", "selection", "related"]
                ],
                context: this.getSession().user_context,
            })
                .then((function (fields) {
                    modelFieldsCache.cache[model] = sortFields(fields, model, self.options.order);
                }).bind(this));
        }
        return def.then((function () {
            return _.filter(modelFieldsCache.cache[model], function (f) {
                return (!filters.searchable || f.searchable) && self.options.filter(f);
            });
        }).bind(this));
    },
    /**
     * Return true if the widget is currently open on the default value page
     *
     * @private
     * @returns {Boolean} Is on default value page
     */
    _isOnDefaultValuePage: function () {
        return this.pages[this.pages.length - 1] === 'defaultValuePage';
    },
    /**
     * Adds a new page to the popover following the given field relation and
     * show the defauld value choice page
     *
     * @private
     * @param {String} name - the name of the field to add to the chain node
     */
    _goToDefaultValuePage: function (name) {
        this._validate(true);

        this._addChainNode(name);
        this.pages.push('defaultValuePage');
        this.$defaultValueInput.val('');
        this.defaultValue = '';

        this._renderDefaultValue();
    },
    /**
     * Adds a new page to the popover following the given field relation and
     * adapts the chain node according to this given field.
     *
     * @private
     * @param {Object} field - the field to add to the chain node
     */
    _goToNextPage: function (field) {
        if (!_.isEqual(this._getLastPageField(field.name), field)) return;

        this._validate(true);
        this._addChainNode(field.name);
        this._pushPageData(field.relation).then(this._render.bind(this));
    },
    /**
     * Removes the last page, adapts the field chain and displays the new
     * last page.
     *
     * @private
     */
    _goToPrevPage: function () {
        if (this.pages.length <= 0) return;

        this._validate(true);
        this._removeChainNode();
        if (this.pages.length > 1) {
            this.pages.pop();
        }
        this._render();
    },
    /**
     * Closes the popover and marks the field as selected. If the field chain
     * changed, it notifies its parents. If not open, this does nothing.
     *
     * @private
     * @param {boolean} cancel - prevent the triggerUp of the `field_chain_changed` event
     */
    _hidePopover: function (cancel = false) {
        if (!this._isOpen) return;

        this._isOpen = false;
        this.$searchInput.parent().removeClass('d-none');
        this.$defaultValueInput.parent().addClass('d-none');
        this.$el.addClass('d-none');

        if (cancel) {
            this.trigger_up("field_chain_cancel");
        } else if (this.dirty) {
            this.trigger_up("field_chain_changed", {chain: this.chain, defaultValue: this.defaultValue});
        }
        this.dirty = false;
        this.defaultValue = '';
    },
    /**
     * Prepares the popover by filling its pages according to the current field
     * chain.
     *
     * @private
     * @returns {Promise} resolved once the whole field chain has been
     *                     processed
     */
    prefill: function () {
        this.pages = [];
        return this._pushPageData(this.model).then((function () {
            this._validate(true);
            return (this.chain.length ? processChain.call(this, this.chain.slice().reverse()) : Promise.resolve());
        }).bind(this));

        function processChain(chain) {
            var fieldName = chain.pop();
            var field = this._getLastPageField(fieldName);
            if (field && field.relation) {
                if (chain.length) { // Fetch next chain node if any and possible
                    return this._pushPageData(field.relation).then(processChain.bind(this, chain));
                } else { // Simply update the last popover page
                    return this._pushPageData(field.relation);
                }
            } else if (field && chain.length === 0) { // Last node fetched
                return Promise.resolve();
            } else if (!field && fieldName === "1") { // TRUE_LEAF
                this._validate(true);
            } else if (!field && fieldName === "0") { // FALSE_LEAF
                this._validate(true);
            } else { // Wrong node chain
                this._validate(false);
            }
            return Promise.resolve();
        }
    },
    /**
     * Gets the fields of a particular model and adds them to a new last
     * popover page.
     *
     * @private
     * @param {string} model - the model name whose fields have to be fetched
     * @returns {Promise} resolved once the fields have been added
     */
    _pushPageData: function (model) {
        var def;
        if (this.model === model && this.options.fields) {
            def = Promise.resolve(sortFields(this.options.fields, model, this.options.order));
        } else {
            def = this._getModelFieldsFromCache(model, this.options.filters);
        }
        return def.then((function (fields) {
            this.pages.push(fields);
        }).bind(this));
    },
    /**
     * Removes the last field name at the end of the current field chain and
     * marks it as dirty.
     *
     * @private
     */
    _removeChainNode: function () {
        this.dirty = true;
        this.chain = this.chain.slice(0, this.pages.length - 1);
        this.chain.pop();
    },
    /**
     * Get the current value for the popover header
     *
     * @private
     */
    _getTitle: function () {
        var title = "";
        if (this.pages.length > 1) {
            var prevField = _.findWhere(this.pages[this.pages.length - 2], {
                name: (this.chain.length === this.pages.length) ? this.chain[this.chain.length - 2] : _.last(this.chain),
            });
            if (prevField) {
                this.titlesNames[_.last(this.chain)] = prevField.string;
                title = prevField.string;
            }
        }
        if (this.options.chainedTitle) {
            title = this.chain.map((chain) => this.titlesNames[chain]).join(' > ');
        }

        return title;
    },
    /**
     * Adapts the content of the popover.
     *
     * @private
     */
    _render: function () {
        this._adaptInputVisibility();

        // Adapt the popover content
        var page = _.last(this.pages);
        this.$(".o_field_selector_popover_header .o_field_selector_title").text(this._getTitle());

        var lines = _.filter(page, this.options.filter);
        if (this.searchValue) {
            lines = fuzzyLookup(this.searchValue, lines, (l) => l.string);
        }

        this.$(".o_field_selector_page").replaceWith(core.qweb.render(this.baseTemplate + ".page", {
            lines: lines,
            followRelations: this.options.followRelations,
            debug: this.options.debugMode,
        }));
        this.$input.val(this.chain.join("."));

        this.trigger_up("field_selector_render");
    },
    /**
     * Adapts the content of the popover with the default value page.
     *
     * @private
     */
    _renderDefaultValue: function () {
        this._adaptInputVisibility();
        this.$defaultValueInput.focus();

        // Adapt the popover content
        let title = this._getTitle() + '<br>' + _t("Default value");
        this.$(".o_field_selector_popover_header .o_field_selector_title")[0].replaceChildren(
            ...$('<div>' + title + '</div>')[0].childNodes
        );

        this.$(".o_field_selector_page").replaceWith(core.qweb.render(this.baseTemplate + ".defaultValue", {
            line: {
                string: '',
                description: this.defaultValue.length ? _t("As a default text when no value are set") : _t("Default text is used when no values are set"),
            }
        }));
        this.$input.val(this.chain.join(".") + (this.defaultValue ? " OR " + this.defaultValue : ""));

        this.trigger_up("field_selector_render");
    },
    /**
     * Adapt the visibilitty of the search and default view input.
     *
     * @private
     */
    _adaptInputVisibility() {
        this.$searchInput.parent().toggleClass("d-none", this._isOnDefaultValuePage());
        this.$defaultValueInput.parent().toggleClass("d-none", !this._isOnDefaultValuePage());
    },
    /**
     * Selects the given field and adapts the chain node according to it.
     * It also closes the popover and so notifies the parents about the change.
     *
     * @param {Object} field - the field to select
     */
    _selectField: function (field) {
        if (!_.isEqual(this._getLastPageField(field.name), field)) return;

        this._validate(true);
        this._addChainNode(field.name);
        this._render();
        this._hidePopover();
    },
    /**
     * Shows the popover to select the field chain. This assumes that the
     * popover has finished its rendering (fully rendered widget or resolved
     * deferred of @see setChain). If already open, this does nothing.
     *
     * @private
     */
    _showPopover: function () {
        if (this._isOpen) return;

        this._isOpen = true;
        this.$el.removeClass('d-none');
    },
    /**
     * Toggles the valid status of the widget and display the error message if
     * it is not valid.
     *
     * @private
     * @param {boolean} valid - true if the widget is valid, false otherwise
     */
    _validate: function (valid) {
        this.valid = !!valid;

        if (!this.valid) {
            this.displayNotification({
                message: _t("Invalid field chain. You may have used a non-existing field name or followed a non-relational field."),
                type: 'danger',
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the widget is focused -> opens the popover
     */
    _onFocusIn: function () {
        clearTimeout(this._hidePopoverTimeout);
        this._showPopover();
    },
    /**
     * Called when the widget is blurred -> closes the popover
     */
    _onFocusOut: function () {
        clearTimeout(this._hidePopoverTimeout);
        this._hidePopoverTimeout = _.defer(() => this._hidePopover(this.options.cancelOnEscape));
    },
    /**
     * Called when the popover "cross" icon is clicked -> closes the popover
     */
    _onCloseClick: function () {
        this._hidePopover(this.options.cancelOnEscape);
    },
    /**
     * Called when the popover "previous" icon is clicked -> removes last chain
     * node
     */
    _onPrevPageClick: function () {
        this._goToPrevPage();
    },
    /**
     * Called when a popover relation field button is clicked -> adds it to
     * the chain
     *
     * @param {Event} e
     */
    _onNextPageClick: function (e) {
        e.stopPropagation();
        this._goToNextPage(this._getLastPageField($(e.currentTarget).data("name")));
    },
    /**
     * Called when a popover non-relation field button is clicked -> adds it to
     * chain and closes the popover
     *
     * @param {Event} e
     */
    _onLastFieldClick: function (e) {
        const name = $(e.currentTarget).data("name");
        if (this.options.needDefaultValue && this._isOnDefaultValuePage()) {
            this._hidePopover();
        } else if (this.options.needDefaultValue) {
            this._goToDefaultValuePage(name);
        } else {
            this._selectField(this._getLastPageField(name));
        }
    },
    /**
     * Called when the debug input value is changed -> adapts the chain
     */
    _onDebugInputChange: function () {
        var userChainStr = this.$input.val();
        var userChain = userChainStr.split(".");
        if (!this.options.followRelations && userChain.length > 1) {
            this.displayNotification({
                title: _t("Relation not allowed"),
                message: _t("You cannot follow relations for this field chain construction"),
                type: 'danger',
            });
            userChain = [userChain[0]];
        }
        this.setChain(userChain).then((function () {
            this.trigger_up("field_chain_changed", {chain: this.chain});
        }).bind(this));
    },
    /**
     * Called when the search input value is changed -> adapts the popover
     */
    _onSearchInputChange: function () {
        this.searchValue = this.$searchInput.val();
        this._render();
    },
    /**
     * Called when the default value input value is changed -> adapts the popover
     */
    _onDefaultValueChange: function () {
        this.defaultValue = this.$defaultValueInput.val();
        if (this._isOnDefaultValuePage()) {
            this._renderDefaultValue();
        }
    },
    /**
     * Called when a popover field button item is hovered -> toggles its
     * "active" status
     *
     * @param {Event} e
     */
    _onItemHover: function (e) {
        this.$("li.o_field_selector_item").removeClass("active");
        $(e.currentTarget).addClass("active");
    },
    /**
     * Called when the user uses the keyboard when the widget is focused
     * -> handles field keyboard navigation
     *
     * @param {Event} e
     */
    _onKeydown: function (e) {
        if (!this.$el.is(":visible")) return;
        var inputHasFocus = this.$input.is(":focus");
        let name = this.$("li.o_field_selector_item.active").data("name");

        switch (e.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                e.preventDefault();
                var $active = this.$("li.o_field_selector_item.active");
                var $to = $active[e.which === $.ui.keyCode.DOWN ? "next" : "prev"](".o_field_selector_item");
                if ($to.length) {
                    $active.removeClass("active");
                    $to.addClass("active");
                    this.$el.focus();

                    var $page = $to.closest(".o_field_selector_page");
                    var full_height = $page.height();
                    var el_position = $to.position().top;
                    var el_height = $to.outerHeight();
                    var current_scroll = $page.scrollTop();
                    if (el_position < 0) {
                        $page.scrollTop(current_scroll - el_height);
                    } else if (full_height < el_position + el_height) {
                        $page.scrollTop(current_scroll + el_height);
                    }
                }
                break;
            case $.ui.keyCode.RIGHT:
                if (inputHasFocus) break;
                e.preventDefault();
                if (name) {
                    var field = this._getLastPageField(name);
                    if (field.relation) {
                        this._goToNextPage(field);
                    } else if (this.options.needDefaultValue && !this._isOnDefaultValuePage()) {
                        this._goToDefaultValuePage(name);
                    }
                }
                break;
            case $.ui.keyCode.LEFT: {
                if (inputHasFocus) break;
                e.preventDefault();
                const isOnDefaultValuePage = this._isOnDefaultValuePage();
                this._goToPrevPage();
                if (isOnDefaultValuePage) {
                    this.$searchInput.focus();
                }
                break;
            }
            case $.ui.keyCode.ESCAPE:
                e.stopPropagation();
                this._hidePopover(this.options.cancelOnEscape);
                break;
            case $.ui.keyCode.ENTER:
                e.preventDefault();
                if (!name && !this._isOnDefaultValuePage()) {
                    this._hidePopover(this.options.cancelOnEscape);
                    break;
                }
                if (this.options.needDefaultValue && this._isOnDefaultValuePage()) {
                    this._hidePopover();
                } else if (this.options.needDefaultValue) {
                    this._goToDefaultValuePage(name);
                } else {
                    this._selectField(this._getLastPageField(name));
                }
                break;
        }
    }
});

return ModelFieldSelectorPopover;

/**
 * Allows to transform a mapping field name -> field info in an array of the
 * field infos, sorted by field user name ("string" value). The field infos in
 * the final array contain an additional key "name" with the field name.
 *
 * @param {Object} fields - the mapping field name -> field info
 * @param {string} model
 * @returns {Object[]} the field infos sorted by field "string" (field infos
 *                     contain additional keys "model" and "name" with the field
 *                     name)
 */
function sortFields(fields, model, order) {
    var array = _.chain(fields)
        .pairs()
        .sortBy(function (p) { return p[1].string; });
    if (order !== 'string') {
        array = array.sortBy(function (p) {return p[1][order]; });
    }
    return array.map(function (p) {
            return _.extend({
                name: p[0],
                model: model,
            }, p[1]);
        }).value();
}
});
