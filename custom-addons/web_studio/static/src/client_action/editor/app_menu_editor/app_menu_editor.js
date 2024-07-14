/** @odoo-module */
import { Component, useRef, useState } from "@odoo/owl";
import { useBus, useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { MenuCreatorDialog } from "@web_studio/client_action/menu_creator/menu_creator";
import { useDialogConfirmation, useSubEnvAndServices } from "@web_studio/client_action/utils";
import { _t } from "@web/core/l10n/translation";

const EditMenuDialogProps = { ...Dialog.props };
EditMenuDialogProps.close = { type: Function };
delete EditMenuDialogProps.slots;
class EditMenuDialog extends Component {
    static components = { Dialog };
    static template = "web_studio.AppMenuEditor.EditMenuDialog";
    static props = EditMenuDialogProps;

    setup() {
        // Keep the bus from the WebClient
        const originalBus = this.env.bus;
        useBus(originalBus, "MENUS:APP-CHANGED", () => (this.state.tree = this.getTree()));

        this.menus = useService("menu");
        this.addDialog = useOwnedDialogs();
        this.orm = useService("orm");
        this.user = useService("user");
        this.rpc = useService("rpc");

        useBus(this.env.bus, "ACTION_MANAGER:UPDATE", () => this.cancel());

        this.title = _t("Edit Menu");

        // States and data
        this.state = useState({ tree: {}, flatMenus: {} });
        this.state.tree = this.getTree();
        this.toMove = {};
        this.toDelete = [];

        // DragAndDrop to move menus around
        const root = useRef("root");
        useNestedSortable({
            ref: root,
            handle: ".o-draggable-handle",
            nest: true,
            maxLevels: 5,
            useElementSize: true,
            onDrop: this.moveMenu.bind(this),
        });

        const { confirm, cancel } = useDialogConfirmation({
            confirm: async () => {
                await this.saveChanges();
            },
        });
        this.confirm = confirm;
        this.cancel = cancel;
    }

    get flatMenus() {
        return this.state.flatMenus;
    }

    get mainItem() {
        return this.state.tree;
    }

    getTree() {
        let currentApp = this.menus.getCurrentApp();
        if (!currentApp) {
            return null;
        }
        currentApp = this.menus.getMenuAsTree(currentApp.id);
        const item = this._getItemFromMenu(currentApp, null);
        item.isDraggable = false;
        item.isRemovable = false;
        return item;
    }

    _getItemFromMenu(menu, parentId) {
        const item = {
            id: menu.id,
            name: menu.name,
            isDraggable: true,
            isRemovable: true,
            parentId,
        };
        item.children = menu.childrenTree.map((menu) => this._getItemFromMenu(menu, item.id));
        this.flatMenus[item.id] = item;
        return item;
    }

    moveMenu({ element, parent, previous }) {
        const menuId = parseInt(element.dataset.itemId);
        const menu = this.flatMenus[menuId];

        // Remove element from parent's children (since we are moving it, this is the mandatory first step)
        let parentMenu = this.flatMenus[menu.parentId];
        parentMenu.children = parentMenu.children.filter((m) => m.id !== menuId);

        // Determine next parent
        const parentLi = parent?.closest("li");
        const parentMenuId = parentLi ? parseInt(parentLi.dataset.itemId) : this.mainItem.id;
        if (parentMenuId !== parentMenu.id) {
            parentMenu = this.flatMenus[parentMenuId];
            menu.parentId = parentMenu.id;
        }

        // Determine at which position we should place the element
        if (previous) {
            const previousMenu = this.flatMenus[previous.dataset.itemId];
            const index = parentMenu.children.findIndex((child) => child === previousMenu);
            parentMenu.children.splice(index + 1, 0, menu);
        } else {
            parentMenu.children.unshift(menu);
        }

        // Last step: prepare the data that can be sent to the server.
        this.toMove[menuId] = {
            parent_menu_id: menu.parentId,
        };

        parentMenu.children.forEach((m, index) => {
            this.toMove[m.id] = this.toMove[m.id] || {};
            this.toMove[m.id].sequence = index + 1;
        });
    }

    removeItem(menu) {
        const parentMenu = this.flatMenus[menu.parentId];
        if (!parentMenu) {
            return;
        }
        parentMenu.children = parentMenu.children.filter((m) => m.id !== menu.id);
        this.toDelete.push(menu.id);
    }

    editItem(menu) {
        this.addDialog(FormViewDialog, {
            resModel: "ir.ui.menu",
            resId: menu.id,
            onRecordSaved: async () => {
                await this.saveChanges(true);
            },
        });
    }

    async saveChanges(reload = false) {
        if (Object.keys(this.toMove).length || this.toDelete.length) {
            await this.orm.call("ir.ui.menu", "customize", [], {
                to_move: this.toMove,
                to_delete: this.toDelete,
            });
            reload = true;
        }
        if (reload) {
            await this.menus.reload();
        }
    }

    onNewMenu() {
        this.addDialog(MenuCreatorDialog, {
            confirm: async (data) => {
                await this.rpc("/web_studio/create_new_menu", {
                    menu_name: data.menuName,
                    model_id: data.modelId[0],
                    model_choice: data.modelChoice,
                    model_options: data.modelOptions || {},
                    parent_menu_id: this.mainItem.id,
                    context: this.user.context,
                });
                this.env.bus.trigger("CLEAR-CACHES");
                this.menus.reload();
            },
        });
    }
}

export class AppMenuEditor extends Component {
    static props = {
        env: { type: Object },
    };
    static template = "web_studio.AppMenuEditor";

    setup() {
        this.menus = useService("menu");
        // original bus from webClient
        const bus = this.env.bus;
        // ovverride the whole env coming from within studio
        // contains an override of dialog and an override of action
        useSubEnvAndServices(this.props.env);
        this.addDialog = useOwnedDialogs();
        useBus(bus, "MENUS:APP-CHANGED", () => this.render());
    }

    onClick(ev) {
        ev.preventDefault();
        this.addDialog(EditMenuDialog);
    }
}
