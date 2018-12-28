odoo.define('web.FilterMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var DropdownMenu = require('web.DropdownMenu');
var search_filters = require('web.search_filters');
var time = require('web.time');

var _t = core._t;
var QWeb = core.qweb;

var FilterMenu = DropdownMenu.extend({
    custom_events: {
        confirm_proposition: '_onConfirmProposition',
        remove_proposition: '_onRemoveProposition',
    },
    events: _.extend({}, DropdownMenu.prototype.events, {
        'click .o_add_custom_filter': '_onAddCustomFilterClick',
        'click .o_add_condition': '_onAddCondition',
        'click .o_apply_filter': '_onApplyClick',
    }),
    /**
     * @override
     * @param {Object} fields
     */
    init: function (parent, filters, fields) {
        this._super(parent, filters);

        // determines where the filter menu is displayed and its style
        this.isMobile = config.device.isMobile;
        // determines when the 'Add custom filter' submenu is open
        this.generatorMenuIsOpen = false;
        this.propositions = [];
        this.fields = _.pick(fields, function (field, name) {
            return field.selectable !== false && name !== 'id';
        });
        this.fields.id = {string: 'ID', type: 'id', searchable: true};
        this.dropdownCategory = 'filter';
        this.dropdownTitle = _t('Filters');
        this.dropdownIcon = 'fa fa-filter';
        this.dropdownSymbol = this.isMobile ?
                                'fa fa-chevron-right float-right mt4' :
                                false;
        this.dropdownStyle.mainButton.class = 'o_filters_menu_button ' +
                                                this.dropdownStyle.mainButton.class;
    },
    /**
     * Render the template used to add a new custom filter and append it
     * to the basic dropdown menu.
     *
     * @override
     */
    start: function () {
        this.$menu = this.$('.o_dropdown_menu');
        this.$menu.addClass('o_filters_menu');
        this._renderGeneratorMenu();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a proposition inside the custom filter edition menu.
     *
     * @private
     * @returns {$.Deferred}
     */
    _appendProposition: function () {
        // make modern sear_filters code!!! It works but...
        var prop = new search_filters.ExtendedSearchProposition(this, this.fields);
        this.propositions.push(prop);
        this.$('.o_apply_filter').prop('disabled', false);
        prop.insertBefore(this.$addFilterMenu);
    },
    /**
     * Confirm a filter proposition, creates it and add it to the menu.
     *
     * @private
     */
    _commitSearch: function () {
        var filters = _.invoke(this.propositions, 'get_filter').map(function (preFilter) {
            return {
                type: 'filter',
                description: preFilter.attrs.string,
                domain: Domain.prototype.arrayToString(preFilter.attrs.domain),
            };
        });
        // TO DO intercepts 'new_filters' and decide what to do whith filters
        //  rewrite web.search_filters?
        this.trigger_up('new_filters', {filters: filters});
        _.invoke(this.propositions, 'destroy');
        this.propositions = [];
        this._toggleCustomFilterMenu();
    },
    /**
     * @private
     */
    _renderGeneratorMenu: function () {
        this.$el.find('.o_generator_menu').remove();
        if (!this.generatorMenuIsOpen) {
            _.invoke(this.propositions, 'destroy');
            this.propositions = [];
        }
        var $generatorMenu = QWeb.render('FilterMenuGenerator', {widget: this});
        this.$menu.append($generatorMenu);
        this.$addFilterMenu = this.$menu.find('.o_add_filter_menu');
        if (this.generatorMenuIsOpen && !this.propositions.length) {
            this._appendProposition();
        }
    },
    /**
     * @override
     * @private
     */
    _renderMenuItems: function () {
        var self= this;
        this._super.apply(this, arguments);
        // the following code adds tooltip on date options in order
        // to alert the user of the meaning of intervals
        var $options = this.$('.o_item_option');
        $options.each(function () {
            var $option = $(this);
            $option.tooltip({
                delay: { show: 500, hide: 0 },
                title: function () {
                    var itemId = $option.attr('data-item_id');
                    var optionId = $option.attr('data-option_id');
                    var fieldName = _.findWhere(self.items, {id: itemId}).fieldName;
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
     * Hide and display the submenu which allows adding custom filters.
     *
     * @private
     */
    _toggleCustomFilterMenu: function () {
        this.generatorMenuIsOpen = !this.generatorMenuIsOpen;
        this._renderGeneratorMenu();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddCondition: function (ev) {
        ev.stopPropagation();
        this._appendProposition();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddCustomFilterClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._toggleCustomFilterMenu();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onApplyClick: function (ev) {
        ev.stopPropagation();
        this._commitSearch();
    },
    /**
     * @override
     * @private
     * @param {jQueryEvent} ev
     */
    _onBootstrapClose: function () {
        this._super.apply(this, arguments);
        this.generatorMenuIsOpen = false;
        this._renderGeneratorMenu();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onConfirmProposition: function (ev) {
        ev.stopPropagation();
        this._commitSearch();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onRemoveProposition: function (ev) {
        ev.stopPropagation();
        this.propositions = _.without(this.propositions, ev.target);
        if (!this.propositions.length) {
            this.$('.o_apply_filter').prop('disabled', true);
        }
        ev.target.destroy();
    },
});

return FilterMenu;

});
