import { ListRenderer } from "@web/views/list/list_renderer";
import { useEffect } from "@odoo/owl";

export class SectionListRenderer extends ListRenderer {
    setup() {
        super.setup();

        this.displayType = "line_section";
        this.titleField = "title";

        useEffect(
            (table) => {
                if (table) {
                    table.classList.add("o_section_list_view");
                }
            },
            () => [this.tableRef.el]
        );
    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isSection(record)) {
            return this.getSectionColumns(columns);
        }
        return columns;
    }

    getRowClass(record) {
        const classNames = super.getRowClass(record).split(" ");
        if (this.isSection(record)) {
            classNames.push(`o_is_${this.displayType}`, `fw-bold`);
        }
        return classNames.join(" ");
    }

    getSectionColumns(columns) {
        const sectionColumns = columns.filter((col) => col.widget === "handle");
        let colspan = columns.length - sectionColumns.length;
        if (this.activeActions.onDelete) {
            colspan++;
        }
        const titleCol = columns.find(
            (col) => col.type === "field" && col.name === this.titleField
        );
        sectionColumns.push({ ...titleCol, colspan });
        return sectionColumns;
    }

    isSection(record) {
        return record.data.display_type === this.displayType;
    }
}
SectionListRenderer.recordRowTemplate = "resource.SectionListRenderer.RecordRow";
