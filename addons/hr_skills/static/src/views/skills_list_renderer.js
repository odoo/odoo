/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

export class CommonSkillsListRenderer extends ListRenderer {
    get colspan() {
        const span = this.allColumns.length;
        if (this.isEditable) {
            return span + 1;
        }

        return span;
    }

    get groupBy() {
        return '';
    }

    get groupedList() {
        const grouped = {};

        for (const record of this.list.records) {
            const data = record.data;
            const group = data[this.groupBy];

            if (grouped[group[1]] === undefined) {
                grouped[group[1]] = {
                    id: parseInt(group[0]),
                    name: group[1] || _t('Other'),
                    list: {
                        records: [],
                    },
                };
            }

            grouped[group[1]].list.records.push(record);
        }
        return grouped;
    }

    get showTable() {
        return this.props.list.records.length;
    }

    get isEditable() {
        return this.props.editable !== false;
    }

    async onCellClicked(record, column, ev) {
        if (!this.isEditable) {
            return;
        }

        return await super.onCellClicked(record, column, ev);
    }
}
CommonSkillsListRenderer.rowsTemplate = "hr_skills.SkillsListRenderer.Rows";
