import { useService, useAutofocus } from "@web/core/utils/hooks";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import wUtils from "@website/js/utils";
import { WebsiteDialog } from "./dialog";
import { Component, useState, useEffect, onWillStart, useRef, reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { isEmail } from "@web/core/utils/strings";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { isAbsoluteURLInCurrentDomain } from "@html_editor/utils/url";
import { useDebounced } from "@web/core/utils/timing";
import { KeepLast } from "@web/core/utils/concurrency";
import { effect } from "@web/core/utils/reactive";

function urlToCheck(url) {
    let relativeUrl = false;

    // Do not check if the page exists if the input is empty, an anchor, an
    // email, or a phone number.
    if (!url.trim() || url.startsWith("#") || isEmail(url) || /^(mailto:|tel:)/.test(url)) {
        return false;
    }

    try {
        relativeUrl = toRelativeIfSameDomain(url);
        if (relativeUrl === url) {
            // External URL
            return false;
        }
    } catch {
        // Relative or invalid URL; proceed with original.
        relativeUrl = url;
    }

    // Remove query params and hash.
    relativeUrl = relativeUrl.split("?")[0].split("#")[0];
    // Ensure the URL starts with "/".
    relativeUrl = relativeUrl.startsWith("/") ? relativeUrl : "/" + relativeUrl;
    // Remove trailing slash if it's not the root "/".
    relativeUrl =
        relativeUrl.endsWith("/") && relativeUrl !== "/" ? relativeUrl.slice(0, -1) : relativeUrl;
    return relativeUrl;
}

async function checkUrlExists(link) {
    const normLink = urlToCheck(link);
    if (normLink === false) {
        return true;
    } else {
        return await rpc("/website/check_existing_link", { link: normLink });
    }
}

const toRelativeIfSameDomain = (url) => {
    // Remove domain from url to keep only the relative path if same domain.
    const urlObj = new URL(url);
    const isSameDomain = isAbsoluteURLInCurrentDomain(url, this.env);
    return isSameDomain ? url.replace(urlObj.origin, "") : url;
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
        this.website = useService("website");
        this.title = this.props.isMegaMenu ? _t("Mega menu item") : _t("Menu item");
        useAutofocus();

        this.urlInputRef = useRef("url-input");
        this.urlInputEdited = !!this.props.url;

        this.state = useState({
            pageNotFound: false,
            url: this.props.url,
            name: this.props.name,
            invalidName: false,
            invalidUrl: false,
        });

        const keepLast = new KeepLast();
        const updatePageNotFound = (url) =>
            keepLast.add(checkUrlExists(url)).then((exists) => (this.state.pageNotFound = !exists));
        const debouncedUpdatePageNotFound = useDebounced(updatePageNotFound, 500);
        effect(({ url }) => debouncedUpdatePageNotFound(url), [this.state]);

        useEffect(
            (input) => {
                if (!input) {
                    return;
                }
                const options = {
                    body: this.website.pageDocument.body,
                    position: "bottom-fit",
                    classes: {
                        "ui-autocomplete": "o_edit_menu_autocomplete",
                    },
                    urlChosen: () => {
                        this.state.url = input.value;
                        this.state.pageNotFound = false;
                    },
                };
                const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(
                    input,
                    options,
                    this.env
                );
                return () => unmountAutocompleteWithPages();
            },
            () => [this.urlInputRef.el]
        );
    }

    onClickOk() {
        this.state.invalidName = !this.state.name;
        if (this.state.invalidName) {
            return;
        }

        let url = this.state.url;
        if (!this.props.isMegaMenu) {
            try {
                url = toRelativeIfSameDomain(url);
            } catch {
                // Do nothing if URL is invalid.
            }
        }
        this.props.save(this.state.name, url);
        this.props.close();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onUrlInput(ev) {
        this.state.invalidUrl = false;
        this.urlInputEdited = true;
    }

    onTitleInput(ev) {
        this.state.invalidName = false;
        if (!this.urlInputEdited && !this.props.isMegaMenu) {
            const title = ev.target.value;
            this.state.url = title ? "/" + wUtils.slugify(title) : "";
        }
    }
}

class MenuRow extends Component {
    static template = "website.MenuRow";
    static props = {
        menu: Object,
        edit: Function,
        delete: Function,
        createPage: Function,
    };
    static components = {
        MenuRow,
    };

    edit() {
        this.props.edit(this.props.menu.fields["id"]);
    }

    delete() {
        this.props.delete(this.props.menu.fields["id"]);
    }

    createPage() {
        this.props.createPage(this.props.menu.fields["id"]);
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
        this.orm = useService("orm");
        this.website = useService("website");
        this.dialogs = useService("dialog");

        this.menuEditor = useRef("menu-editor");

        this.state = useState({ rootMenu: {} });

        onWillStart(async () => {
            const menu = await this.orm.call(
                "website.menu",
                "get_tree",
                [this.website.currentWebsite.id, this.props.rootID],
                { context: { lang: this.website.currentWebsite.metadata.lang } }
            );
            await this.markPageNotFound(menu);
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
            /**
             * @param {DOMElement} element - moved element
             * @param {DOMElement} parent - parent element of where the element was moved
             * @param {DOMElement} placeholder - hint element showing the current position
             */
            onMove: ({ element, placeholder, parent }) => {
                // Adapt the dragged menu item to match the width and position
                // of the placeholder.
                element.style.width = getComputedStyle(placeholder).width;
                element.style.marginLeft =
                    parent && element.parentElement === this.menuEditor.el ? "2rem" : "";
            },
            preventDrag: (el) => el.querySelector(":scope > button"),
        });
    }

    populate(map, menu) {
        map.set(menu.fields["id"], menu);
        for (const submenu of menu.children) {
            this.populate(map, submenu);
        }
    }

    async markPageNotFound(menu) {
        function menuFlattened(menu) {
            return [menu, ...(menu.children ? menu.children.flatMap(menuFlattened) : [])];
        }
        await Promise.all(
            menuFlattened(menu)
                .slice(1) // exclude root menu
                .map(async (menu) => {
                    menu.page_not_found = !(await checkUrlExists(menu.fields["url"]));
                })
        );
    }

    _isAllowedMove(current, elementSelector) {
        const currentIsMegaMenu = current.element.dataset.isMegaMenu === "true";
        if (!currentIsMegaMenu) {
            return (
                current.placeHolder.parentNode.closest(
                    `${elementSelector}[data-is-mega-menu="true"]`
                ) === null
            );
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
        const parentId = menu.fields["parent_id"] || this.state.rootMenu.fields["id"];
        let parentMenu = this.map.get(parentId);
        parentMenu.children = parentMenu.children.filter((m) => m.fields["id"] !== menuId);

        // Determine next parent
        const menuParentId = parent
            ? this._getMenuIdForElement(parent.closest("li"))
            : this.state.rootMenu.fields["id"];
        parentMenu = this.map.get(menuParentId);
        menu.fields["parent_id"] = parentMenu.fields["id"];

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
            url: "",
            save: (name, url) => {
                const newMenu = reactive({
                    fields: {
                        id: `menu_${new Date().toISOString()}`,
                        name,
                        url: isMegaMenu || !url ? "#" : url,
                        new_window: false,
                        is_mega_menu: isMegaMenu,
                        sequence: 0,
                        parent_id: false,
                    },
                    children: [],
                    page_not_found: false,
                });
                this.state.rootMenu.children.push(newMenu);
                this.map.set(newMenu.fields["id"], newMenu);
                this.checkMenuUrlExists(newMenu, url);
            },
        });
    }

    editMenu(id) {
        const menuToEdit = this.map.get(id);
        this.dialogs.add(MenuDialog, {
            name: menuToEdit.fields["name"],
            url: menuToEdit.fields["url"],
            isMegaMenu: menuToEdit.fields["is_mega_menu"],
            save: (name, url) => {
                menuToEdit.fields["name"] = name;
                menuToEdit.fields["url"] = url || "#";
                menuToEdit.page_not_found = false;
                this.checkMenuUrlExists(menuToEdit, url);
            },
        });
    }

    checkMenuUrlExists(menu, url) {
        if (url) {
            checkUrlExists(url).then((exists) => {
                if (menu.fields["url"] === url) {
                    menu.page_not_found = !exists;
                }
            });
        }
    }

    deleteMenu(id) {
        const menuToDelete = this.map.get(id);

        // Delete children first
        for (const child of menuToDelete.children) {
            this.deleteMenu(child.fields.id);
        }

        const parentId = menuToDelete.fields["parent_id"] || this.state.rootMenu.fields["id"];
        const parent = this.map.get(parentId);
        parent.children = parent.children.filter((menu) => menu.fields["id"] !== id);
        this.map.delete(id);
        if (parseInt(id)) {
            this.toDelete.push(id);
        }
    }

    async onClickSave(goToWebsite = true, url) {
        const data = [];
        this.map.forEach((menu, id) => {
            if (this.state.rootMenu.fields["id"] !== id) {
                const menuFields = menu.fields;
                const parentId = menuFields.parent_id || this.state.rootMenu.fields["id"];
                const parentMenu = this.map.get(parentId);
                menuFields["sequence"] = parentMenu.children.findIndex(
                    (m) => m.fields["id"] === id
                );
                menuFields["parent_id"] = parentId;
                data.push(menuFields);
            }
        });

        await this.orm.call(
            "website.menu",
            "save",
            [
                this.website.currentWebsite.id,
                {
                    data: data,
                    to_delete: this.toDelete,
                },
            ],
            { context: { lang: this.website.currentWebsite.metadata.lang } }
        );
        if (this.props.save) {
            this.props.save(url);
        } else if (goToWebsite) {
            this.website.goToWebsite();
        }
    }

    async createPage(id) {
        const menu = this.map.get(id);
        let url = menu.fields["url"];
        url = url.startsWith("/") ? url : "/" + url;
        this.dialogs.add(AddPageDialog, {
            onAddPage: () => {
                this.onClickSave(false, url);
            },
            websiteId: this.website.currentWebsite.id,
            forcedURL: url,
            goToPage: !this.props.save,
            pageTitle: menu.fields["name"],
        });
    }
}
