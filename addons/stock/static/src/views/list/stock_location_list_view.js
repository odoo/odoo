import { onWillRender } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class StockLocationHierarchyListRenderer extends ListRenderer {
    setup() {
        super.setup();
        onWillRender(() => {
            const { list } = this.props;
            this.visibleLocationIds = list.records.map((record) => record.data.id);
            this.hierarchyIndentationEnabled =
                list.orderBy.length === 0 && // avoid indentation in case of ordering
                this.isGroupByIndentationCompatible(list.groupBy) &&
                this.isDomainIndentationCompatible(list.domain);
            if (this.hierarchyIndentationEnabled) {
                list.records.map(record => {
                    record.hierarchyDepth = this._computeHierarchyDepth(record);
                });
            }
        });
    }

    _computeHierarchyDepth(record) {
        const currentPath = record.data.parent_path;
        const allLocationIds = currentPath.split("/");
        allLocationIds.pop(); // Remove last element which is an empty string.
        let invisibleParentsCount = 0;
        for (const id of allLocationIds) {
            if (!this.visibleLocationIds.includes(Number(id))) {
                invisibleParentsCount++;
            }
        }
        return allLocationIds.length - 1 - invisibleParentsCount;
    }

    getCellClass(column, record) {
        let classNames = super.getCellClass(column, record);
        // Adds indentation to child records based on hierarchy depth in list view.
        if (this.mustBeIndented(column, record)) {
            // Hard limitation: the indentation works up to 10 levels, after that,
            // all child records are on the same level even if some are parent of others.
            const depth = Math.min(record.hierarchyDepth, 10);
            if (depth > 0) {
                classNames = `${classNames} o_list_indent_${depth}`;
            }
        }
        return classNames;
    }

    getFormattedValue(column, record) {
        if (this.mustBeIndented(column, record) && record.hierarchyDepth > 0) {
            record.data.complete_name = record.data.name;
        }
        return super.getFormattedValue(...arguments);
    }

    mustBeIndented(column, record) {
        return this.hierarchyIndentationEnabled &&
            column.name === "complete_name" &&
            record.data.parent_path;
    }

    isDomainIndentationCompatible(domain) {
        if (domain.length > 0) {
            const compatibleFields = ["location_id", "usage"];
            for (const leaf of domain) {
                if (Array.isArray(leaf) && leaf.length === 3) {
                    if (!compatibleFields.includes(leaf[0])) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    isGroupByIndentationCompatible(groupBy) {
        if (this.props.list.groupBy.length > 0) {
            const compatibleFields = ["warehouse_id"];
            for (const field of groupBy) {
                if (!compatibleFields.includes(field)) {
                    return false;
                }
            }
        }
        return true;
    }
}

export const StockLocationHierarchyListView = {
    ...listView,
    Renderer: StockLocationHierarchyListRenderer,
};

registry.category("views").add("stock_location_hierarchy_list", StockLocationHierarchyListView);
