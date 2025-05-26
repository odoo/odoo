import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { NavbarLinkPopover } from "@html_editor/main/link/navbar_link_popover";
import { MenuDialog, EditMenuDialog } from "@website/components/dialog/edit_menu";
import { withSequence } from "@html_editor/utils/resource";

export class MenuDataPlugin extends Plugin {
    static id = "menuDataPlugin";
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
                    onClickEditMenu: () => {
                        this.services.dialog.add(EditMenuDialog, {
                            save: async () => {
                                await this.config.reloadEditor({ url: this.document.URL });
                            },
                        });
                    },
                }),
            }),
        ],
    };
}

registry.category("website-plugins").add(MenuDataPlugin.id, MenuDataPlugin);
