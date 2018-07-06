odoo.define('web.DropdownMenu', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;



var DropdownMenu = Widget.extend({
    template: 'web.DropdownMenu',
    events: {
        'click li.o_menu_item': '_onItemClick',
        'click li.o_item_option': '_onOptionClick',
        'click span.o_trash_button': '_onTrashClick',
        'hidden.bs.dropdown': '_onBootstrapClose',
    },

    /**
     * override
     *
     * @param {Widget} parent
     * @param {Object} dropdowHeader object used to customize the dropdown menu. The keys:
     *                      - 'title' (e.g. 'Group By')
     *                      - 'icon' (e.g. 'fa-bars')
     *                      - 'symbol' (e.g. 'caret')
     *                      - 'category' (describes the type of items)
     *                      - 'style' (button style)
     * @param {Object} items list of menu items (type IGMenuItem below)
     *   interface IMenuItem {
     *      itemId: string; (optional) unique id associated with the item
     *      description: string; label printed on screen
     *      groupId: string;
     *      isActive: boolean; (optional) determines if the item is considered active
     *      isOpen: boolean; (optional) in case there are options the submenu presenting the options
     *                                is opened or closed according to isOpen
     *      isRemovable: boolean; (optional) can be removed from menu
     *      options: array of objects with 'optionId' and 'description' keys; (optional)
     *      currentOptionId: string refers to an optionId that is activated if item is active (optional)
     *   }
     */
    init: function (parent, dropdownHeader, items) {
        this._super(parent);
        this.dropdownCategory = dropdownHeader.category;
        this.dropdownTitle = dropdownHeader.title;
        this.dropdownIcon = dropdownHeader.icon;
        this.dropdownSymbol = dropdownHeader.symbol || 'caret';
        // this parameter fixes the menu style. By default,
        // the style used is the one used in the search view
        this.dropdownStyle = dropdownHeader.style || {
                el: {class: 'btn-group o_dropdown', attrs: {}},
                mainButton: {class: 'o_dropdown_toggler_btn btn btn-sm btn-default dropdown-toggle'},
            };
        this.items = _.sortBy(items, 'groupId');
        _.each(this.items, this._prepareItem.bind(this));
    },
    /**
     * override
     */
    start: function () {
        this.$menu = this.$('.o_dropdown_menu');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Array[number]} groupIds
     */
    unsetGroups: function (groupIds) {
        var self = this;
        _.each(self.items, function (item) {
            if (_.contains(groupIds, item.groupId)) {
                item.isActive = false;
                item.currentOptionId = false;
            }
        });
        this._renderMenuItems();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} itemId
     */
    _removeItem: function (itemId) {
        var item, itemIndex;
        item = _.findWhere(this.items, {itemId: itemId});
        itemIndex = this.items.indexOf(item);
        this.items.splice(itemIndex, 1);
        this._renderMenuItems();
        var eventData = {
            category: this.dropdownCategory,
            itemId: itemId,
            groupId: item.groupId,
        };
        this.trigger_up('menu_item_deleted', eventData);
    },
    /**
     * @private
     */
    _renderMenuItems: function () {
        var newMenuItems = QWeb.render('DropdownMenu.MenuItems', {widget: this});
        this.$el.find('.o_menu_item,.divider[data-removable="1"]').remove();
        this.$('ul.o_dropdown_menu').prepend($(newMenuItems));
    },
    /**
     * this function computes some default values for some of the item keys
     * according to values passed at initialization
     *
     * @private
     * @param {Object} item
     */
     _prepareItem: function (item) {
        item.itemId = item.itemId || _.uniqueId('__item__');
        item.isOpen = item.isOpen || false;
        item.isRemovable = item.isRemovable || false;
        if (item.options && item.options.length !== 0) {
            item.options = _.sortBy(item.options, 'groupId');
            item.hasOptions = true;
            item.currentOptionId = item.isActive && item.currentOptionId ? item.currentOptionId : false;
        }
    },
    /**
     * @private
     * @param {string} itemId
     */
    _toggleMenuItem: function (itemId) {
        var item = _.findWhere(this.items, {itemId: itemId});
        if (!item.hasOptions) {
            item.isActive = !item.isActive;
            var eventData = {
                category: this.dropdownCategory,
                itemId: itemId,
                isActive: item.isActive,
                groupId: item.groupId,
            };
            this._renderMenuItems();
            this.trigger_up('menu_item_toggled', eventData);
        }
        if (item.hasOptions) {
            item.isOpen = !item.isOpen;
            this._renderMenuItems();
        }
    },
    /**
     * @private
     * @param {string} itemId
     * @param {string} optionId
     */
    _toggleItemOption: function (itemId, optionId) {
        var item = _.findWhere(this.items, {itemId: itemId});
        var initialState = item.isActive;
        if (item.currentOptionId === optionId) {
            item.isActive = false;
            item.currentOptionId = false;
        } else {
            item.isActive = true;
            item.currentOptionId = optionId;
        }
        var eventData = {
            category: this.dropdownCategory,
            itemId: itemId,
            groupId: item.groupId,
            isActive: item.isActive,
            optionId: item.currentOptionId,
        };
        this._renderMenuItems();
        if (item.isActive !== initialState) {
            this.trigger_up('menu_item_toggled', eventData);
        } else {
            this.trigger_up('item_option_changed', eventData);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method is called when Bootstrap trigger a 'close' event (for example
     * when the user clicks outside the dropdown menu).
     *
     * @private
     * @param {jQueryEvent} event
     */
    _onBootstrapClose: function () {
        _.each(this.items, function(item) {
            item.isOpen = false;
        });
        this._renderMenuItems();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onItemClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var itemId = $(event.currentTarget).data('id');
        this._toggleMenuItem(itemId);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onOptionClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var optionId = $(event.currentTarget).data('option_id');
        var itemId = $(event.currentTarget).data('item_id');
        this._toggleItemOption(itemId, optionId);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onTrashClick: function (event) {
        event.stopPropagation();
        var itemId = $(event.currentTarget).data('id');
        this._removeItem(itemId);
    },
});

return DropdownMenu;

});
