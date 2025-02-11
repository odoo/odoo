/** @odoo-module */

import { makeContext } from "@web/core/context";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useEffect } from "@odoo/owl";

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

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (column.type === "button_group") {
            return `${classNames} text-end`;
        }
        return classNames;
    }

    getSectionColumns(columns) {
        let titleColumnIndex = 0;
        let found = false;
        let colspan = 1;
        for (let index = 0; index < columns.length; index++) {
            const col = columns[index];
            if (!found && col.name !== this.titleField) {
                continue;
            }
            if (!found) {
                found = true;
                titleColumnIndex = index;
                continue;
            }
            if (col.type !== "field" || this.fieldsToShow.includes(col.name)) {
                break;
            }
            colspan += 1;
        }

        const sectionColumns = columns
            .slice(0, titleColumnIndex + 1)
            .concat(columns.slice(titleColumnIndex + colspan));

        sectionColumns[titleColumnIndex] = { ...sectionColumns[titleColumnIndex], colspan };

        return sectionColumns;
    }

    isInlineEditable(record) {
        return this.isSection(record) && this.props.editable;
    }

    isSection(record) {
        return record.data[this.discriminant];
    }

    /**
     *
     * Overriding the method in order to identify the requested column based on its `name`
     * instead of the exact object passed. This is necessary for section rows because the
     * column object could have been replaced in `getSectionColumns` to add a `colspan`
     * attribute.
     *
     * @override
     */
    focusCell(column, forward = true) {
        const actualColumn = column.name
            ? this.state.columns.find((col) => col.name === column.name)
            : column;
        super.focusCell(actualColumn, forward);
    }

    onCellKeydownEditMode(hotkey) {
        switch (hotkey) {
            case "enter":
            case "tab":
            case "shift+tab": {
                this.props.list.leaveEditMode();
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
        const triggeredRecords = this.props.list.records.filter(
            (rec) => rec.data.triggering_question_ids.records.map(a => a.resId).includes(record.resId)
        );
        if (triggeredRecords.length) {
            const res = await super.onDeleteRecord(record);
            await this.props.list.model.root.save();
            return res;
        } else {
            return super.onDeleteRecord(record);
        }
    }
}
