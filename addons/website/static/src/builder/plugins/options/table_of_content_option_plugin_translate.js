import { Plugin } from "@html_editor/plugin";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";

export class TranslateTableOfContentOptionPlugin extends Plugin {
    static id = "tableOfContentOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        normalize_handlers: this.normalize.bind(this),
        content_not_editable_selectors: [".s_table_of_content_navbar"],
    };

    normalize(root) {
        applyFunDependOnSelectorAndExclude(this.updateTableOfContentNavbar.bind(this), root, {
            selector: ".s_table_of_content_main",
        });
    }

    updateTableOfContentNavbar(tableOfContentMain) {
        const tableOfContent = tableOfContentMain.closest(".s_table_of_content");
        const tableOfContentNavbar = tableOfContent.querySelector(".s_table_of_content_navbar");
        const currentNavbarItems = [...tableOfContentNavbar.children].map((el) => el.firstChild);

        const targetedElements = "h1, h2";
        const currentHeadingItems = [
            ...tableOfContentMain.querySelectorAll(targetedElements),
        ].filter((el) => !el.closest(".o_snippet_desktop_invisible"));

        currentNavbarItems.map((el, i) => {
            const newText = currentHeadingItems[i]?.textContent || "";
            if (el.textContent !== newText) {
                el.textContent = newText;
            }

            const newHref = `#${currentHeadingItems[i]?.id}`;
            if (newHref && el.parentElement.getAttribute("href") !== newHref) {
                el.parentElement.setAttribute("href", newHref);
            }
        });
    }
}
