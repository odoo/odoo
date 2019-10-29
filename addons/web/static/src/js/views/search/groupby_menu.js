odoo.define('web.GroupByMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var DropdownMenu = require('web.DropdownMenu');

var QWeb = core.qweb;
var _t = core._t;

var GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];

var DEFAULT_INTERVAL = 'month';

var GroupByMenu = DropdownMenu.extend({
    events: _.extend({}, DropdownMenu.prototype.events,
    {
        'click .o_add_custom_group': '_onAddCustomGroupClick',
        'click button.o_apply_group': '_onButtonApplyClick',
        'click .o_group_selector': '_onGroupSelectorClick',
    }),

    /**
     * @override
     * @param {Widget} parent
     * @param {Object[]} groupbys list of groupbys (type IGroupBy below)
     *   interface IGroupBy {
     *      itemId: string; unique id associated with the groupby
     *      fieldName: string; field name without interval!
     *      description: string; label printed on screen
     *      groupId: string;
     *      isDate: boolean;
     *      isActive: boolean; (optional) determines if the groupby is considered active
     *      isOpen: boolean; (optional) in case there are options the submenu presenting the options
     *                                is opened or closed according to isOpen
     *      isRemovable: boolean; (optional) can be removed from menu
     *      options: array of objects with 'optionId' and 'description' keys; (optional)
     *      currentOptionId: string refers to an optionId that is activated if item is active (optional)
     *   }
     * @param {Object} fields 'field_get' of a model: mapping from field name
     * to an object with its properties
     * @param {Object} options
     * @param {string} options.headerStyle conditions the style of the main button
     */
    init: function (parent, groupbys, fields, options) {
        var self = this;
        this.fields = fields;
        // determines when the 'Add custom groupby' submenu is open
        this.generatorMenuIsOpen = false;
        // determines list of options used by groupbys of type 'date'
        this.intervalOptions = [
            {description: _t('Day'), optionId: 'day', groupId: 1},
            {description: _t('Week'), optionId: 'week', groupId: 1},
            {description: _t('Month'), optionId: 'month', groupId: 1},
            {description: _t('Quarter'), optionId: 'quarter', groupId: 1},
            {description: _t('Year'), optionId: 'year', groupId: 1},
        ];
        this.defaultOptionId = DEFAULT_INTERVAL;
        this.groupableFields = [];
        _.each(fields, function (field, name) {
            if (field.sortable && _.contains(GROUPABLE_TYPES, field.type)) {
                self.groupableFields.push(_.extend({}, field, {
                    name: name,
                    isDate: _.contains(['date', 'datetime'], field.type),
                }));
            }
        });
        this.groupableFields = _.sortBy(this.groupableFields, 'string');
        _.each(groupbys, this._prepareItem.bind(this));
        // determines the list of field names that can be added to the menu
        // via the 'Add Custom Groupby' menu
        this.presentedFields = _.filter(this.groupableFields, function (field) {
            var groupByFields = _.pluck(groupbys, 'fieldName');
            return !_.contains(groupByFields, field.name);
        });
        // determines where the filter menu is displayed and partly its style
        this.isMobile = config.device.isMobile;
        // the default style of the groupby menu can be changed here using the options key 'headerStyle'
        var style;
        if (options && options.headerStyle === 'primary') {
            style = {
                el: {class: 'btn-group o_graph_groupbys_menu o_dropdown', attrs: {'role': 'group'}},
                mainButton: {class: 'btn btn-primary dropdown-toggle'},
            };
        }
        var dropdownHeader = {
            category: 'groupByCategory',
            title: _t('Group By'),
            icon: 'fa fa-bars',
            symbol: this.isMobile ? 'fa fa-chevron-right float-right mt4' : false,
            style: style,
        };
        this._super(parent, dropdownHeader, groupbys, options);
    },

    /**
     * render the template used to add a new custom groupby and append it
     * to the basic dropdown menu
     *
     * @private
     */
    start: function () {
        this._super.apply(this, arguments);
        this.$menu.addClass('o_group_by_menu');
        var $generatorMenu = QWeb.render('GroupbyMenuGenerator', {widget: this});
        this.$menu.append($generatorMenu);
        this.$addCustomGroup = this.$menu.find('.o_add_custom_group');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * method called via the 'Add Custom Groupby' menu to create
     * a new groupby and add it (activated) to the menu
     * In case the field is of type date, it is activated using
     * the option determined by the parameter 'DEFAULT_INTERVAL'
     *
     * @private
     * @param {string} fieldName
     */
    _addGroupby: function (fieldName) {
        var field = _.findWhere(this.groupableFields, {name: fieldName});
        var groupbyName = _.uniqueId('__groupby__');
        var groupby = {
            itemId: groupbyName,
            description: field.string,
            fieldName: fieldName,
            groupId: _.uniqueId('__group__'),
            isActive: true,
        };
        var eventData = _.clone(groupby);
        this._prepareItem(groupby);
        if (groupby.hasOptions) {
            groupby.defaultOptionId = DEFAULT_INTERVAL;
            groupby.currentOptionId = DEFAULT_INTERVAL;
            groupby.isDate = true;
            eventData.optionId = groupby.currentOptionId;
            eventData.isDate = true;
        }
        this.items.push(groupby);
        var fieldIndex = this.presentedFields.indexOf(field);
        this.presentedFields.splice(fieldIndex, 1);
        this._renderGeneratorMenu();
        this._renderMenuItems();
        this.trigger_up('new_groupby', eventData);
    },
    /**
     * override
     *
     * @private
     * @param {Object} item
     */
     _prepareItem: function (item) {
        if (_.contains(['date', 'datetime'], this.fields[item.fieldName].type)) {
            item.options = this.intervalOptions;
        }
        // super has to be called here because we need to add options to groupby
        // before to call it since some keys in a groupby are initialized using
        // the keys 'options' and 'defaultOptionId'
        this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _renderGeneratorMenu: function () {
        this.$el.find('.o_generator_menu').remove();
        var $generatorMenu = QWeb.render('GroupbyMenuGenerator', {widget: this});
        this.$menu.append($generatorMenu);
        this.$addCustomGroup = this.$menu.find('.o_add_custom_group');
        this.$groupSelector = this.$menu.find('.o_group_selector');
    },
    /**
     * @private
     */
    _toggleCustomGroupMenu: function () {
        this.generatorMenuIsOpen = !this.generatorMenuIsOpen;
        this._renderGeneratorMenu();
        this.$addCustomGroup.attr('aria-expanded', this.generatorMenuIsOpen);
        if (this.generatorMenuIsOpen) {
            this.$groupSelector.focus();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * toggle the 'Add Custom Group'
     *
     * @private
     * @param {MouseEvent} event
     */
    _onAddCustomGroupClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this._toggleCustomGroupMenu();
    },
    /*
     * override
     *
     * @private
     * @param {jQueryEvent} event
     */
    _onBootstrapClose: function () {
        this._super.apply(this, arguments);
        this.generatorMenuIsOpen = false;
        this._renderGeneratorMenu();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onButtonApplyClick: function (event) {
        event.stopPropagation();
        var fieldName = this.$groupSelector.val();
        this._addGroupby(fieldName);
        this._toggleCustomGroupMenu();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onGroupSelectorClick: function (event) {
        event.stopPropagation();
    },
});

return GroupByMenu;

});
