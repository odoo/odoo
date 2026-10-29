import { useKeyboardReorder } from "@html_builder/utils/keyboard_reorder";
import {
    Component,
    onWillStart,
    onPatched,
    proxy,
    signal,
    t,
    useApp,
    useEffect,
    useProps,
} from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import wUtils from "@website/js/utils";
import { WebsiteDialog } from "./dialog";
import { rpc } from "@web/core/network/rpc";
import { isEmail } from "@web/core/utils/strings";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { isAbsoluteURLInCurrentDomain } from "@html_editor/utils/url";
import { useDebounced } from "@web/core/utils/timing";
import { KeepLast } from "@web/core/utils/concurrency";

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
    props = useProps({
        name: t.string().optional(),
        url: t.string().optional(),
        isMegaMenu: t.boolean().optional(),
        hasChildren: t.boolean().optional(),
        save: t.function(),
        close: t.function(),
    });

    autofocusRef = signal.ref();

    setup() {
        this.website = useService("website");
        useAutofocus({ ref: this.autofocusRef });

        this.urlInputRef = signal.ref(HTMLInputElement);
        this.urlInputEdited = !!this.props.url;

        this.state = proxy({
            pageNotFound: false,
            url: this.props.url,
            name: this.props.name,
            isMegaMenu: this.props.isMegaMenu,
            invalidName: false,
            invalidUrl: false,
        });

        const keepLast = new KeepLast();
        const updatePageNotFound = (url) =>
            keepLast.add(checkUrlExists(url)).then((exists) => (this.state.pageNotFound = !exists));
        const debouncedUpdatePageNotFound = useDebounced(updatePageNotFound, 500);
        useEffect(() => debouncedUpdatePageNotFound(this.state.url));

        const app = useApp();
        useEffect(() => {
            const input = this.urlInputRef();
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
            const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(app, input, options);
            return () => unmountAutocompleteWithPages();
        });
    }

    getUrl() {
        let url = this.state.url;
        if (!this.state.isMegaMenu) {
            try {
                url = toRelativeIfSameDomain(url);
            } catch {
                // Do nothing if URL is invalid.
            }
        }
        return url;
    }

    onClickOk() {
        this.state.invalidName = !this.state.name;
        if (this.state.invalidName) {
            return;
        }

        this.props.save(this.state.name, this.getUrl(), this.state.isMegaMenu);
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
        if (!this.urlInputEdited && !this.state.isMegaMenu) {
            const title = ev.target.value;
            this.state.url = title ? "/" + wUtils.slugify(title) : "";
        }
    }
}

class MenuRow extends Component {
    static template = "website.MenuRow";
    props = useProps({
        menu: t.object(),
        edit: t.function(),
        delete: t.function(),
        createPage: t.function(),
        keyboardReorder: t.object(),
    });
    static components = {
        MenuRow,
    };

    setup() {
        onPatched(() => this.props.keyboardReorder.restoreFocus());
    }

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

function getMenuIdForElement(element) {
    const menuIdStr = element.dataset.menuId;
    return isNaN(menuIdStr) ? menuIdStr : parseInt(menuIdStr);
}

class MenuEditor extends Component {
    static template = "website.MenuEditor";
    static components = { MenuRow };
    props = useProps({
        rootMenu: t.object(),
        menus: t.instanceOf(Map),
        edit: t.function(),
        delete: t.function(),
        createPage: t.function(),
        moveMenu: t.function(),
    });

    menuEditorRef = signal.ref();

    setup() {
        this.keyboardReorder = useKeyboardReorder({
            getItemsInList: (menuId) =>
                this.getParentMenu(menuId).children.map((menu) => menu.fields["id"]),
            moveItemAfter: (menuId, previousMenuId) =>
                this.props.moveMenu(
                    menuId,
                    this.getParentMenu(menuId).fields["id"],
                    previousMenuId
                ),
            changeNesting: (menuId, direction) => this.changeMenuNesting(menuId, direction),
            getHandle: (menuId) =>
                this.menuEditorRef().querySelector(
                    `li[data-menu-id="${menuId}"] > .input-group > .o_drag_handle`
                ),
        });

        useNestedSortable({
            ref: this.menuEditorRef,
            handle: "div",
            nest: true,
            maxLevels: 2,
            onDragStart: () => this.menuEditorRef().classList.add("o_menu_editor_dragging"),
            onDragEnd: () => this.menuEditorRef().classList.remove("o_menu_editor_dragging"),
            onDrop: ({ element, parent, previous }) =>
                this.props.moveMenu(
                    getMenuIdForElement(element),
                    parent && getMenuIdForElement(parent.closest("li")),
                    previous && getMenuIdForElement(previous)
                ),
            isAllowed: this.isAllowedMove.bind(this),
            useElementSize: true,
            /**
             * @param {DOMElement} element - moved element
             * @param {DOMElement} parent - parent element of where the element
             *      was moved
             * @param {DOMElement} placeholder - hint element showing the
             *      current position
             */
            onMove: ({ element, placeholder, parent }) => {
                // Adapt the dragged menu item to match the width and position
                // of the placeholder.
                element.style.width = getComputedStyle(placeholder).width;
                element.style.marginLeft =
                    parent && element.parentElement === this.menuEditorRef() ? "2rem" : "";
            },
            // Prevent starting a drag from the action buttons (edit, delete),
            // but not from the drag handle itself, which is also a button.
            preventDrag: (el) => el.querySelector(":scope > button:not(.o_drag_handle)"),
        });
    }

