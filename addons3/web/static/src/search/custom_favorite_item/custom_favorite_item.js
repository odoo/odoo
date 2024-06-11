/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component, useRef, useState } from "@odoo/owl";

const favoriteMenuRegistry = registry.category("favoriteMenu");

export class CustomFavoriteItem extends Component {
    setup() {
        this.notificationService = useService("notification");
        this.descriptionRef = useRef("description");
        this.state = useState({
            description: this.env.config.getDisplayName(),
            isDefault: false,
            isShared: false,
        });
    }

    /**
     * @param {Event} ev
     */
    saveFavorite(ev) {
        if (!this.state.description) {
            this.notificationService.add(_t("A name for your favorite filter is required."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.descriptionRef.el.focus();
        }
        const favorites = this.env.searchModel.getSearchItems(
            (s) => s.type === "favorite" && s.description === this.state.description
        );
        if (favorites.length) {
            this.notificationService.add(_t("A filter with same name already exists."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.descriptionRef.el.focus();
        }
        const { description, isDefault, isShared } = this.state;
        this.env.searchModel.createNewFavorite({ description, isDefault, isShared });

        Object.assign(this.state, {
            description: this.env.config.getDisplayName(),
            isDefault: false,
            isShared: false,
        });
    }

    /**
     * @param {boolean} checked
     */
    onDefaultCheckboxChange(checked) {
        this.state.isDefault = checked;
        if (checked) {
            this.state.isShared = false;
        }
    }

    /**
     * @param {boolean} checked
     */
    onShareCheckboxChange(checked) {
        this.state.isShared = checked;
        if (checked) {
            this.state.isDefault = false;
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                this.saveFavorite();
                break;
            case "Escape":
                // Gives the focus back to the component.
                ev.preventDefault();
                ev.target.blur();
                break;
        }
    }
}

CustomFavoriteItem.template = "web.CustomFavoriteItem";
CustomFavoriteItem.components = { CheckBox, AccordionItem };
CustomFavoriteItem.props = {};
favoriteMenuRegistry.add(
    "custom-favorite-item",
    { Component: CustomFavoriteItem, groupNumber: 3 },
    { sequence: 0 }
);
