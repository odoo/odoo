import { useService, useAutofocus } from '@web/core/utils/hooks';
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import wUtils from '@website/js/utils';
import { WebsiteDialog } from './dialog';
import { Component, useState, useEffect, onWillStart, useRef } from "@odoo/owl";

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
    static template = "website.MenuDialog";
    static components = { WebsiteDialog };
    static props = {
        name: { type: String, optional: true },
        url: { type: String, optional: true },
        isMegaMenu: { type: Boolean, optional: true },
        save: Function,
        close: Function,
    };

    setup() {
        this.website = useService('website');
        useAutofocus();

        this.name = useControlledInput(this.props.name, value => !!value);
        this.url = useControlledInput(this.props.url, value => !!value);
        this.urlInputRef = useRef('url-input');

        useEffect((input) => {
            if (!input) {
                return;
            }
            const options = {
                body: this.website.pageDocument.body,
                position: "bottom-fit",
                classes: {
                    'ui-autocomplete': 'o_edit_menu_autocomplete'
                },
                urlChosen: () => {
                    this.url.input.value = input.value;
                },
            };
            const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(input, options);
            return () => unmountAutocompleteWithPages();
        }, () => [this.urlInputRef.el]);
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

class MenuRow extends Component {
    static template = "website.MenuRow";
    static props = {
        menu: Object,
        edit: Function,
        delete: Function,
    };
    static components = {
        MenuRow,
    };

    edit() {
        this.props.edit(this.props.menu.fields['id']);
    }

    delete() {
        this.props.delete(this.props.menu.fields['id']);
    }
}

export class EditMenuDialog extends Component {
    static template = "website.EditMenuDialog";
    static components = {
        MenuRow,
        WebsiteDialog,
    };
    static props = ["rootID?", "close", "save?"];

    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        this.dialogs = useService('dialog');

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
            handle: "div",
            nest: true,
            maxLevels: 2,
            onDrop: this._moveMenu.bind(this),
            isAllowed: this._isAllowedMove.bind(this),
            useElementSize: true,
        });
    }

    populate(map, menu) {
        map.set(menu.fields['id'], menu);
        for (const submenu of menu.children) {
            this.populate(map, submenu);
        }
    }

    _isAllowedMove(current, elementSelector) {
        const currentIsMegaMenu = current.element.dataset.isMegaMenu === "true";
        if (!currentIsMegaMenu) {
            return current.placeHolder.parentNode.closest(`${elementSelector}[data-is-mega-menu="true"]`) === null;
        }
        const isDropOnRoot = current.placeHolder.parentNode.closest(elementSelector) === null;
        return currentIsMegaMenu && isDropOnRoot;
    }

    _getMenuIdForElement(element) {
        const menuIdStr = element.dataset.menuId;
        const menuId = parseInt(menuIdStr);
        return isNaN(menuId) ? menuIdStr : menuId;
    }

    _moveMenu({ element, parent, previous }) {
        const menuId = this._getMenuIdForElement(element);
        const menu = this.map.get(menuId);

        // Remove element from parent's children (since we are moving it, this is the mandatory first step)
        const parentId = menu.fields['parent_id'] || this.state.rootMenu.fields['id'];
        let parentMenu = this.map.get(parentId);
        parentMenu.children = parentMenu.children.filter((m) => m.fields['id'] !== menuId);

        // Determine next parent
        const menuParentId = parent ? this._getMenuIdForElement(parent.closest("li")) : this.state.rootMenu.fields['id'];
        parentMenu = this.map.get(menuParentId);
        menu.fields['parent_id'] = parentMenu.fields['id'];

        // Determine at which position we should place the element
        if (previous) {
            const previousMenu = this.map.get(this._getMenuIdForElement(previous));
            const index = parentMenu.children.findIndex((menu) => menu === previousMenu);
            parentMenu.children.splice(index + 1, 0, menu);
        } else {
            parentMenu.children.unshift(menu);
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
                        'parent_id': false,
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
            },
        });
    }

    deleteMenu(id) {
        const menuToDelete = this.map.get(id);

        // Delete children first
        for (const child of menuToDelete.children) {
            this.deleteMenu(child.fields.id);
        }

        const parentId = menuToDelete.fields['parent_id'] || this.state.rootMenu.fields['id'];
        const parent = this.map.get(parentId);
        parent.children = parent.children.filter(menu => menu.fields['id'] !== id);
        this.map.delete(id);
        if (parseInt(id)) {
            this.toDelete.push(id);
        }
    }

    async onClickSave() {
        const data = [];
        this.map.forEach((menu, id) => {
            if (this.state.rootMenu.fields['id'] !== id) {
                const menuFields = menu.fields;
                const parentId = menuFields.parent_id || this.state.rootMenu.fields['id'];
                const parentMenu = this.map.get(parentId);
                menuFields['sequence'] = parentMenu.children.findIndex(m => m.fields['id'] === id);
                menuFields['parent_id'] = parentId;
                data.push(menuFields);
            }
        });

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
