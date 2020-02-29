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
        'click span.o_trash_button': '_onTrashButtonClick',
        'hidden.bs.dropdown': '_onBootstrapClose',
        'click .dropdown-item-text': '_onDropDownItemTextClick',
    },

    init: function (parent, items) {
        this._super(parent);
        // should be specified
        this.dropdownCategory = null;
        this.dropdownTitle = null;
        this.dropdownIcon = null;
        this.dropdownSymbol = false;
        // this parameter fixes the menu style. By default,
        // the style used is the one used in the search view
        this.dropdownStyle = {
                el: {class: 'btn-group o_dropdown', attrs: {}},
                mainButton: {
                    class: 'o_dropdown_toggler_btn btn btn-secondary ' +
                        'dropdown-toggle ' +
                        (this.dropdownSymbol ? 'o-no-caret' : '')
                },
        };
        this.items = items;
        this.openItems = {};
    },
    /**
     * @override
     */
    start: function () {
        this.$menu = this.$('.o_dropdown_menu');
        this.$dropdownReference = this.$('.o_dropdown_toggler_btn');

         if (_t.database.parameters.direction === 'rtl') {
            this.$menu.addClass('dropdown-menu-right');
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} items
     */
    update: function (items) {
        this.items = items;
        this._renderMenuItems();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _renderMenuItems: function () {
        var newMenuItems = QWeb.render('DropdownMenu.MenuItems', {widget: this});
        this.$el.find('.o_menu_item, .dropdown-divider[data-removable="1"]').remove();
        this.$('.o_dropdown_menu').prepend(newMenuItems);
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
        this.openItems = {};
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
        var id = $(event.currentTarget).data('id');
        var item = this.items.find(function (item) {
            return item.id === id;
        });
        if (item.hasOptions) {
            this.openItems[id] = !this.openItems[id];
            this._renderMenuItems();
        } else {
            this.trigger_up('menu_item_clicked', {id: id});
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onOptionClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var optionId = $(event.currentTarget).data('option_id');
        var id = $(event.currentTarget).data('item_id');
        this.trigger_up('item_option_clicked', {id: id, optionId: optionId});
    },
    /**
     * @private
     * @param {MouseEvent} event
     *
     * To implement in child
     */
     _onTrashButtonClick: function (event) {
     },
});

return DropdownMenu;

});