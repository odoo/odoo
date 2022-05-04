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
        this.rpc = useService("rpc");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");

        this.fieldsAvailableAll = {};
        this.availableFormats = [];
        this.templates = [];

        this.state = useState({
            selectedFormat: 0,
            importCompatibleData: false,
            templateSelection: null,
            fieldsToExport: [],
            templateisEditing: false,
        });

        this.initializeData();

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

    handleTemplateEdition() {
        if (this.state.templateSelection && !this.state.templateisEditing) {
            this.state.templateisEditing = true;
        }
    }

    isFieldSelected(name) {
        return this.state.fieldsToExport.includes(name);
    }

    async loadExportList(value) {
        this.state.templateSelection = value;
        if (value === "new_template") {
            this.state.templateisEditing = true;
            return;
        }
        this.state.templateisEditing = false;
        const list = await this.rpc("/web/export/namelist", {
            model: this.props.root.resModel,
            export_id: Number(value),
        });
        const newList = [];
        list.forEach((field) => {
            newList.push(field.name);
        });
        this.state.fieldsToExport = newList;
    }

    onDraggingEnd([item, target]) {
        this.state.fieldsToExport.splice(target, 0, this.state.fieldsToExport.splice(item, 1)[0]);
    }

    onAddItemExportList(ev) {
        this.state.fieldsToExport.push(ev.target.closest(".o_export_tree_item").dataset.field_id);
        this.handleTemplateEdition();
    }

    onRemoveItemExportList(ev) {
        const item = this.state.fieldsToExport.indexOf(ev.target.parentElement.dataset.field_id);
        this.state.fieldsToExport.splice(item, 1);
        this.handleTemplateEdition();
    }

    async onChangeExportList(ev) {
        this.loadExportList(ev.target.value);
    }

    async onSaveExportListEdition() {
        const name = this.exportListRef.el.value;
        if (!name) {
            this.notification.add(this.env._t("Please enter save field list name"), {
                type: "danger",
            });
            return;
        }

        const exportedFields = this.fieldsToExport.map((field) => [
            0,
            0,
            {
                name: field.name,
            },
        ]);

        const id = await this.rpc("/web/dataset/call_kw", {
            args: [
                {
                    name,
                    export_fields: exportedFields,
                    resource: this.props.root.resModel,
                },
            ],
            kwargs: {
                context: this.props.context,
            },
            model: "ir.exports",
            method: "create",
        });

        this.state.templateSelection = id;
        this.templates.push({ id, name });
    }

    onClearExportListEdition() {
        if (this.state.templateSelection === "new_template") {
            this.state.templateSelection = null;
            return;
        }
        this.loadExportList(this.state.templateSelection);
    }

    onCompatibleDataChange(value) {
        this.state.importCompatibleData = value;
    }

    async onExportButtonClicked() {
        if (!this.fieldsToExport.length) {
            this.notification.add(this.env._t("Please select fields to save export list..."), {
                type: "danger",
            });
            return;
        }
        const exportedFields = this.fieldsToExport.map((field) => ({
            name: field.name,
            label: field.string,
            store: field.store,
            type: field.type,
        }));
        if (this.state.importCompatibleData) {
            exportedFields.unshift({ name: "id", label: this.env._t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    context: this.props.context,
                    model: this.props.root.resModel,
                    ids: this.props.resIds,
                    fields: exportedFields,
                    domain: this.props.root.domain,
                    import_compat: this.state.importCompatibleData,
                    groupby: this.props.root.groupBy,
                }),
            },
            url: `/web/export/${this.availableFormats[this.state.selectedFormat].tag}`,
        });
    }

    async initializeData() {
        this.availableFormats = await this.rpc("/web/export/formats");
        this.fieldsAvailableAll = this.props.root.fields;
        const templates = await this.rpc("/web/dataset/call_kw", {
            args: [],
            kwargs: {
                context: this.props.context,
            },
            model: "ir.exports",
            method: "search_read",
        });
        this.templates = templates;
        this.state.fieldsToExport = Object.values(this.props.root.activeFields).map((i) => i.name);
    }

    close() {
        this.props.close();
    }
}
ExportDataDialog.components = { Dialog, CheckBox };
ExportDataDialog.template = "web.ExportDataDialog";
