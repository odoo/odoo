/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { useSortable } from "@web/core/utils/ui";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { download } from "@web/core/network/download";
import { fuzzyLookup } from "@web/core/utils/search";

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
        return this.props.field.parent.string.concat("/", path.pop());
    }

    async onClick(ev) {
        this.state.subFields = await this.props.onClick(ev);
        this.state.isExpanded = this.props.isFieldExpanded(this.props.field.name);
    }

    isFieldSelected(name) {
        return this.props.fieldsToExport.includes(name);
    }
}
ExportDataItem.template = "web.ExportDataItem";
ExportDataItem.components = { ExportDataItem };
ExportDataItem.props = {
    field: { type: Object, optional: true },
    fieldsToExport: { type: Object, optional: true },
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
            importCompatibleData: false,
            templateSelection: null,
            fieldsToExport: [],
            templateisEditing: false,
            search: [],
        });

        this.title = this.env._t("Export Data");
        this.newTemplateText = this.env._t("New template");
        this.removeFieldText = this.env._t("Remove field");
        this.expandText = this.env._t("Show sub-fields");

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

    /**
     * Returns the current available fields for the user
     * It depends the current fields selected for export
     */
    get fieldsAvailable() {
        const available = this.state.search.length ? this.state.search : this.fieldsAvailableAll;
        return Object.values(available);
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

    expandedContent(id) {
        return this.isFieldExpanded(id) && this.state.expandedFields[id].content;
    }

    isFieldExpanded(id) {
        return this.state.expandedFields[id] && !this.state.expandedFields[id].hidden;
    }

    isFieldExpandable(field) {
        return ["one2many", "many2one"].includes(field.type);
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
        const field = ev.target.closest(".o_export_tree_item").dataset.field_id;
        this.state.fieldsToExport.push(field);
        this.state.search = [];
        this.searchRef.el.value = "";
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

    async onCompatibleDataChange(value) {
        this.state.importCompatibleData = value;
        await this.fetchFields();
    }

    async onSearch(ev) {
        this.state.search = fuzzyLookup(ev.target.value, this.fieldsAvailable, (c) => c.name);
    }

    async loadFields(id) {
        let model = this.props.root.resModel;
        let parentField, parentParams;
        if (id) {
            if (this.state.expandedFields[id]) {
                // we don't make a new RPC if the value is already known
                this.state.expandedFields[id].hidden = !this.state.expandedFields[id].hidden;
                return this.state.expandedFields[id].content;
            }
            parentField = this.fieldsAvailableAll[id];
            model = parentField.params.model;
            parentParams = {
                ...parentField.params,
                parent_field_type: parentField.type,
                parent_field: parentField,
                //exclude: "excludeFields",
            };
        }
        const content = await this.rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            import_compat: this.state.importCompatibleData,
        });
        content.forEach((field) => {
            field.name = field.id.split("/").pop();
            field.parent = parentField;
            field.type = field.field_type;
        });
        if (id) {
            this.state.expandedFields[id] = { content };
        }
        return content;
    }

    async onToggleExpandField(ev) {
        const id = ev.target.closest(".o_export_tree_item").dataset.field_id;
        return await this.loadFields(id);
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

    async fetchFields() {
        const fields = await this.loadFields();
        this.fieldsAvailableAll = {};
        fields.forEach((field) => {
            this.fieldsAvailableAll[field.id] = field;
        });
        if (this.state.importCompatibleData) {
            this.state.fieldsToExport = this.state.fieldsToExport.filter(
                (i) => this.fieldsAvailableAll[i]
            );
        } else {
            this.state.fieldsToExport = Object.values(this.props.root.activeFields).map(
                (i) => i.name && this.fieldsAvailableAll[i.name] && i.name
            );
        }
        this.state.templateSelection && this.loadExportList(this.state.templateSelection);
    }
}
ExportDataDialog.components = { CheckBox, Dialog, ExportDataItem };
ExportDataDialog.template = "web.ExportDataDialog";
