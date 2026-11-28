import {
    clickOnExtraMenuItem,
    clickOnSave,
    openLinkPopup,
    waitForEditMode,
} from "@website/js/tours/tour_utils";
import { addMegaMenu } from "@website/../tests/tours/edit_menus";
import { registry } from "@web/core/registry";

const snippet =
    ":iframe .s_mega_menu_odoo_menu .s_product_categories:has(.nav-link:contains(Child))";

const toggleMegaMenu = {
    content: "Toggle the mega menu",
    trigger: ":iframe .top_menu .nav-item a.o_mega_menu_toggle",
    async run({ click, waitUntil }) {
        const isOpen = this.anchor.getAttribute("aria-expanded") === "true";
        if (isOpen || this.anchor.closest(".o_extra_menu_items")) {
            return;
        }
        await click();
        await waitUntil(() => this.anchor.getAttribute("aria-expanded") === "true", {
            timeout: 3000,
        });
    },
};

registry.category("web_tour.tours").add("mega_menu_product_categories", {
    steps: () => [
        waitForEditMode,
        ...openLinkPopup({
            trigger: ":iframe .top_menu .nav-item a:contains('Home')",
            label: "Home",
        }),
        {
            content: "Open the menu editor",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        ...addMegaMenu("Shop by Category"),
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu,
        {
            content: "Check that the new mega menu has a snippet for the top-level category",
            trigger: `${snippet} a[name='category_heading']:contains(Tour Parent)`,
        },
        {
            content: "Rename a child category in the editor",
            trigger: `${snippet} .nav-link [data-oe-field='name']:contains(Tour Child)`,
            run: "editor Renamed Child",
        },
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu,
        {
            content: "Check that the category itself was renamed",
            trigger: `${snippet} .nav-link:contains(Renamed Child)`,
        },
    ],
});
