odoo.define('web.GroupByMenu', function (require) {
"use strict";

var config = require('web.config');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var core = require('web.core');
var DropdownMenu = require('web.DropdownMenu');

var _t = core._t;
var QWeb = core.qweb;

var DEFAULT_INTERVAL = controlPanelViewParameters.DEFAULT_INTERVAL;
var GROUPABLE_TYPES = controlPanelViewParameters.GROUPABLE_TYPES;
var INTERVAL_OPTIONS = controlPanelViewParameters.INTERVAL_OPTIONS;

var GroupByMenu = DropdownMenu.extend({
    events: _.extend({}, DropdownMenu.prototype.events, {
        'click .o_add_custom_group': '_onAddCustomGroupClick',
        'click button.o_apply_group': '_onButtonApplyClick',
        'click .o_group_selector': '_onGroupSelectorClick',
    }),
    /**
     * @override
     * @param {Widget} parent
     * @param {Object[]} groupBys list of groupBys
     *   }
     * @param {Object} fields 'field_get' of a model: mapping from field name
     *   to an object with its properties
     * @param {Object} options
     * @param {string} options.headerStyle conditions the style of the main button
     */
    init: function (parent, groupBys, fields, options) {
        var self = this;
        options = options || {};
        this._super(parent, groupBys);
        this.fields = fields;
        // determines when the 'Add custom groupby' submenu is open
        this.generatorMenuIsOpen = false;
        // determines list of options used by groupBys of type 'date'
        this.groupableFields = [];
        _.each(fields, function (field, name) {
            if (field.sortable && name !== "id" && _.contains(GROUPABLE_TYPES, field.type)) {
                self.groupableFields.push(_.extend({}, field, {
                    name: name,
                }));
            }
        });
        this.groupableFields = _.sortBy(this.groupableFields, 'string');
        // determines the list of field names that can be added to the menu
        // via the 'Add Custom Groupby' menu
        this.presentedFields = this._setPresentedFields(groupBys);

        // determines where the filter menu is displayed and partly its style
        this.isMobile = config.device.isMobile;

        this.dropdownCategory = 'groupby';
        this.dropdownTitle = _t('Group By');
        this.dropdownIcon = 'fa fa-bars';
        this.dropdownSymbol = this.isMobile && !options.noSymbol ? 'fa fa-chevron-right float-right mt4' : false;
        // the default style of the groupby menu can be changed here using the options key 'headerStyle'
        if (options.headerStyle === 'primary') {
            this.dropdownStyle = {
                el: {class: 'btn-group o_group_by_menu o_dropdown', attrs: {'role': 'group'}},
                mainButton: {class: 'btn btn-primary dropdown-toggle'},
            };
        }
        INTERVAL_OPTIONS = INTERVAL_OPTIONS.map(function (option) {
            return _.extend(option, {description: option.description.toString()});
        });
    },

    /**
     * Render the template used to add a new custom groupby and append it
     * to the basic dropdown menu.
     *
     * @override
     */
    start: function () {
        var superProm = this._super.apply(this, arguments);
        this.$menu.addClass('o_group_by_menu');
        this._renderGeneratorMenu();
        return superProm;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object[]} groupBys
     */
    update: function (groupBys) {
        this._super.apply(this, arguments);
        this.presentedFields = this._setPresentedFields(groupBys);
        this._renderGeneratorMenu();
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method called via the 'Add Custom Groupby' menu to create a new groupby
     * and add it (activated) to the menu. In case the field is of type date, it
     * is activated using the option determined by the parameter
     * 'DEFAULT_INTERVAL'.
     *
     * @private
     * @param {string} fieldName
     */
    _addGroupby: function (fieldName) {
        var field = this.presentedFields.find(function (field) {
            return field.name === fieldName;
        });
        var groupBy = {
            type: 'groupBy',
            description: field.string,
            fieldName: fieldName,
            fieldType: field.type,
        };
        if (_.contains(['date', 'datetime'], field.type)) {
            groupBy.hasOptions = true;
            groupBy.options = INTERVAL_OPTIONS;
            groupBy.defaultOptionId = DEFAULT_INTERVAL;
            groupBy.currentOptionIds = new Set([]);
        }
        this.trigger_up('new_groupBy', groupBy);
    },
    /**
     * @private
     */
    _renderGeneratorMenu: function () {
        this.$el.find('.o_generator_menu').remove();
        var $generatorMenu = QWeb.render('GroupByMenuGenerator', {widget: this});
        this.$menu.append($generatorMenu);
        this.$addCustomGroup = this.$menu.find('.o_add_custom_group');
        this.$groupSelector = this.$menu.find('.o_group_selector');
        this.$dropdownReference.dropdown('update');
    },
    /**
     * @private
     */
    _setPresentedFields: function (groupBys) {
        return this.groupableFields.filter(function (field) {
            var groupByFields = _.pluck(groupBys, 'fieldName');
            return !_.contains(groupByFields, field.name);
        });
    },
    /**
     * @private
     */
    _toggleCustomGroupMenu: function () {
        this.generatorMenuIsOpen = !this.generatorMenuIsOpen;
        this._renderGeneratorMenu();
        if (this.generatorMenuIsOpen) {
            this.$groupSelector.focus();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the 'Add Custom Group'.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddCustomGroupClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._toggleCustomGroupMenu();
    },
    /*
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
     * @param {MouseEvent} ev
     */
    _onButtonApplyClick: function (ev) {
        ev.stopPropagation();
        var fieldName = this.$groupSelector.val();
        this.generatorMenuIsOpen = false;
        this._addGroupby(fieldName);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onGroupSelectorClick: function (ev) {
        ev.stopPropagation();
    },
});

return GroupByMenu;

});
