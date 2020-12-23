odoo.define('web.FavoriteMenu', function (require) {
    "use strict";

    const Dialog = require('web.OwlDialog');
    const DropdownMenu = require('web.DropdownMenu');
    const { FACET_ICONS } = require("web.searchUtils");
    const Registry = require('web.Registry');
    const { useModel } = require('web/static/src/js/model.js');

    /**
     * 'Favorites' menu
     *
     * Simple rendering of the filters of type `favorites` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a submenu registry used to display additional components.
     * Only the favorite generator (@see CustomFavoriteItem) is registered in
     * the `web` module.
     * @see DropdownMenu for additional details.
     * @extends DropdownMenu
     */
    class FavoriteMenu extends DropdownMenu {
        constructor() {
            super(...arguments);

            this.model = useModel('searchModel');
            this.state.deletedFavorite = false;
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get icon() {
            return FACET_ICONS.favorite;
        }

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

        /**
         * @override
         */
        get title() {
            return this.env._t("Favorites");
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemRemoved(ev) {
            const favorite = this.items.find(fav => fav.id === ev.detail.item.id);
            this.state.deletedFavorite = favorite;
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            this.model.dispatch('toggleFilter', ev.detail.item.id);
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

    FavoriteMenu.components = Object.assign({}, DropdownMenu.components, {
        Dialog,
    });
    FavoriteMenu.template = 'web.FavoriteMenu';

    return FavoriteMenu;
});
