odoo.define('web.SearchFacet', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

var SearchFacet = Widget.extend({
    template: 'SearchView.SearchFacet',
    events: _.extend({}, Widget.prototype.events, {
        'click .o_facet_remove': '_onFacetRemove',
        'compositionend': '_onCompositionend',
        'compositionstart': '_onCompositionstart',
        'keydown': '_onKeydown',
    }),
    /**
     * @override
     * @param {Object} facet
     */
    init: function (parent, facet) {
        this._super.apply(this, arguments);

        var self = this;
        this.facet = facet;
        this.facetValues = _.map(this.facet.filters, function (filter) {
            return self._getFilterDescription(filter);
        });
        this.separator = this._getSeparator();
        this.icon = this._getIcon();
        this._isComposing = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the correct description according to filter.
     *
     * @private
     * @returns {string}
     */
    _getFilterDescription: function (filter) {
        if (filter.type === 'field') {
            var values = _.pluck(filter.autoCompleteValues, 'label');
            return values.join(_t(' or '));
        }
        var description = filter.description;
        if (filter.hasOptions) {
            if (filter.type === 'filter') {
                const optionDescriptions = [];
                const sortFunction = (o1, o2) =>
                    filter.options.findIndex(o => o.optionId === o1) - filter.options.findIndex(o => o.optionId === o2);
                const p = _.partition([...filter.currentOptionIds], optionId =>
                    filter.options.find(o => o.optionId === optionId).groupId === 1);
                const yearIds = p[1].sort(sortFunction);
                const otherOptionIds = p[0].sort(sortFunction);
                // the following case corresponds to years selected only
                if (otherOptionIds.length === 0) {
                    yearIds.forEach(yearId => {
                        const d = filter.basicDomains[yearId];
                        optionDescriptions.push(d.description);
                    });
                } else {
                    otherOptionIds.forEach(optionId => {
                        yearIds.forEach(yearId => {
                            const d = filter.basicDomains[yearId + '__' + optionId];
                            optionDescriptions.push(d.description);
                        });
                    });
                }
                description += ': ' + optionDescriptions.join('/');
            } else {
                description = description += ': ' +
                                filter.options.find(o => o.optionId === filter.optionId).description;
            }
        }
        if (filter.type === 'timeRange') {
            var timeRangeValue =_.findWhere(filter.timeRangeOptions, {
                optionId: filter.timeRangeId,
            });
            description += ': ' + timeRangeValue.description;
            if (filter.comparisonTimeRangeId) {
                var comparisonTimeRangeValue =_.findWhere(filter.comparisonTimeRangeOptions, {
                    optionId: filter.comparisonTimeRangeId,
                });
                description += ' / ' + comparisonTimeRangeValue.description;
            }
        }
        return description;
    },
    /**
     * Get the correct icon according to facet type.
     *
     * @private
     * @returns {string}
     */
    _getIcon: function () {
        var icon;
        if (this.facet.type === 'filter') {
            icon = 'fa-filter';
        } else if (this.facet.type === 'groupBy') {
            icon = 'fa-bars';
        } else if (this.facet.type === 'favorite') {
            icon = 'fa-star';
        } else if (this.facet.type === 'timeRange') {
            icon = 'fa-calendar';
        }
        return icon;
    },
    /**
     * Get the correct separator according to facet type.
     *
     * @private
     * @returns {string}
     */
    _getSeparator: function () {
        var separator;
        if (this.facet.type === 'filter') {
            separator = _t('or');
        } else if (this.facet.type === 'field') {
            separator = _t('or');
        } else if (this.facet.type === 'groupBy') {
            separator = '>';
        }
        return separator;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CompositionEvent} ev
     */
    _onCompositionend: function (ev) {
        this._isComposing = false;
    },
    /**
     * @private
     * @param {CompositionEvent} ev
     */
    _onCompositionstart: function (ev) {
        this._isComposing = true;
    },
    /**
     * @private
     */
    _onFacetRemove: function () {
        this.trigger_up('facet_removed', {group: this.facet});
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        if (this._isComposing) {
            return;
        }
        switch (ev.which) {
            case $.ui.keyCode.BACKSPACE:
                this.trigger_up('facet_removed', {group: this.facet});
                break;
        }
    },
});

return SearchFacet;

});
