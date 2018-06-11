odoo.define('web.DropdownMenu', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;

// interface IItem {
//     itemId: string;
//     description: string;
//     groupId: string;
//     isActive: boolean; (optional)
//     isOpen: boolean; (optional)
//     isRemovable: boolean; (optional)
//     options: array of objects with 'optionId' and 'description' keys; (optional)
//     defaultOptionId: string refers to an optionId (optional)
//     currentOptionId: string refers to an optionId that is activated if item is active (optional)
// }

var DropdownMenu = Widget.extend({
    template: 'web.DropdownMenu',
    events: {
        'click li.o_menu_item': '_onItemClick',
        'click li.o_item_option': '_onOptionClick',
        'click li.o_menu_item span.o_submenu_switcher': '_openItemOptions',
        'click span.o_trash_button': '_onTrashClick',
        'hidden.bs.dropdown': '_onBootstrapClose',
    },

    /**
     * @param {Widget} parent
     * @param {Object} dropdowHeader object with keys 'title' and 'icon'
     * @param {Object} items values are arrays of items (see interface IItems)
     * @param {Object} itemGenerator
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
     * @private
     * @param {Object} item
     */
     _prepareItem: function (item) {
        item.isOpen = item.isOpen || false;
        item.isRemovable = item.isRemovable || false;
        item.hasOptions = item.options && item.options.length !== 0 ? true : false;
        item.defaultOptionId = item.hasOptions ?
            (item.defaultOptionId || item.options[0].optionId) :
            false;
        item.currentOptionId = item.isActive ? (item.currentOptionId || item.defaultOptionId ) : false;
    },
    /**
     * @private
     * @param {string} itemId
     */
    _toggleMenuItem: function (itemId) {
        var item = _.findWhere(this.items, {itemId: itemId});
        item.isActive = !item.isActive;
        var eventData = {
            category: this.dropdownCategory,
            itemId: itemId,
            isActive: item.isActive,
            groupId: item.groupId,
        };
        if (item.hasOptions) {
            if (item.isActive) {
                item.currentOptionId = item.defaultOptionId;
                eventData.optionId = item.currentOptionId;
            } else {
                item.currentOptionId = false;
            }
        }
        this._renderMenuItems();
        this.trigger_up('menu_item_toggled', eventData);
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
    /**
     * @private
     * @param {string} itemId
     */
    _toggleMenuOptions: function (itemId) {
        var item = _.findWhere(this.items, {itemId: itemId});
        item.isOpen = !item.isOpen;
        this._renderMenuItems();
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
    /**
     * @private
     * @param {MouseEvent} event
     */
    _openItemOptions: function (event) {
        // we preventdefault the event here to avoid changing the hash # in the
        // url.
        event.preventDefault();
        event.stopPropagation();
        var itemId = $(event.currentTarget).data('id');
        this._toggleMenuOptions(itemId);
    },
});

return DropdownMenu;

});