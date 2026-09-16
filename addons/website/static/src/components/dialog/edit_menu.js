/** @odoo-module native */
import { isAbsoluteURLInCurrentDomain } from "@html_editor/utils/url";
import {
    Component,
    onWillStart,
    reactive,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useNestedSortable } from "@web/core/utils/dnd";
import { isEmail } from "@web/core/utils/format/strings";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";
import { useDebounced } from "@web/core/utils/timing";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { autocompleteWithPages, slugify } from "@website/js/utils";

import { WebsiteDialog } from "./dialog.js";

const log = makeLogger("website.dialog.edit_menu");

function urlToCheck(url) {
    let relativeUrl;

    if (
        !url.trim() ||
        url.startsWith("#") ||
        isEmail(url) ||
        /^(mailto:|tel:)/.test(url)
    ) {
        return false;
    }

    try {
        relativeUrl = toRelativeIfSameDomain(url);
        if (relativeUrl === url) {
            return false;
        }
    } catch {
        relativeUrl = url;
    }

    relativeUrl = relativeUrl.split("?")[0].split("#")[0];
    relativeUrl = relativeUrl.startsWith("/") ? relativeUrl : "/" + relativeUrl;
    relativeUrl =
        relativeUrl.endsWith("/") && relativeUrl !== "/"
            ? relativeUrl.slice(0, -1)
            : relativeUrl;
    return relativeUrl;
}

async function checkUrlExists(link) {
    const normLink = urlToCheck(link);
    if (normLink === false) {
        log.logic("checkUrlExists skip: not an internal page url", { link });
        return true;
    } else {
        return await rpc("/website/check_existing_link", { link: normLink });
    }
}

