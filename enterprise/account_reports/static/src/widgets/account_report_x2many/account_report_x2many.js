/** @odoo-module **/

import { useRef, onWillRender } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useOpenX2ManyRecord, useX2ManyCrud } from "@web/views/fields/relational_utils";

export class AccountReportListRenderer extends ListRenderer {
    static template = "account_reports.AccountReportList";

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        // From ListRenderer
        // We can't really use `super.setup()` because it expects to be used on a html table.
        this.allColumns = this.processAllColumn(this.props.archInfo.columns, this.props.list);
        this.keyOptionalFields = `optional_fields,${this.createViewKey()}`;
        this.optionalActiveFields = this.computeOptionalActiveFields();
        this.columns = this.getActiveColumns(this.props.list);

        this.env.model.config.activeFields.line_ids.defaultOrderBy = [
            {
                "name": "sequence",
                "asc": true
            },
            {
                "name": "id",
                "asc": true
            }
        ]

        useNestedSortable({
            ref: useRef("root"),
            elements: "li.draggable",
            nest: true,
            nestInterval: 10,
            onDragStart: (ctx) => this.onDragStart(ctx),
            onDragEnd: () => this.onDragEnd(),
            onDrop: (ctx) => this.onDrop(ctx),
        });

        onWillRender(() => {
            this.allColumns = this.processAllColumn(this.props.archInfo.columns, this.props.list);
            this.columns = this.getActiveColumns(this.props.list);
        });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Records
    //------------------------------------------------------------------------------------------------------------------
    recordsDataDeepCopy(records) {
        const fields = this.allColumns.map((column) => column.name);

        return records.map((record) => {
            let recordData = {};

            for (const field of fields)
                recordData[field] = record.data[field];

            return recordData;
        });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Format
    //------------------------------------------------------------------------------------------------------------------
    formatData() {
        let idToIndexMap = {};
        let tree = [];

        let lines = this.recordsDataDeepCopy(this.props.list.records);

        for (const [index, line] of lines.entries()) {
            line.index = index;
            line.children = [];
            line.descendants_count = 0;

            idToIndexMap[line.id] = index;

            if (line.parent_id?.[0]) {
                let parentLine = lines[idToIndexMap[line.parent_id[0]]];

                if (parentLine) {
                    parentLine?.children.push(line);

                    while (parentLine) {
                        parentLine.descendants_count += 1;
                        parentLine = lines[idToIndexMap[parentLine.parent_id?.[0]]];
                    }
                } else {
                    // Since the parentLine doesn't exist yet. It means that this line is out of sequence.
                    line.out_of_sequence_error = true;

                    tree.push(line);
                }
            } else {
                tree.push(line);
            }
        }

        return tree;
    }

    //------------------------------------------------------------------------------------------------------------------
    // Placeholder
    //------------------------------------------------------------------------------------------------------------------
    onDragStart(ctx) {
        function sanitize(element) {
            if (element.nodeName === 'LI') {
                ["data-record_index", "data-record_id", "data-descendants_count"].forEach((attribute) => {
                    element.removeAttribute(attribute);
                });

                element.classList.remove("draggable");
            }

            Array.from(element.childNodes).forEach((child) => {
                sanitize(child);
            });
        }

        const placeholder = ctx.element.cloneNode(true);

        placeholder.removeAttribute("style");
        placeholder.classList.replace("o_dragged", "o_dragged_placeholder");

        sanitize(placeholder);

        document.querySelector(".o_nested_sortable_placeholder").after(placeholder);
    }

    onDragEnd() {
        // Clear placeholder
        document.querySelector(".o_dragged_placeholder").remove();
    }

    //------------------------------------------------------------------------------------------------------------------
    // Nested sorting
    //------------------------------------------------------------------------------------------------------------------
    async setRecordParent(currentElement, parentElement) {
        const currentRecordIndex = currentElement.dataset.record_index;
        const parentRecordIndex = parentElement?.dataset.record_index;

        // Default root element
        let parent = false;

        // parentRecordIndex is a string. It should be true with '0'.
        if (parentRecordIndex) {
            parent = [
                this.props.list.records[parentRecordIndex].data.id,
                this.props.list.records[parentRecordIndex].data.name,
            ];
        }

        await this.props.list.records[currentRecordIndex].update({'parent_id': parent});
    }

    async setRecordHierarchy(currentElement, parentElement) {
        const currentRecordIndex = parseInt(currentElement.dataset.record_index);
        const parentRecordIndex = parentElement?.dataset.record_index;
        const parentRecord = (parentRecordIndex) ? this.props.list.records[parentRecordIndex].data : null;

        const hierarchyLevels = {};

        if (parentRecord)
            hierarchyLevels[parentRecord.id] = parentRecord.hierarchy_level;

        const ancestors = new Set();

        for (let index = currentRecordIndex; index < this.props.list.records.length; index++) {
            const record = this.props.list.records[index];
            const parentId = (record.data.parent_id) ? record.data.parent_id[0] : false;

            if (ancestors.size && !ancestors.has(parentId))
                break;

            let parentHierarchyLevel = (record.data.parent_id) ? hierarchyLevels[record.data.parent_id[0]] : null;

            if (parentHierarchyLevel != null) {
                parentHierarchyLevel = (parentHierarchyLevel === 0) ? 1 : parentHierarchyLevel;
                await record.update({'hierarchy_level': parentHierarchyLevel + 2});
            } else {
                await record.update({'hierarchy_level': 1});
            }

            ancestors.add(record.data.id);
            hierarchyLevels[record.data.id] = record.data.hierarchy_level;
        }
    }

    async setRecordSequence(currentElement, parentElement, previousElement, previousElementDescendantCount, nextElement) {
        const currentRecordIndex = currentElement.dataset.record_index;
        const currentRecordDescendantsCount = parseInt(currentElement.dataset.descendants_count);
        const lastDescendantIndex = parseInt(currentRecordIndex) + currentRecordDescendantsCount
        const recordsToMove = this.props.list.records.slice(currentRecordIndex, lastDescendantIndex + 1);

        // We remove the element(s) we are moving
        this.props.list.records.splice(currentRecordIndex, recordsToMove.length);

        const previousRecordIndex = previousElement?.dataset.record_index;
        const nextRecordIndex = nextElement?.dataset.record_index;

        let newCurrentRecordIndex;

        if (previousRecordIndex) {
            newCurrentRecordIndex = parseInt(previousRecordIndex) + 1 + parseInt(previousElementDescendantCount);
        } else if (nextRecordIndex) {
            // We add the element in the first position
            newCurrentRecordIndex = parseInt(nextRecordIndex);
        } else {
            // We add the element as a first child
            newCurrentRecordIndex = parseInt(parentElement?.dataset.record_index) + 1;
        }

        // If the original position of the line we want to move is before the position we want to drop it, then we need
        // to adjust the index because all the indexes of the lines after it have changed (we removed lines).
        if (currentRecordIndex < newCurrentRecordIndex) {
            newCurrentRecordIndex -= (1 + currentRecordDescendantsCount);
        }

        // We add the element(s) we are moving into the new position
        this.props.list.records.splice(newCurrentRecordIndex, 0, ...recordsToMove);

        for (const [index, record] of this.props.list.records.entries())
            await record.update({'sequence': index + 1});
    }

    async onDrop(ctx) {
        const parentRecordIndex = ctx.parent?.dataset.record_index;

        // We can't drop a line if it's parent has a 'user_groupby`
        if (this.props.list.records[parentRecordIndex]?.data.user_groupby)
            return this.dialog.add(WarningDialog, {
                message: _t("A line with a 'Group By' value cannot have children."),
            });

        // We need to save it before as it's value might change during calculations below
        const previousElementDescendantCount = ctx.previous?.dataset.descendants_count

        await this.setRecordParent(ctx.element, ctx.parent);
        await this.setRecordHierarchy(ctx.element, ctx.parent);
        await this.setRecordSequence(ctx.element, ctx.parent, ctx.previous, previousElementDescendantCount, ctx.next);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Delete
    //------------------------------------------------------------------------------------------------------------------
    onDeleteRecord(recordIndex) {
        const currentRecordId = this.props.list.records[recordIndex].data.id
        const nextRecordParentId = this.props.list.records[recordIndex + 1]?.data.parent_id[0]

        // We check if the next line is a children of the current one
        if (nextRecordParentId === currentRecordId)
            return this.dialog.add(ConfirmationDialog, {
                body: _t("This line and all its children will be deleted. Are you sure you want to proceed?"),
                confirmLabel: "Delete",
                confirm: () => { this.deleteRecord(recordIndex) },
                cancel: () => {},
            });

        this.deleteRecord(recordIndex);
    }

    deleteRecord(recordIndex) {
        const recordToDelete = this.props.list.records[recordIndex];

        const recordsToDelete = [recordToDelete];
        const ancestors = new Set([recordToDelete.data.id]);

        // We get all the children of the line we are deleting
        for (let index = recordIndex + 1; index < this.props.list.records.length; index++) {
            const record = this.props.list.records[index];

            if (!ancestors.has(record.data.parent_id[0]))
                break;

            recordsToDelete.push(record);
            ancestors.add(record.data.id);
        }

        for (const record of recordsToDelete)
            this.props.list.delete(record);
    }
}

export class AccountReportsLinesListX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: AccountReportListRenderer,
    }

    // Overrides the "openRecord" method to overload the save. This will force the record to be saved in the database.
    setup() {
        super.setup();

        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                for (const [index, record] of this.props.record.data.line_ids.records.entries())
                    record.update({'sequence': index + 1});

                record.update({
                    'sequence': this.props.record.data.line_ids.records.length,
                });

                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: updateRecord,
            isMany2Many: this.isMany2Many,
        });

        this._openRecord = (params) => {
            const activeElement = document.activeElement;

            openRecord({
                ...params,
                onClose: () => {
                    if (activeElement) {
                        activeElement.focus();
                    }
                },
            });
        };
    }
}

registry.category("fields").add("account_report_lines_list_x2many", {
    ...x2ManyField,
    component: AccountReportsLinesListX2ManyField,
});
