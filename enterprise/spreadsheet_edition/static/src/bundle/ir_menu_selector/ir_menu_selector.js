/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";

import { Component, useState, useExternalListener, useRef, onMounted } from "@odoo/owl";

export class IrMenuSelector extends Component {
    static components = { Many2XAutocomplete };
    static template = "spreadsheet_edition.IrMenuSelector";
    static props = {
        menuId: { type: Number, optional: true },
        onValueChanged: Function,
        autoFocus: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.ref = useRef("menuSelectorRef");
        this.menus = useService("menu");
        onMounted(() => {
            if (this.props.autoFocus) {
                this.ref.el.querySelector("input")?.focus();
            }
        });
    }

    get many2XAutocompleteProps() {
        return {
            resModel: "ir.ui.menu",
            fieldString: _t("Menu Items"),
            getDomain: this.getDomain.bind(this),
            update: this.updateMenu.bind(this),
            activeActions: {},
            placeholder: _t("Select a menu..."),
            value: this._getMenuPath(this.props.menuId),
        };
    }

    updateMenu(selectedMenus) {
        this.props.onValueChanged(selectedMenus[0]?.id);
    }

    getDomain() {
        return [
            "|",
            ["id", "in", this.availableAppMenuIds],
            "&",
            ["action", "!=", false],
            ["id", "in", this.availableMenuIds],
        ];
    }

    get availableMenuIds() {
        return this.menus
            .getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
    }

    get availableAppMenuIds() {
        return this.menus
            .getAll()
            .filter((menu) => menu.id === menu.appID)
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
    }

    /**
     * Get the path of the given menu as a string of the form "App/Menu/Submenu".
     * @private
     */
    _getMenuPath(menuId) {
        if (menuId === undefined) {
            return "";
        }
        const menuTree = this.menus.getMenuAsTree("root");
        const computedTree = computeAppsAndMenuItems(menuTree);
        const app = computedTree.apps.find((app) => app.id === menuId);
        if (app) {
            return app.label;
        }
        const menu = computedTree.menuItems.find((menu) => menu.id === menuId);
        if (!menu) {
            return "";
        }
        const path = menu.parents.replace(/ \/ /g, "/");
        return path + "/" + menu.label;
    }
}

export class IrMenuSelectorDialog extends Component {
    static components = { Dialog, IrMenuSelector };
    static template = "spreadsheet_edition.IrMenuSelectorDialog";
    static props = {
        onMenuSelected: Function,
        close: Function, // prop added by Dialog service
    };

    setup() {
        this.selectedMenu = useState({
            id: undefined,
        });
        // Clicking anywhere will close the link editor menu. It should be
        // prevented otherwise the chain of event would be broken.
        // A solution would be to listen all clicks coming from this dialog and stop
        // their propagation.
        // However, the autocomplete dropdown of the Many2OneField widget is *not*
        // a child of this component. It's actually a direct child of "body" ¯\_(ツ)_/¯
        // The following external listener handles this.
        useExternalListener(document.body, "click", (ev) => {
            ev.stopPropagation();
            ev.preventDefault(); // stop jumping to odoo home page
        });
    }
    _onConfirm() {
        this.props.onMenuSelected(this.selectedMenu.id);
    }
    _onValueChanged(value) {
        this.selectedMenu.id = value;
    }
}
