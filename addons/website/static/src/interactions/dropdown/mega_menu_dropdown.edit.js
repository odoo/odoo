import { registry } from "@web/core/registry";
import { MegaMenuDropdown } from "./mega_menu_dropdown";

const MegaMenuDropdownEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            ".o_mega_menu_toggle": {
                ...this.dynamicContent[".o_mega_menu_toggle"],
                "t-on-click": (ev) => {
                    const toggleEl = ev.currentTarget;
                    const megaMenuEl = toggleEl.parentElement.querySelector(".o_mega_menu");
                    // Activate the mega menu options when shown.
                    if (!megaMenuEl || !megaMenuEl.classList.contains("show")) {
                        this.websiteEditService.callShared(
                            "builderOptions",
                            "deactivateContainers"
                        );
                    } else {
                        this.websiteEditService.callShared(
                            "builderOptions",
                            "updateContainers",
                            megaMenuEl
                        );
                    }
                },
            },
        };

        setup() {
            super.setup();
            this.websiteEditService = this.services.website_edit;

            // Hide all the open mega menus when destroying the interaction.
            this.registerCleanup(() => {
                const megaMenuToggleEls = this.el.querySelectorAll(".o_mega_menu_toggle.show");
                for (const megaMenuToggleEl of megaMenuToggleEls) {
                    const bsDropdown = window.Dropdown.getOrCreateInstance(megaMenuToggleEl);
                    bsDropdown.hide();
                    bsDropdown.dispose();
                }
            });
        }
    };

registry.category("public.interactions.edit").add("website.mega_menu_dropdown", {
    Interaction: MegaMenuDropdown,
    mixin: MegaMenuDropdownEdit,
});
