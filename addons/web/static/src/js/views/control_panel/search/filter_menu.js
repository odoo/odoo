odoo.define('web.FilterMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var DropdownMenu = require('web.DropdownMenu');
var search_filters = require('web.search_filters');

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
        var superProm = this._super.apply(this, arguments);
        this.$menu.addClass('o_filters_menu');
        this._renderGeneratorMenu();
        return superProm;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a proposition inside the custom filter edition menu.
     *
     * @private
     * @returns {Promise}
     */
    _appendProposition: function () {
        // make modern sear_filters code!!! It works but...
        var prop = new search_filters.ExtendedSearchProposition(this, this.fields);
        this.propositions.push(prop);
        this.$('.o_apply_filter').prop('disabled', false);
        return prop.insertBefore(this.$addFilterMenu);
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
        this.$dropdownReference.dropdown('update');
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
