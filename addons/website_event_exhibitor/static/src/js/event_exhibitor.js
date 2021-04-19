odoo.define('website_event_exhibitor.event_exhibitor', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
publicWidget.registry.eventExhibitor = publicWidget.Widget.extend({
    selector: '.o_wesponsor_index',
    events: {
        'click .dropdown-menu a': '_onAddFilter',
        'click .o_wesponsor_search_tag a': '_onRemoveFilter',
        'input .o_wesearch_bar': '_onSearch',
    },

    /**
     * @override
     */
    start: function () {
        this.$container = this.$el.find('.o_wesponsor_active_search_tags');
        this.term = ''
        this.activeTags = new Map([
            ['country', []],
            ['level', []]
        ]);
        return this._super.apply(this, arguments);
    },

    /**
     * 
     * @param {OdooEvent} event
     */
    _onSearch: function (event) {
        event.preventDefault();
        this.term = $(event.target).val();
        this.applyFilter();
    },

    /**
     * 
     * @param {OdooEvent} event
     */
    _onAddFilter: function (event) {
        event.preventDefault();
        const $link = $(event.target);
        const group = $link.closest('.dropdown-menu').data('group');
        const value = $link.data('value');
        if (this.addFilter(group, value)) {
            const $tag = this.renderTag(group, value);
            this.$container.append($tag);
        }
    },

    /**
     * @param {String} group
     * @param {String} value
     * @returns {boolean}
     */
    addFilter: function (group, value) {
        if (!this.activeTags.has(group)) {
            return false;
        }
        const values = this.activeTags.get(group);
        if (values.includes(value)) {
            return false;
        }
        this.activeTags.set(group, [...values, value]);
        this.applyFilter();
        return true;
    },

    applyFilter: function () {
        this.$el.find('.o_wesponsor_card').each((index, card) => {
            const $card = $(card);
            if (this.matchWithTags($card) && this.matchWithTerms($card)) {
                $card.parent().show();
            } else {
                $card.parent().hide();
            }
        });
    },

    /**
     * Returns true if the card matches with the selected tags. Otherwise returns false.
     * @param {Object} predicates
     * @returns {Function}
     */
    matchWithTags: function ($card) {
        const data = this.extractData($card);
        for (let [group, tags] of this.activeTags) {
            if (tags.length === 0) {
                continue;
            }
            if (!tags.includes(data[group])) {
                return false;
            }
        }
        return true;
    },

    /**
     * @param {OdooEvent} event
     */
    _onRemoveFilter: function (event) {
        event.preventDefault();
        const $tag = $(event.target).parent();
        const data = $tag.data();
        if (this.removeFilter(data.group, data.value)) {
            $tag.remove();
        }
    },

    // Helpers:

    /**
     * @param {jQuery} $card
     */
    extractData: function ($card) {
        const $image = $card.find('img');
        const $group = $card.closest('.o_wesponsor_category');
        return {
            country: $image.attr('alt').trim() || '',
            level: $group.find('h2').text().trim() || ''
        }
    },

    /**
     * @param {String} group
     * @param {String} value
     */
    removeFilter: function (group, value) {
        if (!this.activeTags.has(group)) {
            return false;
        }
        const values = this.activeTags.get(group);
        this.activeTags.set(group, values.filter(elem => elem !== value));
        this.applyFilter();
        return true;
    },

    /**
     * @param {String} group Group
     * @param {String} value Value
     */
    renderTag: function (group, value) {
        return $(
            '<span ' +
                'data-group="' + group + '" ' +
                'data-value="' + value + '" ' +
                'class="o_wesponsor_search_tag align-items-baseline border d-inline-flex pl-2 mt-3 rounded ml16 mb-2 bg-white">' +
                '<i class="fa fa-tag mr-2 text-muted"/>' +
                value +
                '<a href="#" class="btn border-0 py-1">&#215;</a>' +
            '</span>'
        );
    },

    /**
     * Returns true if the card matches with the provided term. Otherwise, returns false.
     * @param {jQuery} $card
     * @returns {boolean}
     */
    matchWithTerms: function ($card) {
        let active = false
        active = this.highlight($card.find('.card-title > span:first')) || active;
        active = this.highlight($card.find('.card-body > span:first')) || active;
        const term = this.term.trim().toLowerCase();
        if (term.length > 0) {
            $.each(this.extractData($card), (key, str) => {
                active = (str.toLowerCase().indexOf(term) >= 0) || active;
            });
        }
        return active;
    },

    /**
     * Returns true of the element has been highlighted, false otherwise.
     * @param {jQuery} $elem
     * @returns {boolean}
     */
    highlight: function ($elem) {
        const text = $elem.text();
        if (this.term.length === 0) {
            $elem.empty();
            $elem.append(text);
            return true;
        }
        const pattern = new RegExp('(' + this.escape(this.term) + ')', 'gi');
        if (!pattern.test(text)) {
            $elem.empty();
            $elem.append(text);
            return false;
        }
        $elem.empty();
        $elem.append(text.replaceAll(pattern, '<mark>$1</mark>'));
        return true;
    },

    /**
     * Escapes regular expression special characters.
     * @param {String} string
     */
    escape: function (string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },
});

return {
    eventExhibitor: publicWidget.registry.eventExhibitor,
};
});
