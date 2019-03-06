odoo.define('web.FiltersMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var DropdownMenu = require('web.DropdownMenu');
var search_filters = require('web.search_filters');
var time = require('web.time');
var TimeRangeMenuOptions = require('web.TimeRangeMenuOptions');

var QWeb = core.qweb;
var _t = core._t;

var PERIOD_OPTIONS = TimeRangeMenuOptions.PeriodOptions;

var DEFAULT_PERIOD = 'this_month';

var FiltersMenu = DropdownMenu.extend({
    custom_events: {
        remove_proposition: '_onRemoveProposition',
        confirm_proposition: '_onConfirmProposition',
    },
    events: _.extend({}, DropdownMenu.prototype.events, {
        'click .o_add_custom_filter': '_onAddCustomFilterClick',
        'click .o_add_condition': '_appendProposition',
        'click .o_apply_filter': '_onApplyClick',
        ':hover .o_item_option': '_onOptionHover',
    }),

    /**
     * @override
     * @param {Widget} parent
     * @param {Object[]} filters list of filters (type IFilter below)
     *   interface IFilter {
     *      itemId: string; unique id associated with the filter
     *      domain: string;
     *      isPeriod: boolean
     *      fieldName: string; fieldName used to generate a domain in case isDate is true (and domain empty)
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
     * @param {Object} fields
     */
    init: function (parent, filters, fields) {
        // determines where the filter menu is displayed and its style
        this.isMobile = config.device.isMobile;
        // determines list of options used by filter of type 'date'
        this.periodOptions = PERIOD_OPTIONS;
        this.defaultOptionId = DEFAULT_PERIOD;
        // determines when the 'Add custom filter' submenu is open
        this.generatorMenuIsOpen = false;
        this.propositions = [];
        this.fields = _.pick(fields, function (field, name) {
            return field.selectable !== false && name !== 'id';
        });
        this.fields.id = {string: 'ID', type: 'id', searchable: true};
        var dropdownHeader = {
            category: 'filterCategory',
            title: _t('Filters'),
            icon: 'fa fa-filter',
            symbol: this.isMobile ? 'fa fa-chevron-right float-right mt4' : false,
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
        this.$menu = this.$('.o_dropdown_menu');
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
        _.each(filters, function (filter) {
            filter.attrs.domain = Domain.prototype.arrayToString(filter.attrs.domain);
        });
        var groupId = _.uniqueId('__group__');
        var data = [];
        filters.forEach(function (filter) {
            var filterName = _.uniqueId('__filter__');
            var filterItem = {
                itemId: filterName,
                description: filter.attrs.string,
                groupId: groupId,
                isActive: true,
            };
            self._prepareItem(filterItem);
            data.push({
                itemId: filterName,
                groupId: groupId,
                filter: filter,
            });
            self.items.push(filterItem);
        });
        this._renderMenuItems();
        this.trigger_up('new_filters', data);
        _.invoke(this.propositions, 'destroy');
        this.propositions = [];
        this._toggleCustomFilterMenu();
    },
    /**
     * override
     *
     * @private
     * @param {Object} item
     */
     _prepareItem: function (item) {
        if (item.isPeriod) {
            item.options = this.periodOptions;
        }
        this._super.apply(this, arguments);
    },
    /**
     * override
     *
     * @private
     */
    _renderMenuItems: function () {
        var self= this;
        this._super.apply(this, arguments);
        // the following code adds tooltip on date options in order
        // to alert the user of the meaning of intervals
        var $options = this.$('.o_filters_menu .o_item_option');
        $options.each(function () {
            var $option = $(this);
            $option.tooltip({
                delay: { show: 500, hide: 0 },
                title: function () {
                    var itemId = $option.attr('data-item_id');
                    var optionId = $option.attr('data-option_id');
                    var fieldName = _.findWhere(self.items, {itemId: itemId}).fieldName;
                    var domain = Domain.prototype.constructDomain(fieldName, optionId, 'date', true);
                    var evaluatedDomain = Domain.prototype.stringToArray(domain);
                    var dateFormat = time.getLangDateFormat();
                    var dateStart = moment(evaluatedDomain[1][2], "YYYY-MM-DD", 'en').format(dateFormat);
                    var dateEnd = moment(evaluatedDomain[2][2], "YYYY-MM-DD", 'en').format(dateFormat);
                    if (optionId === 'today' || optionId === 'yesterday') {
                        return dateStart;
                    }
                    return _.str.sprintf(_t('From %s To %s'), dateStart, dateEnd);
                }
            });
        });
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
                .attr('aria-expanded', self.generatorMenuIsOpen)
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
