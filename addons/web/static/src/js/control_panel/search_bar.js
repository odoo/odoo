odoo.define('web.SearchBar', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const field_utils = require('web.field_utils');
    const { useAutofocus } = require('web.custom_hooks');
    const { useModel } = require('web/static/src/js/model.js');

    const CHAR_FIELDS = ['char', 'html', 'many2many', 'many2one', 'one2many', 'text'];
    const { Component, hooks } = owl;
    const { useExternalListener, useRef, useState } = hooks;

    let sourceId = 0;

    /**
     * Search bar
     *
     * This component has two main roles:
     * 1) Display the current search facets
     * 2) Create new search filters using an input and an autocompletion values
     *    generator.
     *
     * For the first bit, the core logic can be found in the XML template of this
     * component, searchfacet components or in the ControlPanelModel itself.
     *
     * The autocompletion mechanic works with transient subobjects called 'sources'.
     * Sources contain the information that will be used to generate new search facets.
     * A source is generated either:
     * a. From an undetermined user input: the user will give a string and select
     *    a field from the autocompletion dropdown > this will search the selected
     *    field records with the given pattern (with an 'ilike' operator);
     * b. From a given selection: when given an input by the user, the searchbar
     *    will pre-fetch 'many2one' field records matching the input value and filter
     *    'select' fields with the same value. If the user clicks on one of these
     *    fetched/filtered values, it will generate a matching search facet targeting
     *    records having this exact value.
     * @extends Component
     */
    class SearchBar extends Component {
        constructor() {
            super(...arguments);

            this.focusOnUpdate = useAutofocus();
            this.inputRef = useRef('search-input');
            this.model = useModel('searchModel');
            this.state = useState({
                sources: [],
                focusedItem: 0,
                inputValue: "",
            });

            this.autoCompleteSources = this.model.get('filters', f => f.type === 'field').map(
                filter => this._createSource(filter)
            );
            this.noResultItem = [null, this.env._t("(no result)")];

            useExternalListener(window, 'click', this._onWindowClick);
            useExternalListener(window, 'keydown', this._onWindowKeydown);
        }

        mounted() {
            // 'search' will always patch the search bar, 'focus' will never.
            this.env.searchModel.on('search', this, this.focusOnUpdate);
            this.env.searchModel.on('focus-control-panel', this, () => {
                this.inputRef.el.focus();
            });
        }

        willUnmount() {
            this.env.searchModel.off('search', this);
            this.env.searchModel.off('focus-control-panel', this);
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _closeAutoComplete() {
            this.state.sources = [];
            this.state.focusedItem = 0;
            this.state.inputValue = "";
            this.inputRef.el.value = "";
            this.focusOnUpdate();
        }

        /**
         * @private
         * @param {Object} filter
         * @returns {Object}
         */
        _createSource(filter) {
            const field = this.props.fields[filter.fieldName];
            const type = field.type === "reference" ? "char" : field.type;
            const source = {
                active: true,
                description: filter.description,
                filterId: filter.id,
                filterOperator: filter.operator,
                id: sourceId ++,
                operator: CHAR_FIELDS.includes(type) ? 'ilike' : '=',
                parent: false,
                type,
            };
            switch (type) {
                case 'selection': {
                    source.active = false;
                    source.selection = field.selection || [];
                    break;
                }
                case 'boolean': {
                    source.active = false;
                    source.selection = [
                        [true, this.env._t("Yes")],
                        [false, this.env._t("No")],
                    ];
                    break;
                }
                case 'many2one': {
                    source.expand = true;
                    source.expanded = false;
                    source.context = field.context;
                    source.relation = field.relation;
                    if (filter.domain) {
                        source.domain = filter.domain;
                    }
                }
            }
            return source;
        }

        /**
         * @private
         * @param {Object} source
         * @param {[any, string]} values
         * @param {boolean} [active=true]
         */
        _createSubSource(source, [value, label], active = true) {
            const subSource = {
                active,
                filterId: source.filterId,
                filterOperator: source.filterOperator,
                id: sourceId ++,
                label,
                operator: '=',
                parent: source,
                value,
            };
            return subSource;
        }

        /**
         * @private
         * @param {Object} source
         * @param {boolean} shouldExpand
         */
        async _expandSource(source, shouldExpand) {
            source.expanded = shouldExpand;
            if (shouldExpand) {
                let args = source.domain;
                if (typeof args === 'string') {
                    try {
                        args = Domain.prototype.stringToArray(args);
                    } catch (err) {
                        args = [];
                    }
                }
                const results = await this.rpc({
                    kwargs: {
                        args,
                        context: source.context,
                        limit: 8,
                        name: this.state.inputValue.trim(),
                    },
                    method: 'name_search',
                    model: source.relation,
                });
                const options = results.map(result => this._createSubSource(source, result));
                const parentIndex = this.state.sources.indexOf(source);
                if (!options.length) {
                    options.push(this._createSubSource(source, this.noResultItem, false));
                }
                this.state.sources.splice(parentIndex + 1, 0, ...options);
            } else {
                this.state.sources = this.state.sources.filter(src => src.parent !== source);
            }
        }

        /**
         * @private
         * @param {string} query
         */
        _filterSources(query) {
            return this.autoCompleteSources.reduce(
                (sources, source) => {
                    // Field selection or boolean.
                    if (source.selection) {
                        const options = [];
                        source.selection.forEach(result => {
                            if (fuzzy.test(query, result[1].toLowerCase())) {
                                options.push(this._createSubSource(source, result));
                            }
                        });
                        if (options.length) {
                            sources.push(source, ...options);
                        }
                    // Any other type.
                    } else if (this._validateSource(query, source)) {
                        sources.push(source);
                    }
                    // Fold any expanded item.
                    if (source.expanded) {
                        source.expanded = false;
                    }
                    return sources;
                },
                []
            );
        }

        /**
         * Focus the search facet at the designated index if any.
         * @private
         */
        _focusFacet(index) {
            const facets = this.el.getElementsByClassName('o_searchview_facet');
            if (facets.length) {
                facets[index].focus();
            }
        }

        /**
         * Try to parse the given rawValue according to the type of the given
         * source field type. The returned formatted value is the one that will
         * supposedly be sent to the server.
         * @private
         * @param {string} rawValue
         * @param {Object} source
         * @returns {string}
         */
        _parseWithSource(rawValue, { type }) {
            const parser = field_utils.parse[type];
            let parsedValue;
            switch (type) {
                case 'date':
                case 'datetime': {
                    const parsedDate = parser(rawValue, { type }, { timezone: true });
                    const dateFormat = type === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD';
                    const momentValue = moment(parsedDate, dateFormat);
                    if (!momentValue.isValid()) {
                        throw new Error('Invalid date');
                    }
                    parsedValue = parsedDate.toJSON();
                    break;
                }
                case 'many2one': {
                    parsedValue = rawValue;
                    break;
                }
                default: {
                    parsedValue = parser(rawValue);
                }
            }
            return parsedValue;
        }

        /**
         * @private
         * @param {Object} source
         */
        _selectSource(source) {
            // Inactive sources are:
            // - Selection sources
            // - "no result" items
            if (source.active) {
                const labelValue = source.label || this.state.inputValue;
                this.model.dispatch('addAutoCompletionValues', {
                    filterId: source.filterId,
                    value: source.value || this._parseWithSource(labelValue, source),
                    label: labelValue,
                    operator: source.filterOperator || source.operator,
                });
            }
            this._closeAutoComplete();
        }

        /**
         * @private
         * @param {string} query
         * @param {Object} source
         * @returns {boolean}
         */
        _validateSource(query, source) {
            try {
                this._parseWithSource(query, source);
            } catch (err) {
                return false;
            }
            return true;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {Object} facet
         * @param {number} facetIndex
         * @param {KeyboardEvent} ev
         */
        _onFacetKeydown(facet, facetIndex, ev) {
            switch (ev.key) {
                case 'ArrowLeft':
                    if (facetIndex === 0) {
                        this.inputRef.el.focus();
                    } else {
                        this._focusFacet(facetIndex - 1);
                    }
                    break;
                case 'ArrowRight':
                    const facets = this.el.getElementsByClassName('o_searchview_facet');
                    if (facetIndex === facets.length - 1) {
                        this.inputRef.el.focus();
                    } else {
                        this._focusFacet(facetIndex + 1);
                    }
                    break;
                case 'Backspace':
                    this._onFacetRemove(facet);
                    break;
            }
        }

        /**
         * @private
         * @param {Object} facet
         */
        _onFacetRemove(facet) {
            this.model.dispatch('deactivateGroup', facet.groupId);
        }

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onSearchKeydown(ev) {
            if (ev.isComposing) {
                // This case happens with an IME for example: we let it handle all key events.
                return;
            }
            const currentItem = this.state.sources[this.state.focusedItem] || {};
            switch (ev.key) {
                case 'ArrowDown':
                    ev.preventDefault();
                    if (Object.keys(this.state.sources).length) {
                        let nextIndex = this.state.focusedItem + 1;
                        if (nextIndex >= this.state.sources.length) {
                            nextIndex = 0;
                        }
                        this.state.focusedItem = nextIndex;
                    } else {
                        this.env.bus.trigger('focus-view');
                    }
                    break;
                case 'ArrowLeft':
                    if (currentItem.expanded) {
                        // Priority 1: fold expanded item.
                        ev.preventDefault();
                        this._expandSource(currentItem, false);
                    } else if (currentItem.parent) {
                        // Priority 2: focus parent item.
                        ev.preventDefault();
                        this.state.focusedItem = this.state.sources.indexOf(currentItem.parent);
                        // Priority 3: Do nothing (navigation inside text).
                    } else if (ev.target.selectionStart === 0) {
                        // Priority 4: navigate to rightmost facet.
                        this._focusFacet(this.model.get("facets").length - 1);
                    }
                    break;
                case 'ArrowRight':
                    if (ev.target.selectionStart === this.state.inputValue.length) {
                        // Priority 1: Do nothing (navigation inside text).
                        if (currentItem.expand) {
                            // Priority 2: go to first child or expand item.
                            ev.preventDefault();
                            if (currentItem.expanded) {
                                this.state.focusedItem ++;
                            } else {
                                this._expandSource(currentItem, true);
                            }
                        } else if (ev.target.selectionStart === this.state.inputValue.length) {
                            // Priority 3: navigate to leftmost facet.
                            this._focusFacet(0);
                        }
                    }
                    break;
                case 'ArrowUp':
                    ev.preventDefault();
                    let previousIndex = this.state.focusedItem - 1;
                    if (previousIndex < 0) {
                        previousIndex = this.state.sources.length - 1;
                    }
                    this.state.focusedItem = previousIndex;
                    break;
                case 'Backspace':
                    if (!this.state.inputValue.length) {
                        const facets = this.model.get("facets");
                        if (facets.length) {
                            this._onFacetRemove(facets[facets.length - 1]);
                        }
                    }
                    break;
                case 'Enter':
                    if (!this.state.inputValue.length) {
                        this.model.dispatch('search');
                        break;
                    }
                    /* falls through */
                case 'Tab':
                    if (this.state.inputValue.length) {
                        this._selectSource(currentItem);
                    }
                    break;
                case 'Escape':
                    if (this.state.sources.length) {
                        this._closeAutoComplete();
                    }
                    break;
            }
        }

        /**
         * @private
         * @param {InputEvent} ev
         */
        _onSearchInput(ev) {
            this.state.inputValue = ev.target.value;
            const wasVisible = this.state.sources.length;
            const query = this.state.inputValue.trim().toLowerCase();
            if (query.length) {
                this.state.sources = this._filterSources(query);
            } else if (wasVisible) {
                this._closeAutoComplete();
            }
        }

        /**
         * Only handled if the user has moved its cursor at least once after the
         * results are loaded and displayed.
         * @private
         * @param {number} resultIndex
         */
        _onSourceMousemove(resultIndex) {
            this.state.focusedItem = resultIndex;
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onWindowClick(ev) {
            if (this.state.sources.length && !this.el.contains(ev.target)) {
                this._closeAutoComplete();
            }
        }

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onWindowKeydown(ev) {
            if (ev.key === 'Escape' && this.state.sources.length) {
                ev.preventDefault();
                ev.stopPropagation();
                this._closeAutoComplete();
            }
        }
    }

    SearchBar.defaultProps = {
        fields: {},
    };
    SearchBar.props = {
        fields: Object,
    };
    SearchBar.template = 'web.SearchBar';

    return SearchBar;
});
