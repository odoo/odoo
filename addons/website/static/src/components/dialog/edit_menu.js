/** @odoo-module **/

import { useService, useAutofocus } from '@web/core/utils/hooks';
import wUtils from 'website.utils';
import { WebsiteDialog } from './dialog';

const { Component, useState, useEffect, onWillStart, useRef, onMounted } = owl;

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
        this.title = this.env._t("Add a menu item");
        useAutofocus();

        this.name = useControlledInput(this.props.name, value => !!value);
        this.url = useControlledInput(this.props.url, value => !!value);
        this.urlInputRef = useRef('url-input');

        useEffect(() => {
            const $input = $(this.urlInputRef.el);
            // This is only there to avoid changing the
            // wUtils.autocompleteWithPages api
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

        this.title = this.env._t("Edit Menu");
        this.saveButton = this.env._t("Save");

        this.menuEditor = useRef('menu-editor');

        this.state = useState({ rootMenu: {} });

        onWillStart(async () => {
            const menu = await this.orm.call('website.menu', 'get_tree', [this.website.currentWebsite.id, this.props.rootID]);
            this.state.rootMenu = menu;
            this.map = new Map();
            this.populate(this.map, this.state.rootMenu);
            this.toDelete = [];
        });

        onMounted(() => {
            this.$sortables = $(this.menuEditor.el);
            this.$sortables.nestedSortable({
                listType: 'ul',
                handle: 'div',
                items: 'li',
                maxLevels: 2,
                toleranceElement: '> div',
                forcePlaceholderSize: true,
                opacity: 0.6,
                placeholder: 'oe_menu_placeholder',
                tolerance: 'pointer',
                attribute: 'data-menu-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
                isAllowed: (placeholder, placeholderParent, currentItem) => {
                    return !placeholderParent
                        || !currentItem[0].dataset.isMegaMenu && !placeholderParent[0].dataset.isMegaMenu;
                },
            });
        });
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
        this.toDelete.push(id);
    }

    async onClickSave() {
        const newMenus = this.$sortables.nestedSortable('toArray', {startDepthCount: 0});
        const levels = [];
        const data = [];

        // Resequence, re-tree and remove useless data
        for (const menu of newMenus) {
            if (menu.id) {
                levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                const {fields: menuFields} = this.map.get(menu.id) || this.map.get(parseInt(menu.id, 10));
                menuFields['sequence'] = levels[menu.depth];
                // JQuery's nestedSortable() extracts parent_ids as string.
                // They must be ints when they are actual existing ids but
                // remain as strings when they represent a creation ("new-##").
                menuFields['parent_id'] = parseInt(menu['parent_id']) || menu['parent_id'] || this.state.rootMenu.fields['id'];
                data.push(menuFields);
            }
        }

        await this.orm.call('website.menu', 'save', [
            this.website.currentWebsite.id,
            {
                'data': data,
                'to_delete': this.toDelete,
            }
        ]);
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
