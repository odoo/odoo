import { registry } from "@web/core/registry";
import { TableOfContentOptionPlugin } from "../../options/table_of_content_option_plugin";

export class TranslateTableOfContentOptionPlugin extends TableOfContentOptionPlugin {
    static dependencies = [...super.dependencies, "savePlugin"];

    getNavbarContainer(tableOfContentEl) {
        const containerEl = super.getNavbarContainer(tableOfContentEl);
        // If there is no heading elements in the snippet, there is no links,
        // and thus no translation span. Hence the falllback
        return containerEl.querySelector(":scope > [data-oe-translation-state]") || containerEl;
    }

    updateTableOfContentNavbar(tableOfContentMain) {
        const tableOfContentEl = tableOfContentMain.closest(".s_table_of_content");
        const tableOfContentNavbarContentEl = this.getNavbarContainer(tableOfContentEl);
        const tableOfContentNavbarContentBefore = tableOfContentNavbarContentEl.innerHTML;
        super.updateTableOfContentNavbar(tableOfContentMain);
        const tableOfContentNavbarContentAfter = tableOfContentNavbarContentEl.innerHTML;
        if (tableOfContentNavbarContentEl.matches("[data-oe-translation-state]")) {
            if (tableOfContentNavbarContentBefore !== tableOfContentNavbarContentAfter) {
                this.dependencies.savePlugin.setDirtyElement(tableOfContentNavbarContentEl);
            }
        }
    }
}

registry
    .category("translation-plugins")
    .add(TranslateTableOfContentOptionPlugin.id, TranslateTableOfContentOptionPlugin);
