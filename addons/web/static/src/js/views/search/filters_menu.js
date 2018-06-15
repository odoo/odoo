odoo.define('web.FiltersMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var DropdownMenu = require('web.DropdownMenu');
var search_filters = require('web.search_filters');

var QWeb = core.qweb;
var _t = core._t;



var FiltersMenu = DropdownMenu.extend({
    custom_events: {
        remove_proposition: '_onRemoveProposition',
        confirm_proposition: '_onConfirmProposition',
    },
    events: _.extend({}, DropdownMenu.prototype.events, {
        'click .o_add_custom_filter': '_onAddCustomFilterClick',
        'click .o_add_condition': '_appendProposition',
        'click .o_apply_filter': '_onApplyClick',
    }),

    /**
     * @override
     * @param {Widget} parent
     * @param {Object[]} filters list of filters (type IFilter below)
     *   interface IFilter {
     *      itemId: string; unique id associated with the filter
     *      domain: string;
     *      description: string; label printed on screen
     *      groupId: string;
     *      isActive: boolean; (optional) determines if the filter is considered active
     *      isOpen: boolean; (optional) in case there are options the submenu presenting the options
     *                                is opened or closed according to isOpen
     *      isRemovable: boolean; (optional) can be removed from menu
     *      options: array of objects with 'optionId' and 'description' keys; (optional)
     *      defaultOptionId: string refers to an optionId (optional)
     *      currentOptionId: string refers to an optionId that is activated if item is active (optional)
     *   }
     * @param {Object} fields 'field_get' of a model: mapping from field name
     * to an object with its properties
     */
    init: function (parent, filters, fields) {
        // determines where the filter menu is displayed and its style
        this.isMobile = config.device.isMobile;
        // determines list of options used by filter of type 'date'
        // TO DO: simplify optionIds below
        this.intervalOptions = [
            {description: _t('Day'), optionId: '__interval__day__'},
            {description: _t('Week'), optionId: '__interval__week__'},
            {description: _t('Month'), optionId: '__interval__month__'},
            {description: _t('Year'), optionId: '__interval__year__'},
        ];
        // determines the default option used in case
        // it has not been provided for a filter
        this.defaultOptionId = "__interval__month__";
        // determines when the 'Add custom filter' submenu is open
        this.generatorMenuIsOpen = false;
        this.propositions = [];
        this.fields = _.pick(fields, function (field, name) {
            return field.selectable !== false && name !== 'id';
        });
        this.fields.id = {string: 'ID', type: 'id', searchable: true};
        var dropdownHeader = {
            category: 'filterCategory',
            title: 'Filters',
            icon: 'fa fa-filter',
            symbol: this.isMobile ? 'fa fa-chevron-right pull-right mt4' : 'caret'
        };
        this._super(parent, dropdownHeader, filters, this.fields);
    },

    /**
     * render the template used to add a new custom filter and append it
     * to the basic dropdown menu
     *
     * @private
     */
    start: function () {
        this.$menu = this.$('ul.o_dropdown_menu');
        this.$menu.addClass('o_filters_menu');
        var generatorMenu = QWeb.render('FiltersMenuGenerator', {widget: this});
        this.$menu.append(generatorMenu);
        this.$addCustomFilter = this.$menu.find('.o_add_custom_filter');
        this.$addFilterMenu = this.$menu.find('.o_add_filter_menu');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a proposition inside the custom filter edition menu
     *
     * @private
     * @returns {$.Deferred}
     */
    _appendProposition: function () {
        var prop = new search_filters.ExtendedSearchProposition(this, this.fields);
        this.propositions.push(prop);
        this.$('.o_apply_filter').prop('disabled', false);
        return prop.insertBefore(this.$addFilterMenu);
    },
    /**
     * Confirm a filter selection, creates it and add it to the menu
     *
     * @private
     */
    _commitSearch: function () {
        var self = this;
        var filters = _.invoke(this.propositions, 'get_filter');
        var groupId = _.uniqueId('__group__');
        var toSendToSearchView = [];
        filters.forEach(function (filter) {
            var filterName = _.uniqueId('__filter__');
            var filterItem = {
                itemId: filterName,
                description: filter.attrs.string,
                groupId: groupId,
                isActive: true,
            };
            self._prepareItem(filterItem);
            toSendToSearchView.push({
                itemId: filterName,
                groupId: groupId,
                filter: filter,
            });
            self.items.push(filterItem);
        });
        this._renderMenuItems();
        this.trigger_up('new_filter', toSendToSearchView);
        _.invoke(this.propositions, 'destroy');
        this.propositions = [];
        // this._appendProposition();
        this._toggleCustomFilterMenu();
    },
    /**
     * Hide and display the sub menu which allows adding custom filters
     *
     * @private
     */
    _toggleCustomFilterMenu: function () {
        var self = this;
        this.generatorMenuIsOpen = !this.generatorMenuIsOpen;
        var def;
        if (this.generatorMenuIsOpen && !this.propositions.length) {
            def = this._appendProposition();
        }
        if (!this.generatorMenuIsOpen) {
            _.invoke(this.propositions, 'destroy');
            this.propositions = [];
        }
        $.when(def).then(function () {
            self.$addCustomFilter
                .toggleClass('o_closed_menu', !self.generatorMenuIsOpen)
                .toggleClass('o_open_menu', self.generatorMenuIsOpen);
            self.$('.o_add_filter_menu').toggle();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddCustomFilterClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this._toggleCustomFilterMenu();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onApplyClick: function (event) {
        event.stopPropagation();
        this._commitSearch();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onConfirmProposition: function (event) {
        event.stopPropagation();
        this._commitSearch();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onRemoveProposition: function (event) {
        event.stopPropagation();
        this.propositions = _.without(this.propositions, event.target);
        if (!this.propositions.length) {
            this.$('.o_apply_filter').prop('disabled', true);
        }
        event.target.destroy();
    },
});

return FiltersMenu;

});
