odoo.define('web.SearchBar', function (require) {
"use strict";

var AutoComplete = require('web.AutoComplete');
var searchBarAutocompleteRegistry = require('web.search_bar_autocomplete_sources_registry');
var SearchFacet = require('web.SearchFacet');
var Widget = require('web.Widget');

var SearchBar = Widget.extend({
    template: 'SearchView.SearchBar',
    events: _.extend({}, Widget.prototype.events, {
        'compositionend .o_searchview_input': '_onCompositionendInput',
        'compositionstart .o_searchview_input': '_onCompositionstartInput',
        'keydown': '_onKeydown',
    }),
    /**
     * @override
     * @param {Object} [params]
     * @param {Object} [params.context]
     * @param {Object[]} [params.facets]
     * @param {Object} [params.fields]
     * @param {Object[]} [params.filterFields]
     * @param {Object[]} [params.filters]
     * @param {Object[]} [params.groupBys]
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);

        this.context = params.context;

        this.facets = params.facets;
        this.fields = params.fields;
        this.filterFields = params.filterFields;

        this.autoCompleteSources = [];
        this.searchFacets = [];
        this._isInputComposing = false;
    },
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('input');
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        _.each(this.facets, function (facet) {
            defs.push(self._renderFacet(facet));
        });
        defs.push(this._setupAutoCompletion());
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focus the searchbar.
     */
    focus: function () {
      this.$input.focus();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _focusFollowing: function () {
        var focusedIndex = this._getFocusedFacetIndex();
        var $toFocus;
        if (focusedIndex === this.searchFacets.length - 1) {
            $toFocus = this.$input;
        } else {
            $toFocus = this.searchFacets.length && this.searchFacets[focusedIndex + 1].$el;
        }

        if ($toFocus.length) {
            $toFocus.focus();
        }
    },
    /**
     * @private
     */
    _focusPreceding: function () {
        var focusedIndex = this._getFocusedFacetIndex();
        var $toFocus;
        if (focusedIndex === -1) {
            $toFocus = this.searchFacets.length && _.last(this.searchFacets).$el;
        } else if (focusedIndex === 0) {
            $toFocus = this.$input;
        } else {
            $toFocus = this.searchFacets.length && this.searchFacets[focusedIndex - 1].$el;
        }

        if ($toFocus.length) {
            $toFocus.focus();
        }
    },
    /**
     * @private
     * @returns {integer}
     */
    _getFocusedFacetIndex: function () {
        return _.findIndex(this.searchFacets, function (searchFacet) {
            return searchFacet.$el[0] === document.activeElement;
        });
    },
    /**
     * Provide auto-completion result for req.term.
     *
     * @private
     * @param {Object} req request to complete
     * @param {String} req.term searched term to complete
     * @param {Function} callback
     */
    _getAutoCompleteSources: function (req, callback) {
        var defs = this.autoCompleteSources.map(function (source) {
            return source.getAutocompletionValues(req.term);
        });
        Promise.all(defs).then(function (result) {
            var resultCleaned = _(result).chain()
                .compact()
                .flatten(true)
                .value();
            callback(resultCleaned);
        });
    },
    /**
     * @private
     * @param {Object} facet
     * @returns {Promise}
     */
    _renderFacet: function (facet) {
        var searchFacet = new SearchFacet(this, facet);
        this.searchFacets.push(searchFacet);
        return searchFacet.insertBefore(this.$('input'));
    },
    /**
     * @private
     * @returns {Promise}
     */
    _setupAutoCompletion: function () {
        var self = this;
        this._setupAutoCompletionWidgets();
        this.autoComplete = new AutoComplete(this, {
            $input: this.$('input'),
            source: this._getAutoCompleteSources.bind(this),
            select: this._onAutoCompleteSelected.bind(this),
            get_search_string: function () {
                return self.$input.val().trim();
            },
        });
        return this.autoComplete.appendTo(this.$el);
    },
    /**
     * @private
     */
    _setupAutoCompletionWidgets: function () {
        var self = this;
        var registry = searchBarAutocompleteRegistry;
        _.each(this.filterFields, function (filter) {
            var field = self.fields[filter.attrs.name];
            var Obj = registry.getAny([filter.attrs.widget, field.type]);
            if (Obj) {
                self.autoCompleteSources.push(new (Obj) (self, filter, field, self.context));
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} e
     * @param {Object} ui
     * @param {Object} ui.item selected completion item
     */
    _onAutoCompleteSelected: function (e, ui) {
        e.preventDefault();
        var facet = ui.item.facet;
        if (!facet) {
            // this happens when selecting "(no result)" item
            this.trigger_up('reset');
            return;
        }
        var filter = facet.filter;
        if (filter.type === 'field') {
            var values = filter.autoCompleteValues;
            values.push(facet.values[0]);
            this.trigger_up('autocompletion_filter', {
                filterId: filter.id,
                autoCompleteValues: values,
            });
        } else {
            this.trigger_up('autocompletion_filter', {
                filterId: filter.id,
            });
        }
    },
    /**
     * @rivate
     * @param {CompositionEvent} ev
     */
    _onCompositionendInput: function () {
        this._isInputComposing = false;
    },
    /**
     * @rivate
     * @param {CompositionEvent} ev
     */
    _onCompositionstartInput: function () {
        this._isInputComposing = true;
    },
    /**
     * @private
     * @param {KeyEvent} e
     */
    _onKeydown: function (e) {
        if (this._isInputComposing) {
            return;
        }
        switch(e.which) {
            case $.ui.keyCode.LEFT:
                this._focusPreceding();
                e.preventDefault();
                break;
            case $.ui.keyCode.RIGHT:
                this._focusFollowing();
                e.preventDefault();
                break;
            case $.ui.keyCode.DOWN:
                // if the searchbar dropdown is closed, try to focus the renderer
                const $dropdown = this.$('.o_searchview_autocomplete:visible');
                if (!$dropdown.length) {
                    this.trigger_up('navigation_move', { direction: 'down' });
                    e.preventDefault();
                }
                break;
            case $.ui.keyCode.BACKSPACE:
                if (this.$input.val() === '') {
                    this.trigger_up('facet_removed');
                }
                break;
            case $.ui.keyCode.ENTER:
                if (this.$input.val() === '') {
                    this.trigger_up('reload');
                }
                break;
        }
    },
});

return SearchBar;

});
