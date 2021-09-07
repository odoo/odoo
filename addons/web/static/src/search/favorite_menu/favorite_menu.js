/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FACET_ICONS } from "../utils/misc";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useService } from "@web/core/utils/hooks";

const favoriteMenuRegistry = registry.category("favoriteMenu");

const { Component } = owl;

export class FavoriteMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.favorite;
        this.dialogService = useService("dialog");

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {Array}
     */
    get items() {
        const favorites = this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite"
        );
        const registryMenus = [];
        for (const item of favoriteMenuRegistry.getAll()) {
            if ("isDisplayed" in item ? item.isDisplayed(this.env) : true) {
                registryMenus.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return [...favorites, ...registryMenus];
    }

    /**
     * @param {CustomEvent} ev
     */
    onFavoriteSelected(ev) {
        const { itemId } = ev.detail.payload;
        this.env.searchModel.toggleSearchItem(itemId);
    }

    /**
     * @param {number} itemId
     */
    openConfirmationDialog(itemId) {
        const { userId } = this.items.find((item) => item.id === itemId);
        const dialogProps = {
            title: this.env._t("Warning"),
            body: userId
                ? this.env._t("Are you sure that you want to remove this filter?")
                : this.env._t(
                      "This filter is global and will be removed for everybody if you continue."
                  ),
            confirm: () => this.env.searchModel.deleteFavorite(itemId),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}

FavoriteMenu.template = "web.FavoriteMenu";