const toRelativeIfSameDomain = (url) => {
    const urlObj = new URL(url);
    const isSameDomain = isAbsoluteURLInCurrentDomain(url);
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
        useLifecycleLog(log);
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
            keepLast
                .add(checkUrlExists(url))
                .then((exists) => (this.state.pageNotFound = !exists));
        const debouncedUpdatePageNotFound = useDebounced(updatePageNotFound, 500);
        effect(({ url }) => debouncedUpdatePageNotFound(url), [this.state]);

        useEffect(
            (input) => {
                if (!input) {
                    log.logic("MenuDialog no url input: skip autocomplete");
                    return;
                }
                log.lifecycle("MenuDialog autocompleteWithPages attached");
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
                const unmountAutocompleteWithPages = autocompleteWithPages(
                    input,
                    options,
                    this.env,
                );
                return () => unmountAutocompleteWithPages();
            },
            () => [this.urlInputRef.el],
        );
    }

    onClickOk() {
        this.state.invalidName = !this.state.name;
        if (this.state.invalidName) {
            log.logic("MenuDialog save refused: empty name");
            return;
        }

        let url = this.state.url;
        if (!this.props.isMegaMenu) {
            try {
                url = toRelativeIfSameDomain(url);
            } catch {}
        }
        log.logic("MenuDialog save", () => ({
            url,
            typedUrl: this.state.url,
            isMegaMenu: this.props.isMegaMenu,
        }));
        this.props.save(this.state.name, url);
        this.props.close();
    }

    onUrlInput(ev) {
        this.state.invalidUrl = false;
        this.urlInputEdited = true;
    }

    onTitleInput(ev) {
        this.state.invalidName = false;
        if (!this.urlInputEdited && !this.props.isMegaMenu) {
            const title = ev.target.value;
            this.state.url = title ? "/" + slugify(title) : "";
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
        useLifecycleLog(log);
        this.orm = useService("orm");
        this.website = useService("website");
        this.dialogs = useService("dialog");

        this.menuEditor = useRef("menu-editor");

        this.state = useState({ rootMenu: {} });

        onWillStart(async () => {
            const endTree = log.perf("get_tree", () => ({ rootID: this.props.rootID }));
            const menu = await this.orm.call(
                "website.menu",
                "get_tree",
                [this.website.currentWebsite.id, this.props.rootID],
                { context: { lang: this.website.currentWebsite.metadata.lang } },
            );
            endTree();
            const endCheck = log.perf("markPageNotFound");
            await this.markPageNotFound(menu);
            endCheck();
            this.state.rootMenu = menu;
            this.map = new Map();
            this.populate(this.map, this.state.rootMenu);
            this.toDelete = [];
            log.pipeline("EditMenuDialog menus indexed", () => ({
                menus: this.map.size,
            }));
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
             * @param {DOMElement} element
             * @param {DOMElement} parent
             * @param {DOMElement} placeholder
             */
            onMove: ({ element, placeholder, parent }) => {
                element.style.width = getComputedStyle(placeholder).width;
                element.style.marginLeft =
                    parent && element.parentElement === this.menuEditor.el
                        ? "2rem"
                        : "";
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
            return [
                menu,
                ...(menu.children ? menu.children.flatMap(menuFlattened) : []),
            ];
        }
        log.pipeline("markPageNotFound checking menu urls", () => ({
            menus: menuFlattened(menu).length - 1,
        }));
        await Promise.all(
            menuFlattened(menu)
                .slice(1)
                .map(async (menu) => {
                    menu.page_not_found = !(await checkUrlExists(menu.fields["url"]));
                }),
        );
    }

    _isAllowedMove(current, elementSelector) {
        const currentIsMegaMenu = current.element.dataset.isMegaMenu === "true";
        if (!currentIsMegaMenu) {
            return (
                current.placeHolder.parentNode.closest(
                    `${elementSelector}[data-is-mega-menu="true"]`,
                ) === null
            );
        }
        const isDropOnRoot =
            current.placeHolder.parentNode.closest(elementSelector) === null;
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
        log.logic("moveMenu", () => ({
            menuId,
            toRoot: !parent,
            afterSibling: Boolean(previous),
        }));

        const parentId = menu.fields["parent_id"] || this.state.rootMenu.fields["id"];
        let parentMenu = this.map.get(parentId);
        parentMenu.children = parentMenu.children.filter(
            (m) => m.fields["id"] !== menuId,
        );

        const menuParentId = parent
            ? this._getMenuIdForElement(parent.closest("li"))
            : this.state.rootMenu.fields["id"];
        parentMenu = this.map.get(menuParentId);
        menu.fields["parent_id"] = parentMenu.fields["id"];

        if (previous) {
            const previousMenu = this.map.get(this._getMenuIdForElement(previous));
            const index = parentMenu.children.findIndex(
                (menu) => menu === previousMenu,
            );
            parentMenu.children.splice(index + 1, 0, menu);
        } else {
            parentMenu.children.unshift(menu);
        }
    }

    addMenu(isMegaMenu) {
        log.logic("addMenu", () => ({ isMegaMenu, menus: this.map.size }));
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
                log.pipeline("addMenu saved new menu", () => ({
                    id: newMenu.fields.id,
                    url: newMenu.fields.url,
                }));
                this.state.rootMenu.children.push(newMenu);
                this.map.set(newMenu.fields["id"], newMenu);
                this.checkMenuUrlExists(newMenu, url);
            },
        });
    }

    editMenu(id) {
        const menuToEdit = this.map.get(id);
        log.logic("editMenu", { id });
        this.dialogs.add(MenuDialog, {
            name: menuToEdit.fields["name"],
            url: menuToEdit.fields["url"],
            isMegaMenu: menuToEdit.fields["is_mega_menu"],
            save: (name, url) => {
                log.pipeline("editMenu saved", { id, url });
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
        log.logic("deleteMenu", () => ({ id, name: this.map.get(id)?.fields?.name }));
        const menuToDelete = this.map.get(id);

        for (const child of menuToDelete.children) {
            this.deleteMenu(child.fields.id);
        }

        const parentId =
            menuToDelete.fields["parent_id"] || this.state.rootMenu.fields["id"];
        const parent = this.map.get(parentId);
        parent.children = parent.children.filter((menu) => menu.fields["id"] !== id);
        this.map.delete(id);
        if (parseInt(id)) {
            log.pipeline("deleteMenu queued for server delete", { id });
            this.toDelete.push(id);
        }
    }

    async onClickSave(goToWebsite = true, url) {
        log.logic("save", () => ({ goToWebsite, url, menus: this.map.size }));
        const data = [];
        this.map.forEach((menu, id) => {
            if (this.state.rootMenu.fields["id"] !== id) {
                const menuFields = menu.fields;
                const parentId =
                    menuFields.parent_id || this.state.rootMenu.fields["id"];
                const parentMenu = this.map.get(parentId);
                menuFields["sequence"] = parentMenu.children.findIndex(
                    (m) => m.fields["id"] === id,
                );
                menuFields["parent_id"] = parentId;
                data.push(menuFields);
            }
        });
        log.pipeline("save collected", () => ({
            menus: data.length,
            toDelete: this.toDelete.length,
        }));

        const endSave = log.perf("website.menu save", () => ({ menus: data.length }));
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
            { context: { lang: this.website.currentWebsite.metadata.lang } },
        );
        endSave();
        log.logic("save done", () => ({
            customSave: Boolean(this.props.save),
            goToWebsite,
        }));
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
        log.logic("createPage from menu", { id, url });
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
