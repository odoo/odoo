import { registry } from "@web/core/registry";
import { TableOfContent } from "./table_of_content";

export const TableOfContentEdit = (I) =>
    class extends I {
        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            if (this.el.classList.contains("s_table_of_content_horizontal_navbar")) {
                snapshot = JSON.parse(snapshot || "{}");
                snapshot.horizontalNavbar = true;
                snapshot = JSON.stringify(snapshot);
            }
            return snapshot;
        }
    };

registry.category("public.interactions.edit").add("website.table_of_content", {
    Interaction: TableOfContent,
    mixin: TableOfContentEdit,
});
