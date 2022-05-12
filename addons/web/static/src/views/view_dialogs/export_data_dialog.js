/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { useSortable } from "@web/core/utils/ui";

const { Component, useRef, useState, onMounted } = owl;

class ExportDataItem extends Component {
    setup() {
        this.state = useState({
            isExpanded: false,
            subFields: [],
        });
    }

    get formattedName() {
        if (!this.props.field.parent) return this.props.field.string;
        const path = this.props.field.string.split("/");
        const start = this.props.field.parent.parent ? "…/" : "";
        return start + this.props.field.parent.string.concat("/", path.pop());
    }

    async onClick(ev) {
        this.state.subFields = await this.props.onClick(ev);
        this.state.isExpanded = this.props.isFieldExpanded(this.props.field.name);
    }

    isFieldSelected(name) {
        return this.props.exportedFields.includes(name);
    }
}
ExportDataItem.template = "web.ExportDataItem";
ExportDataItem.components = { ExportDataItem };
ExportDataItem.props = {
    field: { type: Object, optional: true },
    exportedFields: { type: Object, optional: true },
    expandedContent: Function,
    isFieldExpanded: Function,
    isFieldExpandable: Function,
    onClick: Function,
    onAdd: Function,
};

export class ExportDataDialog extends Component {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");
        this.searchRef = useRef("search");

        this.fieldsAvailableAll = {};
        this.availableFormats = [];
        this.templates = [];

        this.state = useState({
            expandedFields: {},
            selectedFormat: 0,
            compatible: false,
            templateId: null,
            exportedFields: [],
            templateisEditing: false,
            search: [],
        });

        this.title = this.env._t("Export Data");
        this.newTemplateText = this.env._t("New template");
        this.removeFieldText = this.env._t("Remove field");
        this.expandText = this.env._t("Show sub-fields");

        useSortable({
            // Params
            ref: this.draggableRef,
            elements: ".o_export_field",
            cursor: "grabbing",
            // Hooks
            onDrop: async ({ item, previous, next }) => {
                const indexes = [item, previous, next].map(
                    (e) => e && this.state.exportedFields.indexOf(e.dataset.field_id)
                );
                let target;
                if (indexes[0] < indexes[1]) {
                    target = previous ? indexes[1] : 0;
                } else {
                    target = next ? indexes[2] : this.state.exportedFields.length - 1;
                }
                this.onDraggingEnd([indexes[0], target]);
            },
        });