    isAllowedMove(current, elementSelector) {
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

    /**
     * @param {number|string} menuId
     * @returns {Object} the parent menu, the root menu for a top-level menu
     */
    getParentMenu(menuId) {
        const parentId = this.props.menus.get(menuId).fields["parent_id"];
        return parentId ? this.props.menus.get(parentId) : this.props.rootMenu;
    }

    /**
     * Nests (1) or un-nests (-1) a menu, with the same restrictions as the drag
     * and drop (see `isAllowedMove`).
     *
     * @param {number|string} menuId
     * @param {1|-1} direction
     * @returns {boolean} whether the menu moved
     */
    changeMenuNesting(menuId, direction) {
        const move = direction === 1 ? this.getNestMove(menuId) : this.getUnnestMove(menuId);
        if (!move) {
            return false;
        }
        this.props.moveMenu(menuId, move.parentId, move.previousId);
        return true;
    }

    /**
     * Returns the move parameters for nesting a menu as the last child of its
     * previous sibling.
     *
     * @param {number|string} menuId
     * @returns {Object|null} null if the nesting is not allowed
     */
    getNestMove(menuId) {
        const menu = this.props.menus.get(menuId);
        const parentMenu = this.getParentMenu(menuId);
        const index = parentMenu.children.findIndex((m) => m.fields["id"] === menuId);
        const prevSiblingMenu = parentMenu.children[index - 1];
        // Mega menus stay at the root and the tree is limited to `maxLevels`.
        if (
            !prevSiblingMenu ||
            menu.fields["is_mega_menu"] ||
            prevSiblingMenu.fields["is_mega_menu"] ||
            menu.children.length ||
            parentMenu.fields["id"] !== this.props.rootMenu.fields["id"]
        ) {
            return null;
        }
        return {
            parentId: prevSiblingMenu.fields["id"],
            previousId: prevSiblingMenu.children.at(-1)?.fields["id"],
        };
    }

    /**
     * Returns the move placing a menu right after its parent menu.
     *
     * @param {number|string} menuId
     * @returns {Object|null} null if the menu is already at the root
     */
    getUnnestMove(menuId) {
        const parentMenu = this.getParentMenu(menuId);
        if (parentMenu.fields["id"] === this.props.rootMenu.fields["id"]) {
            return null;
        }
        // The tree has two levels, so un-nesting always moves to the root (no
        // `parentId`).
        return { previousId: parentMenu.fields["id"] };
    }
}

export class EditMenuDialog extends Component {
    static template = "website.EditMenuDialog";
    static components = {
        MenuEditor,
        WebsiteDialog,
    };
    props = useProps({
        rootID: t.or([t.number(), t.literal(null)]).optional(),
        close: t.function(),
        save: t.function().optional(),
    });

    setup() {
        this.orm = useService("orm");
        this.website = useService("website");
        this.dialogs = useService("dialog");

        this.state = proxy({ rootMenu: {} });

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

    /**
     * @param {number|string} menuId
     * @param {number|string} [parentId] the new parent menu, none for the root
     *      menu
     * @param {number|string} [previousId] the new previous sibling, none to
     *      move the menu first
     */
    moveMenu(menuId, parentId, previousId) {
        const menu = this.map.get(menuId);

        // Remove element from parent's children (since we are moving it, this is the mandatory first step)
        const oldParentId = menu.fields["parent_id"] || this.state.rootMenu.fields["id"];
        let parentMenu = this.map.get(oldParentId);
        parentMenu.children = parentMenu.children.filter((m) => m.fields["id"] !== menuId);

        // Determine next parent
        parentMenu = this.map.get(parentId || this.state.rootMenu.fields["id"]);
        menu.fields["parent_id"] = parentMenu.fields["id"];

        // Determine at which position we should place the element
        if (previousId) {
            const previousMenu = this.map.get(previousId);
            const index = parentMenu.children.findIndex((menu) => menu === previousMenu);
            parentMenu.children.splice(index + 1, 0, menu);
        } else {
            parentMenu.children.unshift(menu);
        }
    }

    addMenu() {
        this.dialogs.add(MenuDialog, {
            url: "",
            save: (name, url, isMegaMenu) => {
                const newMenu = proxy({
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
            hasChildren: menuToEdit.children.length > 0,
            save: (name, url, isMegaMenu) => {
                menuToEdit.fields["name"] = name;
                menuToEdit.fields["url"] = isMegaMenu || !url ? "#" : url;
                menuToEdit.fields["is_mega_menu"] = isMegaMenu;
                menuToEdit.page_not_found = false;
                menuToEdit.is_homepage = !isMegaMenu && menuToEdit.is_homepage;
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
            onAddPage: ({ createdUrl }) => {
                if (createdUrl) {
                    menu.fields["url"] = createdUrl;
                }
                this.onClickSave(false, createdUrl ?? url);
            },
            websiteId: this.website.currentWebsite.id,
            forcedURL: url,
            goToPage: !this.props.save,
            pageTitle: menu.fields["name"],
        });
    }
}
