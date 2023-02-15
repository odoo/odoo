/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { useSortable } from "@web/core/utils/sortable";
import { useDebounced } from "@web/core/utils/timing";

import { Component, useRef, useState, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";

class DeleteExportListDialog extends Component {
    async onDelete() {
        await this.props.delete();
        this.props.close();
    }
}
DeleteExportListDialog.components = { Dialog };
DeleteExportListDialog.template = "web.DeleteExportListDialog";

class ExportDataItem extends Component {
    setup() {
        this.subFields = [];
        this.state = useState({
            isExpanded: false,
        });
    }

    async onClick(ev) {
        if (this.props.isFieldExpandable(this.props.field)) {
            this.subFields = await this.props.onClick(ev);
            this.state.isExpanded = this.props.isFieldExpanded(this.props.field.name);
        }
    }

    isFieldSelected(current) {
        return this.props.exportList.find(({ name }) => name === current);
    }
}
ExportDataItem.template = "web.ExportDataItem";
ExportDataItem.components = { ExportDataItem };
ExportDataItem.props = {
    field: { type: Object, optional: true },
    exportList: { type: Object, optional: true },
    expandedContent: Function,
    isDebug: Boolean,
    isFieldExpandable: Function,
    isFieldExpanded: Function,
    onClick: Function,
    onAdd: Function,
};

export class ExportDataDialog extends Component {
    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");
        this.searchRef = useRef("search");

        this.knownFields = {};
        this.expandedFields = {};
        this.availableFormats = [];
        this.templates = [];

        this.state = useState({
            exportList: [],
            isCompatible: false,
            isEditingTemplate: false,
            search: [],
            selectedFormat: 0,
            templateId: null,
            isSmall: this.env.isSmall,
        });

        this.title = this.env._t("Export Data");
        this.newTemplateText = this.env._t("New template");
        this.removeFieldText = this.env._t("Remove field");

        this.debouncedOnResize = useDebounced(this.updateSize, 300);

        useSortable({
            // Params
            ref: this.draggableRef,
            elements: ".o_export_field",
            enable: !this.state.isSmall,
            cursor: "grabbing",
            // Hooks
            onDrop: async ({ element, previous, next }) => {
                const indexes = [element, previous, next].map(
                    (e) =>
                        e &&
                        Object.values(this.state.exportList).findIndex(
                            ({ name }) => name === e.dataset.field_id
                        )
                );
                let target;
                if (indexes[0] < indexes[1]) {
                    target = previous ? indexes[1] : 0;
                } else {
                    target = next ? indexes[2] : this.state.exportList.length - 1;
                }
                this.onDraggingEnd([indexes[0], target]);
            },
        });

        onWillStart(async () => {
            this.availableFormats = await this.rpc("/web/export/formats");
            this.templates = await this.orm.searchRead(
                "ir.exports",
                [["resource", "=", this.props.root.resModel]],
                [],
                {
                    context: this.props.context,
                }
            );
            await this.fetchFields();
        });

        onMounted(() => {
            browser.addEventListener("resize", this.debouncedOnResize);
            this.updateSize();
        });

        onWillUnmount(() => browser.removeEventListener("resize", this.debouncedOnResize));
    }

    get fieldsAvailable() {
        if (this.searchRef.el && this.searchRef.el.value) {
            return this.state.search.length && Object.values(this.state.search);
        }
        return Object.values(this.knownFields);
    }

    get isDebug() {
        return Boolean(odoo.debug);
    }

    get rootFields() {
        return this.fieldsAvailable.filter(({ parent }) => !parent);
    }

    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }

    /**
     * Load fields to display and (re)set the list of available fields
     */
    async fetchFields() {
        this.state.search = [];
        this.knownFields = {};
        await this.loadFields();
        this.setDefaultExportList();
        if (this.searchRef.el) {
            this.searchRef.el.value = "";
        }
        if (this.state.templateId) {
            this.loadExportList(this.state.templateId);
        }
    }

    enterTemplateEdition() {
        if (this.state.templateId && !this.state.isEditingTemplate) {
            this.state.isEditingTemplate = true;
        }
    }

    expandedContent(id) {
        return this.isFieldExpanded(id) && this.expandedFields[id].fields;
    }

    isFieldExpanded(id) {
        return this.expandedFields[id] && !this.expandedFields[id].hidden;
    }

    isFieldExpandable({ name }) {
        return this.knownFields[name].children && name.split("/").length < 3;
    }

    async loadExportList(value) {
        this.state.templateId = value === "new_template" ? value : Number(value);
        this.state.isEditingTemplate = value === "new_template";
        if (!value || value === "new_template") {
            return;
        }
        const fields = await this.rpc("/web/export/namelist", {
            model: this.props.root.resModel,
            export_id: Number(value),
        });
        this.state.exportList = fields;
    }

    async loadFields(id) {
        let model = this.props.root.resModel;
        let parentField, parentParams;
        if (id) {
            if (this.expandedFields[id]) {
                // we don't make a new RPC if the value is already known
                this.expandedFields[id].hidden = !this.expandedFields[id].hidden;
                return this.expandedFields[id].fields;
            }
            parentField = this.knownFields[id];
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
            this.state.isCompatible,
            parentParams
        );
        for (const field of fields) {
            field.name = field.id;
            field.label = field.string;
            field.parent = parentField;
            if (!this.knownFields[field.id]) {
                this.knownFields[field.id] = field;
            }
        }
        if (id) {
            this.expandedFields[id] = { fields };
        }
        return fields;
    }

    onDraggingEnd([item, target]) {
        this.state.exportList.splice(target, 0, this.state.exportList.splice(item, 1)[0]);
    }

    onAddItemExportList(ev) {
        const field = ev.target.closest(".o_export_tree_item").dataset.field_id;
        this.state.exportList.push(this.knownFields[field]);
        this.state.search = [];
        this.searchRef.el.value = "";
        this.enterTemplateEdition();
    }

    onRemoveItemExportList(ev) {
        const item = this.state.exportList.findIndex(
            ({ name }) => name === ev.target.parentElement.dataset.field_id
        );
        this.state.exportList.splice(item, 1);
        this.enterTemplateEdition();
    }

    async onChangeExportList(ev) {
        this.loadExportList(ev.target.value);
    }

    async onSaveExportTemplate() {
        const name = this.exportListRef.el.value;
        if (!name) {
            return this.notification.add(this.env._t("Please enter save field list name"), {
                type: "danger",
            });
        }
        const id = await this.orm.create(
            "ir.exports",
            [
                {
                    name,
                    export_fields: this.state.exportList.map((field) => [
                        0,
                        0,
                        {
                            name: field.name,
                        },
                    ]),
                    resource: this.props.root.resModel,
                },
            ],
            { context: this.props.context }
        );
        this.state.isEditingTemplate = false;
        this.state.templateId = id;
        this.templates.push({ id, name });
    }

    onCancelExportTemplate() {
        this.state.isEditingTemplate = false;
        if (this.state.templateId === "new_template") {
            this.state.templateId = null;
            return;
        }
        this.loadExportList(this.state.templateId);
    }

    async onClickExportButton() {
        if (!this.state.exportList.length) {
            return this.notification.add(
                this.env._t("Please select fields to save export list..."),
                {
                    type: "danger",
                }
            );
        }
        await this.props.download(
            this.state.exportList,
            this.state.isCompatible,
            this.availableFormats[this.state.selectedFormat].tag
        );
    }

    async onDeleteExportTemplate() {
        this.dialog.add(DeleteExportListDialog, {
            text: this.env._t("Do you really want to delete this export template?"),
            delete: async () => {
                const id = Number(this.state.templateId);
                await this.orm.unlink("ir.exports", [id], { context: this.props.context });
                this.templates.splice(
                    this.templates.findIndex((i) => i.id === id),
                    1
                );
                this.state.templateId = null;
                this.setDefaultExportList();
            },
        });
    }

    async onSearch(ev) {
        this.state.search = fuzzyLookup(
            ev.target.value,
            this.fieldsAvailable || Object.values(this.knownFields),
            (field) => field.string
        );
    }

    async onToggleCompatibleExport(value) {
        this.state.isCompatible = value;
        await this.fetchFields();
    }

    async onToggleExpandField(ev) {
        const id = ev.target.closest(".o_export_tree_item").dataset.field_id;
        const fields = await this.loadFields(id);
        return fields;
    }

    setDefaultExportList() {
        if (this.state.isCompatible) {
            this.state.exportList = this.state.exportList.filter(
                ({ name }) => this.knownFields[name]
            );
        } else {
            this.state.exportList = this.props.defaultExportList;
        }
    }

    setFormat(ev) {
        if (ev.target.checked) {
            this.state.selectedFormat = this.availableFormats.findIndex(
                ({ tag }) => tag === ev.target.value
            );
        }
    }
}
ExportDataDialog.components = { CheckBox, Dialog, ExportDataItem };
ExportDataDialog.props = {
    close: { type: Function },
    context: { type: Object, optional: true },
    defaultExportList: { type: Array },
    download: { type: Function },
    getExportedFields: { type: Function },
    root: { type: Object },
};
ExportDataDialog.template = "web.ExportDataDialog";
