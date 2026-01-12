import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class AccountAccountHierarchyListRenderer extends ListRenderer {

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);

        if (column.name === 'name') {
            return `${classNames} o_list_indent_${record.data.depth}`;
        }
        return classNames;

    }
}

export const AccountAccountHierarchyListView = {
    ...listView,
    Renderer: AccountAccountHierarchyListRenderer,
};

registry.category("views").add("account_hierarchy_list", AccountAccountHierarchyListView);