        onMounted(async () => {
            this.availableFormats = await this.rpc("/web/export/formats");
            this.templates = await this.rpc("/web/dataset/call_kw", {
                args: [],
                kwargs: {
                    context: this.props.context,
                },
                model: "ir.exports",
                method: "search_read",
            });
            await this.fetchFields();
        });
    }

    get fieldsAvailable() {
        if (this.searchRef.el && this.searchRef.el.value) {
            return this.state.search.length && Object.values(this.state.search);
        }
        return Object.values(this.fieldsAvailableAll);
    }

    get rootFields() {
        return this.fieldsAvailable.filter((i) => !i.parent);
    }

    /**
     * Returns the currently selected fields to export
     */
    get exportList() {
        const fields = this.state.exportedFields.map((id) => this.fieldsAvailableAll[id]);
        return fields.sort((a, b) =>
            this.state.exportedFields.indexOf(a.id) < this.state.exportedFields.indexOf(b.id)
                ? -1
                : 1
        );
    }

    handleTemplateEdition() {
        if (this.state.templateId && !this.state.templateisEditing) {
            this.state.templateisEditing = true;
        }
    }

    expandedContent(id) {
        return this.isFieldExpanded(id) && this.state.expandedFields[id].fields;
    }

    isFieldExpanded(id) {
        return this.state.expandedFields[id] && !this.state.expandedFields[id].hidden;
    }

    isFieldExpandable(field) {
        return ["one2many", "many2one"].includes(field.field_type);
    }

    async loadExportList(value) {
        this.state.templateId = value;
        if (value === "new_template") {
            return (this.state.templateisEditing = true);
        }
        this.state.templateisEditing = false;
        const fields = await this.rpc("/web/export/namelist", {
            model: this.props.root.resModel,
            export_id: Number(value),
        });
        this.state.exportedFields = fields.map((field) => field.name);
    }

    onDraggingEnd([item, target]) {
        this.state.exportedFields.splice(target, 0, this.state.exportedFields.splice(item, 1)[0]);
    }

    onAddItemExportList(ev) {
        const field = ev.target.closest(".o_export_tree_item").dataset.field_id;
        this.state.exportedFields.push(field);
        this.state.search = [];
        this.searchRef.el.value = "";
        this.handleTemplateEdition();
    }

    onRemoveItemExportList(ev) {
        const item = this.state.exportedFields.indexOf(ev.target.parentElement.dataset.field_id);
        this.state.exportedFields.splice(item, 1);
        this.handleTemplateEdition();
    }

    async onChangeExportList(ev) {
        this.loadExportList(ev.target.value);
    }

    async onSaveExportListEdition() {
        const name = this.exportListRef.el.value;
        if (!name) {
            return this.notification.add(this.env._t("Please enter save field list name"), {
                type: "danger",
            });
        }

        const exportList = this.exportList.map((field) => [
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
                    export_fields: exportList,
                    resource: this.props.root.resModel,
                },
            ],
            kwargs: {
                context: this.props.context,
            },
            model: "ir.exports",
            method: "create",
        });

        this.state.templateId = id;
        this.templates.push({ id, name });
    }

    onClearExportListEdition() {
        if (this.state.templateId === "new_template") {
            return (this.state.templateId = null);
        }
        this.loadExportList(this.state.templateId);
    }

    async onCompatibleDataChange(value) {
        this.state.compatible = value;
        await this.fetchFields();
    }

    async onSearch(ev) {
        this.state.search = fuzzyLookup(
            ev.target.value,
            this.fieldsAvailable || Object.values(this.fieldsAvailableAll),
            (field) => field.string
        );
    }

    async loadFields(id) {
        let model = this.props.root.resModel;
        let parentField, parentParams;
        if (id) {
            if (this.state.expandedFields[id]) {
                // we don't make a new RPC if the value is already known
                this.state.expandedFields[id].hidden = !this.state.expandedFields[id].hidden;
                return this.state.expandedFields[id].fields;
            }
            parentField = this.fieldsAvailableAll[id];
            model = parentField.params && parentField.params.model;
            parentParams = {
                ...parentField.params,
                parent_field_type: parentField.field_type,
                parent_field: parentField,
                parent_name: parentField.string,
                exclude: [parentField.relation_field],
            };
        }
        const fields = await this.props.getExportedFields(
            model,
            this.state.compatible,
            parentParams
        );
        fields.forEach((field) => {
            field.name = parentField
                ? parentField.name + "/" + field.id.split("/").pop()
                : field.id;
            field.parent = parentField;
        });
        if (id) {
            this.state.expandedFields[id] = { fields };
        }
        return fields;
    }

    async onToggleExpandField(ev) {
        const id = ev.target.closest(".o_export_tree_item").dataset.field_id;
        const fields = await this.loadFields(id);
        fields.forEach((field) => {
            this.fieldsAvailableAll[field.name] = field;
        });
        return fields;
    }

    async onExportButtonClicked() {
        if (!this.exportList.length) {
            return this.notification.add(
                this.env._t("Please select fields to save export list..."),
                {
                    type: "danger",
                }
            );
        }
        await this.props.download(
            this.exportList,
            this.state.compatible,
            this.availableFormats[this.state.selectedFormat].tag
        );
    }

    async fetchFields() {
        this.state.search = [];
        this.searchRef.el.value = "";
        const fields = await this.loadFields();
        this.fieldsAvailableAll = {};
        fields.forEach((field) => {
            this.fieldsAvailableAll[field.name] = field;
        });
        if (this.state.compatible) {
            this.state.exportedFields = this.state.exportedFields.filter(
                (i) => this.fieldsAvailableAll[i]
            );
        } else {
            this.state.exportedFields = Object.values(this.props.root.activeFields).map(
                (i) => i.name && this.fieldsAvailableAll[i.name] && i.name
            );
        }
        this.state.templateId && this.loadExportList(this.state.templateId);
    }
}
ExportDataDialog.components = { CheckBox, Dialog, ExportDataItem };
ExportDataDialog.template = "web.ExportDataDialog";
