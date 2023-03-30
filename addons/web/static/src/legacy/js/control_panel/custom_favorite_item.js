odoo.define('web.CustomFavoriteItem', function (require) {
    "use strict";

    const { CheckBox } = require("@web/core/checkbox/checkbox");
    const { Dropdown } = require("@web/core/dropdown/dropdown");
    const FavoriteMenu = require('web.FavoriteMenu');
    const { useModel } = require('web.Model');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { useState, useRef } = owl;

    let favoriteId = 0;

    /**
     * Favorite generator menu
     *
     * This component is used to add a new favorite linked which will take every
     * information out of the current context and save it to a new `ir.filter`.
     *
     * There are 3 additional inputs to modify the filter:
     * - a text input (mandatory): the name of the favorite (must be unique)
     * - 'use by default' checkbox: if checked, the favorite will be the default
     *                              filter of the current model (and will bypass
     *                              any existing default filter). Cannot be checked
     *                              along with 'share with all users' checkbox.
     * - 'share with all users' checkbox: if checked, the favorite will be available
     *                                    with all users instead of the current
     *                                    one.Cannot be checked along with 'use
     *                                    by default' checkbox.
     * Finally, there is a 'Save' button used to apply the current configuration
     * and save the context to a new filter.
     */
    class CustomFavoriteItem extends LegacyComponent {
        setup() {
            const favId = favoriteId++;
            this.useByDefaultId = `o_favorite_use_by_default_${favId}`;
            this.shareAllUsersId = `o_favorite_share_all_users_${favId}`;
            this.descriptionRef = useRef("description");
            this.model = useModel("searchModel");
            this.interactive = true;
            this.state = useState({
                description: this.env.action.name || "",
                isDefault: false,
                isShared: false,
            });
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         */
        saveFavorite() {
            if (!this.state.description) {
                this.env.services.notification.notify({
                    message: this.env._t("A name for your favorite filter is required."),
                    type: 'danger',
                });
                return this.descriptionRef.el.focus();
            }
            const favorites = this.model.get('filters', f => f.type === 'favorite');
            if (favorites.some(f => f.description === this.state.description)) {
                this.env.services.notification.notify({
                    message: this.env._t("Filter with same name already exists."),
                    type: 'danger',
                });
                return this.descriptionRef.el.focus();
            }
            this.model.dispatch('createNewFavorite', {
                type: 'favorite',
                description: this.state.description,
                isDefault: this.state.isDefault,
                isShared: this.state.isShared,
            });
            // Reset state
            Object.assign(this.state, {
                description: this.env.action.name || "",
                isDefault: false,
                isShared: false,
                open: false,
            });
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {boolean} checked
         */
        onDefaultCheckboxChange(checked) {
            this.state.isDefault = checked;
            if (checked) {
                this.state.isShared = false;
            }
        }

        /**
         * @private
         * @param {boolean} checked
         */
        onShareCheckboxChange(checked) {
            this.state.isShared = checked;
            if (checked) {
                this.state.isDefault = false;
            }
        }

        /**
         * @private
         * @param {jQueryEvent} ev
         */
        onInputKeydown(ev) {
            switch (ev.key) {
                case 'Enter':
                    ev.preventDefault();
                    this.saveFavorite();
                    break;
                case 'Escape':
                    // Gives the focus back to the component.
                    ev.preventDefault();
                    ev.target.blur();
                    break;
            }
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @param {Object} env
         * @returns {boolean}
         */
        static shouldBeDisplayed(env) {
            return true;
        }
    }

    CustomFavoriteItem.props = {};
    CustomFavoriteItem.template = "web.CustomFavoriteItem";
    CustomFavoriteItem.components = { CheckBox, Dropdown };
    CustomFavoriteItem.groupNumber = 3; // have 'Save Current Search' in its own group

    FavoriteMenu.registry.add('favorite-generator-menu', CustomFavoriteItem, 0);

    return CustomFavoriteItem;
});
