import { Plugin } from "@html_editor/plugin";
import { applyFunDependOnSelectorAndExclude } from "../utils";

export class TableOfContentOptionPlugin extends Plugin {
    static id = "tableOfContentOption";

    resources = {
        normalize_handlers: this.normalize.bind(this),
        force_not_editable_selector: [".s_table_of_content_navbar .table_of_content_link > *"],
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

        currentNavbarItems.map(
            (el, i) => (el.textContent = currentHeadingItems[i]?.textContent || "")
        );
    }
}
