import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { NavbarLinkPopover } from "./navbar_link_popover/navbar_link_popover";
import { MenuDialog, EditMenuDialog } from "@website/components/dialog/edit_menu";
import { withSequence } from "@html_editor/utils/resource";

export class MenuDataPlugin extends Plugin {
    static id = "menuDataPlugin";
    static shared = ["openEditMenu"];
    static dependencies = ["savePlugin"];
    resources = {
        link_popovers: [
            withSequence(10, {
                PopoverClass: NavbarLinkPopover,
                isAvailable: (linkElement) =>
                    linkElement &&
                    linkElement.closest(".top_menu, o_extra_menu_items, [data-content_menu_id]") &&
                    !linkElement.closest(
                        ".dropdown-toggle, li.o_header_menu_button a, [data-toggle], .o_offcanvas_logo, .o_mega_menu"
                    ),
                getProps: (props) => ({
                    ...props,
                    onClickEditLink: (elem, callback) => {
                        const menuEl = elem.props.linkElement.querySelector("[data-oe-id]");
                        this.services.dialog.add(MenuDialog, {
                            name: menuEl.textContent,
                            url: menuEl.parentElement.attributes["href"].nodeValue,
                            save: async (name, url) => {
                                const websiteId = this.services.website.currentWebsite.id;
                                const data = {
                                    id: parseInt(menuEl.attributes["data-oe-id"].nodeValue),
                                    name,
                                    url,
                                };
                                const result = await this.services.orm.call(
                                    "website.menu",
                                    "save",
                                    [websiteId, { data: [data] }]
                                );
                                menuEl.parentElement.attributes["href"].nodeValue = url;
                                menuEl.textContent = name;
                                callback();
                                return result;
                            },
                        });
                    },
                    onClickEditMenu: this.openEditMenu.bind(this, props.linkElement),
                }),
            }),
        ],
        is_link_editable_predicates: this.isMenuLink.bind(this),
    };

    setup() {
        this.websiteService = this.services.website;
    }

    openEditMenu(linkEl) {
        if (this.isEditMenuOpening) {
            return Promise.resolve();
        }
        this.isEditMenuOpening = true;
        return new Promise((resolve) => {
            const rootID = parseInt(
                linkEl?.closest("[data-content_menu_id]")?.dataset.content_menu_id
            );
            this.services.dialog.add(
                EditMenuDialog,
                {
                    rootID: isNaN(rootID) ? null : rootID,
                    save: async (newPageUrl) => {
                        // Save the page before reloading the editor.
                        await this.dependencies.savePlugin.save();
                        await this.config.reloadEditor();
                        if (newPageUrl) {
                            this.websiteService.goToWebsite({
                                path: newPageUrl,
                                edition: true,
                                websiteId: this.websiteService.currentWebsite.id,
                            });
                        }
                    },
                },
                {
                    onClose: () => {
                        this.isEditMenuOpening = false;
                        resolve();
                    },
                }
            );
        });
    }

    /**
     * This predicate is used to determine if the link element is editable.
     * It checks if the link element is a menu item or a nav link
     * @param {HTMLElement} linkElement - The link element to check.
     * @returns {boolean} - True if the link element is editable, false otherwise.
     */
    isMenuLink(linkElement) {
        return (
            linkElement &&
            (linkElement.getAttribute("role") === "menuitem" ||
                linkElement.classList.contains("nav-link")) &&
            !linkElement.dataset.bsToggle
        );
    }
}

registry.category("website-plugins").add(MenuDataPlugin.id, MenuDataPlugin);
