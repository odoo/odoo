odoo.define('web.AddNewFavoriteMenu', function (require) {
"use strict";

var core = require('web.core');
var favoritesSubmenusRegistry = require('web.favorites_submenus_registry');
var Widget = require('web.Widget');

var _t = core._t;

var AddNewFavoriteMenu = Widget.extend({
    template: 'AddNewFavoriteMenu',
    events: _.extend({}, Widget.prototype.events, {
        'click .o_save_favorite': '_onSaveFavoriteClick',
        'click .o_add_favorite.o_menu_header': '_onMenuHeaderClick',
        'click input[type="checkbox"]': '_onCheckboxClick',
        'keyup .o_save_name input': '_onKeyUp',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.action
     * @param {Object} params.favorites
     */
    init: function (parent, params) {
        this._super(parent);
        this.favorites = params.favorites;
        this.action = params.action;
        this.isOpen = false;
    },
    /**
     * @override
     */
    start: function () {
        this._render();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} params
     */
    update: function (params) {
        this.favorites = params.favorites;
    },
    /**
     * Close the menu and re-render the widget.
     */
    closeMenu: function () {
        this.isOpen = false;
        this._render();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _render: function () {
        this.renderElement();
        if (this.isOpen) {
            var $input = this.$('.o_favorite_name input.o_input');
            $input.val(this.action.name);
            $input.focus();
        }
    },
    /**
     * @private
     */
    _saveFavorite: function () {
        var self = this;
        var $inputs = this.$('input');
        var description = $inputs[0].value;
        var isDefault = $inputs[1].checked;
        var isShared = $inputs[2].checked;

        if (!description.length){
            this.do_warn(_t("Error"), _t("A name for your favorite is required."));
            $inputs[0].focus();
            return;
        }
        var descriptionAlreadyExists = !!this.favorites.find(function (favorite) {
            return favorite.description === description;
        });
        if (descriptionAlreadyExists) {
            this.do_warn(_t("Error"), _t("Filter with same name already exists."));
            $inputs[0].focus();
            return;
        }
        this.trigger_up('new_favorite', {
            type: 'favorite',
            description: description,
            isDefault: isDefault,
            isShared: isShared,
            on_success: function () {self.generatorMenuIsOpen = false;},
        });
        this.closeMenu();
    },
    /**
     * Hide and display the submenu which allows adding custom filters.
     *
     * @private
     */
    _toggleMenu: function () {
        this.isOpen = !this.isOpen;
        this._render();
        this.trigger_up('favorite_submenu_toggled');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Additional behavior when a checkbox is clicked upon
     * Namely, some checkbox are mutually exclusive
     * this function allows this
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onCheckboxClick: function (ev) {
        function mutuallyExclusive (elem) {
            if (!elem.id) return false;
            return ['use_by_default', 'share_all_users'].some(function (str) {
                return elem.id.indexOf(str);
            });
        }
        var $checkboxes = this.$('input[type="checkbox"]');
        var currentCheckBox = ev.target;

        if (mutuallyExclusive(currentCheckBox)) {
            for (var i=0; i < $checkboxes.length; i++) {
                var checkbox = $checkboxes[i];
                if (checkbox !== currentCheckBox && mutuallyExclusive(checkbox)) {
                    checkbox.checked = false;
                }
            }
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onKeyUp: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            this._saveFavorite();
        }
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onMenuHeaderClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._toggleMenu();
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onSaveFavoriteClick: function (ev) {
        ev.stopPropagation();
        this._saveFavorite();
    },
});

favoritesSubmenusRegistry.add('add_new_favorite_menu', AddNewFavoriteMenu, 0);

return AddNewFavoriteMenu;

});
