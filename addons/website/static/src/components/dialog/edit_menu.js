/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService, useAutofocus } from '@web/core/utils/hooks';
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import wUtils from '@website/js/utils';
import { WebsiteDialog } from './dialog';

const { Component, useState, useEffect, onWillStart, useRef } = owl;

const useControlledInput = (initialValue, validate) => {
    const input = useState({
        value: initialValue,
        hasError: false,
    });

    const isValid = () => {
        if (validate(input.value)) {
            return true;
        }
        input.hasError = true;
        return false;
    };

    useEffect(() => {
        input.hasError = false;
    }, () => [input.value]);

    return {
        input,
        isValid,
    };
};

export class MenuDialog extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.website = useService('website');
        this.title = _t("Add a menu item");
        useAutofocus();

        this.name = useControlledInput(this.props.name, value => !!value);
        this.url = useControlledInput(this.props.url, value => !!value);
        this.urlInputRef = useRef('url-input');

        useEffect(() => {
            const $input = $(this.urlInputRef.el);
            // wUtils.autocompleteWithPages rely on a widget that has a _rpc and
            // trigger_up method.
            const fakeWidget = {
                _rpc: ({ route, params }) => this.rpc(route, params),
                trigger_up: () => {
                    this.url.input.value = this.urlInputRef.el.value;
                },
            };
            const options = {
                body: this.website.pageDocument.body,
                classes: {
                    'ui-autocomplete': 'o_edit_menu_autocomplete'
                },
            };
            wUtils.autocompleteWithPages(fakeWidget, $input, options);
            return () => $input.urlcomplete('destroy');
        }, () => []);
    }

    onClickOk() {
        if (this.name.isValid()) {
            if (this.props.isMegaMenu || this.url.isValid()) {
                this.props.save(this.name.input.value, this.url.input.value);
                this.props.close();
            }
        }
    }
}
MenuDialog.template = 'website.MenuDialog';
MenuDialog.props = {
    name: { type: String, optional: true },
    url: { type: String, optional: true },
    isMegaMenu: { type: Boolean, optional: true },
    save: Function,
    close: Function,
};
MenuDialog.components = { WebsiteDialog };

class MenuRow extends Component {
    edit() {
        this.props.edit(this.props.menu.fields['id']);
    }

    delete() {
        this.props.delete(this.props.menu.fields['id']);
    }
}
MenuRow.props = {
    menu: Object,
    edit: Function,
    delete: Function,
};
MenuRow.template = 'website.MenuRow';
MenuRow.components = {
    MenuRow,
};

export class EditMenuDialog extends Component {
    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        this.dialogs = useService('dialog');

        this.title = _t("Edit Menu");
        this.saveButton = _t("Save");

        this.menuEditor = useRef('menu-editor');

        this.state = useState({ rootMenu: {} });

        onWillStart(async () => {
            const menu = await this.orm.call(
                'website.menu',
                'get_tree',
                [this.website.currentWebsite.id, this.props.rootID],
                { context: { lang: this.website.currentWebsite.metadata.lang } }
            );
            this.state.rootMenu = menu;
            this.map = new Map();
            this.populate(this.map, this.state.rootMenu);
            this.toDelete = [];
        });

