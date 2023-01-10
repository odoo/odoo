/** @odoo-module */

import { makeContext } from "@web/core/context";
import { ListRenderer } from "@web/views/list/list_renderer";

const { useEffect } = owl;

export class QuestionPageListRenderer extends ListRenderer {
    setup() {
        super.setup();

        this.discriminant = "is_page";
        this.fieldsToShow = ["random_questions_count"];
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

    add(params) {
        let editable = false;
        if (params.context && !this.env.isSmall) {
            const evaluatedContext = makeContext([params.context]);
            if (evaluatedContext[`default_${this.discriminant}`]) {
                editable = this.props.editable;
            }
        }
        super.add({ ...params, editable });
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
            classNames.push(`o_is_section`, `fw-bold`);
        }
        return classNames.join(" ");
    }

    getSectionColumns(columns) {
        const sectionColumns = [];

        let titleColumnIndex = 0;
        for (const col of columns) {
            if (col.type !== "field") {
                continue;
            }
            if (col.widget === "handle") {
                titleColumnIndex = 1;
                sectionColumns.push(col);
                continue;
            }
            if (this.fieldsToShow.includes(col.name) && col.name !== this.titleField) {
                sectionColumns.push(col);
            }
        }

        const colspan = columns.length - sectionColumns.length;
        const titleCol = columns.find(
            (col) => col.type === "field" && col.name === this.titleField
        );
        sectionColumns.splice(titleColumnIndex, 0, { ...titleCol, colspan });

        return sectionColumns;
    }

    isInlineEditable(record) {
        return this.isSection(record) && this.props.editable;
    }

    isSection(record) {
        return record.data[this.discriminant];
    }

    onCellKeydownEditMode(hotkey) {
        switch (hotkey) {
            case "enter":
            case "tab":
            case "shift+tab": {
                this.props.list.unselectRecord(true);
                return true;
            }
        }
        return super.onCellKeydownEditMode(...arguments);
    }

    /**
     * Save the survey after a question used as trigger is deleted. This allows
     * immediate feedback on the form view as the triggers will be removed
     * anyway on the records by the ORM.
     *
     * @override
     * @param record
     * @return {Promise<void>}
     */
    async onDeleteRecord(record) {
        const triggeredRecords = this.props.list.records.filter(rec => rec.data.triggering_question_id[0] === record.data.id);
        if (triggeredRecords.length) {
            const res = await super.onDeleteRecord(record);
            await this.props.list.model.root.save({stayInEdition: true});
            return res;
        } else {
            return super.onDeleteRecord(record);
        }
    }
}
