import { registry } from "@web/core/registry";
import { MegaMenuDropdown } from "./mega_menu_dropdown";

const MegaMenuDropdownEdit = (I) => class extends I {
    dynamicContent = {
        ...this.dynamicContent,
        ".o_mega_menu_toggle": {
            ...this.dynamicContent[".o_mega_menu_toggle"],
            "t-on-shown.bs.dropdown": () => {
                // Focus the mega menu to show its options. Click is
                // listened to in BuilderOptionsPlugin to call updateContainers.
                this.waitForTimeout(() => {
                        document
                            .querySelector(".o_mega_menu")
                            .dispatchEvent(new PointerEvent("click", { bubbles: true }));
                });
            },
        },
    };

    setup() {
        super.setup();
        const hasMegaMenu = this.el.querySelector(".o_mega_menu_toggle");
        if (hasMegaMenu) {
            const bsDropdown = window.Dropdown.getOrCreateInstance(".o_mega_menu_toggle");
            this.registerCleanup(() => {
                bsDropdown.hide();
                bsDropdown.dispose();
            });
        }
    }
};

registry
    .category("public.interactions.edit")
    .add("website.mega_menu_dropdown", {
        Interaction: MegaMenuDropdown,
        mixin: MegaMenuDropdownEdit,
    });
