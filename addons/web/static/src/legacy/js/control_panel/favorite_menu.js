odoo.define('web.FavoriteMenu', function (require) {
    "use strict";

    const Dialog = require('web.OwlDialog');
    const { FACET_ICONS } = require("web.searchUtils");
    const Registry = require('web.Registry');
    const { useModel } = require('web.Model');
    const { SearchDropdownItem } = require("@web/search/search_dropdown_item/search_dropdown_item");
    const { Component, useState } = owl;

    /**
     * 'Favorites' menu
     *
     * Simple rendering of the filters of type `favorites` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a submenu registry used to display additional components.
     * Only the favorite generator (@see CustomFavoriteItem) is registered in
     * the `web` module.
     */
    class FavoriteMenu extends Component {
        constructor() {
            super(...arguments);
            this.icon = FACET_ICONS.favorite;
            this.model = useModel('searchModel');
            this.state = useState({ deletedFavorite: false });
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            const favorites = this.model.get('filters', f => f.type === 'favorite');
            const registryMenus = this.constructor.registry.values().reduce(
                (menus, Component) => {
                    if (Component.shouldBeDisplayed(this.env)) {
                        menus.push({
                            key: Component.name,
                            groupNumber: Component.groupNumber,
                            Component,
                        });
                    }
                    return menus;
                },
                []
            );
            return [...favorites, ...registryMenus];
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {int} id
         */
        openConfirmationDialog(id) {
            const favorite = this.items.find(fav => fav.id === id);
            this.state.deletedFavorite = favorite;
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        onFavoriteSelected(ev) {
            ev.stopPropagation();
            this.model.dispatch('toggleFilter', ev.detail.payload.itemId);
        }

        /**
         * @private
         */
        async _onRemoveFavorite() {
            this.model.dispatch('deleteFavorite', this.state.deletedFavorite.id);
            this.state.deletedFavorite = false;
        }
    }

    FavoriteMenu.registry = new Registry();
    FavoriteMenu.components = { Dialog, DropdownItem: SearchDropdownItem };
    FavoriteMenu.template = 'web.Legacy.FavoriteMenu';

    return FavoriteMenu;
});
