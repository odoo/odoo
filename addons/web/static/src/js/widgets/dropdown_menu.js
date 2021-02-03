odoo.define('web.DropdownMenu', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;



var DropdownMenu = Widget.extend({
    template: 'web.DropdownMenu',
    events: {
        'click .o_menu_item': '_onItemClick',
        'click .o_item_option': '_onOptionClick',
        'click span.o_trash_button': '_onTrashClick',
        'hidden.bs.dropdown': '_onBootstrapClose',
        'click .dropdown-item-text': '_onDropDownItemTextClick',
    },

    /**
     * override
     *
     * @param {Widget} parent
     * @param {Object} dropdownHeader object used to customize the dropdown menu.
     * @param {String} dropdownHeader.title
     * @param {String} dropdownHeader.icon
     * @param {String} dropdownHeader.symbol
     * @param {String} dropdownHeader.category descripbes the type of items
     * @param {String} dropdownHeader.style the button style
     * @param {Object[]} items list of menu items
     *
     * Menu items:
     *
     * * itemId: string; (optional) unique id associated with the item
     * * description: string; label printed on screen
     * * groupId: string;
     * * isActive: boolean; (optional) determines if the item is considered active
     * * isOpen: boolean; (optional) in case there are options the submenu presenting the options is opened or closed according to isOpen
     * * isRemovable: boolean; (optional) can be removed from menu options: array of objects with 'optionId' and 'description' keys; (optional)
     * * currentOptionId: string refers to an optionId that is activated if item is active (optional)
     */
    init: function (parent, dropdownHeader, items) {
        this._super(parent);
        this.dropdownCategory = dropdownHeader.category;
        this.dropdownTitle = dropdownHeader.title;
        this.dropdownIcon = dropdownHeader.icon;
        this.dropdownSymbol = dropdownHeader.symbol || false;
        // this parameter fixes the menu style. By default,
        // the style used is the one used in the search view
        this.dropdownStyle = dropdownHeader.style || {
                el: {class: 'btn-group o_dropdown', attrs: {}},
                mainButton: {class: 'o_dropdown_toggler_btn btn btn-secondary dropdown-toggle' + (this.dropdownSymbol ? ' o-no-caret' : '')},
            };
        this.items = items;
        _.each(this.items, this._prepareItem.bind(this));
    },
    /**
     * override
     */
    start: function () {
        var self = this;
        this.$menu = this.$('.o_dropdown_menu');
        this.$dropdownReference = this.$('.o_dropdown_toggler_btn');

        if (_t.database.parameters.direction === 'rtl') {
            this.$menu.addClass('dropdown-menu-right');
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string[]} activeItemIds
     */
    updateItemsStatus: function (activeItemIds) {
        _.each(this.items, function (item) {
            if (!_.contains(activeItemIds, item.itemId)) {
                item.isActive = false;
                item.currentOptionId = false;
            } else {
                item.isActive = true;
                item.currentOptionId = item.hasOptions ?
                    (item.currentOptionId || item.defaultOptionId) :
                    false;
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
        this.$el.find('.o_menu_item, .dropdown-divider[data-removable="1"]').remove();
        this.$('.o_dropdown_menu').prepend($(newMenuItems));
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
            item.defaultOptionId = item.defaultOptionId || this.defaultOptionId;
            item.currentOptionId = item.isActive && item.defaultOptionId ? item.defaultOptionId : false;
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
        _.each(this.items, function (item) {
            item.isOpen = false;
        });
        this._renderMenuItems();
    },
    /**
     * Reacts to click on bootstrap's dropdown-item-text
     * Protects against Bootstrap dropdown close from inside click
     *
     * @private
     */
    _onDropDownItemTextClick: function (ev) {
        ev.stopPropagation();
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