        useNestedSortable({
            ref: this.menuEditor,
            nest: true,
            listTagName: "ul",
            handle: "div",
            onDrop: ({ element, previous, parent }) => {
                const menuId = element && element.dataset.menuId;
                const previousId = previous && previous.dataset.menuId;
                const newParentId = parent && parent.dataset.menuId;
                const menu = this.map.get(parseInt(menuId) || menuId);
                const newParentMenu = this.map.get(parseInt(newParentId) || newParentId) || this.state.rootMenu;
                const previousMenu = this.map.get(parseInt(previousId) || previousId);
                this.reorderMenu(menu, previousMenu, newParentMenu);
            }
        });
    }

    reorderMenu(menu, previousMenu, newParentMenu) {
        const findMenuIndex = (id) => {
            return (menu) => menu.fields.id === id;
        };
        // Remove from old menu
        const oldParentMenu = this.map.get(menu.fields["parent_id"]);
        const menuIndex = oldParentMenu.children.findIndex(findMenuIndex(menu.fields.id));
        oldParentMenu.children.splice(menuIndex, 1);
        // Find correct parent menu
        if (newParentMenu !== this.state.rootMenu) {
            // Prevent going further than 2 levels deep
            if (newParentMenu.fields["parent_id"] !== this.state.rootMenu.fields.id) {
                previousMenu = newParentMenu;
                newParentMenu = this.map.get(newParentMenu.fields["parent_id"]);
            }
            // Prevent a menu with children or a mega menu from going anywhere but
            // the top level. Prevent a menu from using a mega menu as a parent.
            if (
                menu.fields["is_mega_menu"]
                || menu.children.length >= 1
                || newParentMenu.fields["is_mega_menu"]
            ) {
                previousMenu = newParentMenu;
                newParentMenu = this.state.rootMenu;
            }
        }
        // Insert in new menu
        if (previousMenu) {
            const previousIndex = newParentMenu.children.findIndex(findMenuIndex(previousMenu.fields.id));
            newParentMenu.children.splice(previousIndex + 1, 0, menu);
        } else {
            newParentMenu.children.unshift(menu);
        }
        menu.fields["parent_id"] = newParentMenu.fields.id;
    }

    populate(map, menu) {
        map.set(menu.fields['id'], menu);
        for (const submenu of menu.children) {
            this.populate(map, submenu);
        }
    }

    addMenu(isMegaMenu) {
        this.dialogs.add(MenuDialog, {
            isMegaMenu,
            save: (name, url, isNewWindow) => {
                const newMenu = {
                    fields: {
                        id: `menu_${(new Date).toISOString()}`,
                        name,
                        url: isMegaMenu ? '#' : url,
                        new_window: isNewWindow,
                        'is_mega_menu': isMegaMenu,
                        sequence: 0,
                        'parent_id': this.state.rootMenu.fields.id,
                    },
                    'children': [],
                };
                this.map.set(newMenu.fields['id'], newMenu);
                this.state.rootMenu.children.push(newMenu);
            },
        });
    }

    editMenu(id) {
        const menuToEdit = this.map.get(id);
        this.dialogs.add(MenuDialog, {
            name: menuToEdit.fields['name'],
            url: menuToEdit.fields['url'],
            isMegaMenu: menuToEdit.fields['is_mega_menu'],
            save: (name, url) => {
                menuToEdit.fields['name'] = name;
                menuToEdit.fields['url'] = url;
                // Forces a rerender
                this.state.rootMenu.children = [...this.state.rootMenu.children];
            },
        });
    }

    deleteMenu(id) {
        const menuToDelete = this.map.get(id);
        const parentId = menuToDelete.fields['parent_id'] || this.state.rootMenu.fields['id'];
        const parent = this.map.get(parentId);
        parent.children = parent.children.filter(menu => menu.fields['id'] !== id);
        this.map.delete(id);
        if (parseInt(id)) {
            this.toDelete.push(id);
        }
    }

    async onClickSave() {
        const rootId = this.state.rootMenu.fields.id;
        const newMenus = [
            ...this.state.rootMenu.children,
            ...this.state.rootMenu.children.flatMap((menu) => menu.children)
        ];
        const levels = [];
        const data = [];

        // Resequence, re-tree and remove useless data
        for (const menu of newMenus) {
            const depth = menu.fields.parent_id !== rootId;
            levels[depth] = (levels[depth] || 0) + 1;
            const {fields: menuFields} = this.map.get(menu.fields.id);
            menuFields["sequence"] = levels[depth];
            data.push(menuFields);
        }

        await this.orm.call('website.menu', 'save', [
            this.website.currentWebsite.id,
            {
                'data': data,
                'to_delete': this.toDelete,
            }
        ],
        { context: { lang: this.website.currentWebsite.metadata.lang } });
        if (this.props.save) {
            this.props.save();
        } else {
            this.website.goToWebsite();
        }
    }
}
EditMenuDialog.template = 'website.EditMenuDialog';
EditMenuDialog.components = {
    MenuRow,
    WebsiteDialog,
};
