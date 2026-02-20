import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class AccountAccountHierarchyListRenderer extends ListRenderer {
    getCellClass(column, record) {
        let classNames = super.getCellClass(column, record);

        // adds indentation to child accounts based on hierarchy depth in list view
        if (
            this.props.list.domain.length === 0 && // avoid indentation in case of filtering
            this.props.list.orderBy.length === 0 && // avoid indentation in case of ordering
            this.props.list.groupBy.length === 0 && // avoid indentation in case of grouping
            record.data.parent_path &&
            column.name === "name"
        ) {
            const depth = record.data.parent_path.split("/").length - 2;
            classNames = `${classNames} o_list_indent_${depth}`;
        }
        return classNames;
    }
}

export const AccountAccountHierarchyListView = {
    ...listView,
    Renderer: AccountAccountHierarchyListRenderer,
};

registry.category("views").add("account_hierarchy_list", AccountAccountHierarchyListView);
