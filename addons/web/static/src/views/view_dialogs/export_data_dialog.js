/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { useSortable } from "@web/core/utils/ui";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { download } from "@web/core/network/download";

const { Component, useRef, useState } = owl;

export class ExportDataDialog extends Component {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");

        this.fieldsAvailableAll = {};
        this.state = useState({
            selectedFormat: 0,
            shouldUpdateData: false,
            templateSelection: null,
            fieldsToExport: null,
        });

        this.initializeData();
        this.availableFormats = ["XLSX", "CSV"];
        this.options = [];

        this.title = this.env._t("Export Data");
        this.newTemplateText = this.env._t("New template");
        this.removeFieldText = this.env._t("Remove field");

        useSortable({
            ref: this.draggableRef,
            setup: () => ({ items: ".o_export_field", cursor: "grabbing" }),
            onDrop: async ({ item, previous, next }) => {
                const indexes = [item, previous, next].map(
                    (e) => e && this.state.fieldsToExport.indexOf(e.dataset.field_id)
                );
                let target;
                if (indexes[0] < indexes[1]) {
                    target = previous ? indexes[1] : 0;
                } else {
                    target = next ? indexes[2] : this.state.fieldsToExport.length - 1;
                }
                this.onDraggingEnd([indexes[0], target]);
            },
        });
    }

    /**
     * Returns the current available fields for the user
     * It depends the current fields selected for export
     */
    get fieldsAvailable() {
        return Object.values(this.fieldsAvailableAll);
    }

    /**
     * Returns the currently selected fields to export
     * and display to the user on the right list
     */
    get fieldsToExport() {
        const fields = this.state.fieldsToExport.map((id) => this.fieldsAvailableAll[id]);
        return fields.sort((a, b) =>
            this.state.fieldsToExport.indexOf(a.id) < this.state.fieldsToExport.indexOf(b.id)
                ? -1
                : 1
        );
    }

    isFieldSelected(name) {
        return this.state.fieldsToExport.includes(name);
    }

    onDraggingEnd([item, target]) {
        this.state.fieldsToExport.splice(target, 0, this.state.fieldsToExport.splice(item, 1)[0]);
    }

    onAddItemExportList(ev) {
        this.state.fieldsToExport.push(ev.target.closest(".o_export_tree_item").dataset.field_id);
    }

    onRemoveItemExportList(ev) {
        const item = this.state.fieldsToExport.indexOf(ev.target.parentElement.dataset.field_id);
        this.state.fieldsToExport.splice(item, 1);
        //todo handle exportlist -> save template?
    }

    onChangeExportList(ev) {
        this.state.templateSelection = ev.target.value;
    }

    onSaveExportListEdition() {
        const name = this.exportListRef.el.value;
        if (!name) {
            this.notification.add(this.env._t("Please enter save field list name"), {
                type: "danger",
            });
            return;
        }
        console.log(`save the ${name} template`);
        this.options.push(name);
        this.state.templateSelection = name;
    }

    onClearExportListEdition() {
        this.state.templateSelection = null;
    }

    onUpdateDataChange() {
        // todo updateDataChange
    }

    async onExportButtonClicked() {
        const exportedFields = this.fieldsToExport.map((field) => ({
            name: field.name,
            label: field.string,
            store: field.store,
            type: field.type,
        }));
        const request = {
            data: {
                data: JSON.stringify({
                    context: this.props.context,
                    model: this.props.root.resModel,
                    ids: this.props.resIds,
                    fields: exportedFields,
                    domain: this.props.root.domain,
                    import_compat: false,
                    groupby: this.props.root.groupBy,
                }),
            },
            url: `/web/export/${this.availableFormats[this.state.selectedFormat].toLowerCase()}`,
        };
        console.log(request);
        await download(request);
    }

    async initializeData() {
        this.fieldsAvailableAll = this.props.root.fields;
        this.state.fieldsToExport = Object.values(this.props.root.activeFields).map((i) => i.name);
    }

    close() {
        this.props.close();
    }
}
ExportDataDialog.components = { Dialog, CheckBox };
ExportDataDialog.template = "web.ExportDataDialog";
