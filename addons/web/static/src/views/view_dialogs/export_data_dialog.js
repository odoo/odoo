/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { unique } from "@web/core/utils/arrays";
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
        this.state = useState({
            isExpanded: this.subFields.length > 0 && this.props.isExpanded,
        });
    }

    get subFields() {
        return this.props.getSubFields(this.props.field.id);
    }

    async loadExpandedContent(id) {
        if (this.props.isFieldExpandable(id)) {
            await this.props.onToggleExpandField(id);
            this.state.isExpanded = !this.state.isExpanded;
        }
    }

    onDoubleClick(id) {
        if (!this.props.isFieldExpandable(id) && !this.isFieldSelected(id)) {
            this.props.onAdd(id);
        }
    }

    isFieldSelected(current) {
        return this.props.exportList.find(({ id }) => id === current);
    }
}
ExportDataItem.template = "web.ExportDataItem";
ExportDataItem.components = { ExportDataItem };
ExportDataItem.props = {
    exportList: { type: Object, optional: true },
    field: { type: Object, optional: true },
    getSubFields: Function,
    isDebug: Boolean,
    isExpanded: Boolean,
    isFieldExpandable: Function,
    onAdd: Function,
    onToggleExpandField: Function,
    search: Array,
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
                            ({ id }) => id === e.dataset.field_id
                        )
                );
                let target;
                if (indexes[0] < indexes[1]) {
                    target = previous ? indexes[1] : 0;
                } else {
                    target = next ? indexes[2] : this.state.exportList.length - 1;
                }
                this.onDraggingEnd(indexes[0], target);
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
        if (this.searchRef.el && this.searchRef.el.value) {
            const rootFromSearchResults = this.fieldsAvailable.map((f) => {
                if (f.parent) {
                    const parentEl = this.knownFields[f.parent.id];
                    return this.knownFields[parentEl.parent ? parentEl.parent.id : parentEl.id];
                }
                return this.knownFields[f.id];
            });
            return unique(rootFromSearchResults);
        }
        return this.fieldsAvailable.filter(({ parent }) => !parent);
    }

    getSubFields(id) {
        let subfieldsFromSearchResults = [];
        const fieldsAvailable = this.fieldsAvailable;
        const expandedFields = (this.expandedFields[id] && this.expandedFields[id].fields) || [];
        if (this.searchRef.el && this.searchRef.el.value) {
            subfieldsFromSearchResults = fieldsAvailable
                .filter((f) => f.parent && this.knownFields[f.parent.id].parent)
                .map((f) => f.parent);
        }
        const availableSubFields = unique([...fieldsAvailable, ...subfieldsFromSearchResults]);
        return expandedFields.filter((a) => availableSubFields.some((b) => a.id === b.id));
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
        await this.setDefaultExportList();
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

    isFieldExpandable(id) {
        return this.knownFields[id].children && id.split("/").length < 3;
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
        this.state.exportList = fields.map(({ label, name }) => {
            return {
                string: label,
                id: name,
            };
        });
    }

    async loadFields(id) {
        let model = this.props.root.resModel;
        let parentField, parentParams;
        if (id) {
            if (this.expandedFields[id]) {
                // we don't make a new RPC if the value is already known
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

    onDraggingEnd(item, target) {
        this.state.exportList.splice(target, 0, this.state.exportList.splice(item, 1)[0]);
    }

    onAddItemExportList(fieldId) {
        this.state.exportList.push(this.knownFields[fieldId]);
        this.enterTemplateEdition();
    }

    onRemoveItemExportList(fieldId) {
        const item = this.state.exportList.findIndex(({ id }) => id === fieldId);
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
                            name: field.id,
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
            Object.values(this.knownFields),
            // because fuzzyLookup gives an higher score if the string starts with the pattern,
            // reversing the string makes the search more reliable in this context
            (field) => field.id.split("/").reverse().join("/")
        );
        if (this.isDebug) {
            this.state.search = unique([
                ...this.state.search,
                ...Object.values(this.knownFields).filter((f) => {
                    return f.id.includes(ev.target.value);
                }),
            ]);
        }
    }

    onToggleCompatibleExport(value) {
        this.state.isCompatible = value;
        this.fetchFields();
    }

    onToggleExpandField(id) {
        return this.loadFields(id);
    }

    async setDefaultExportList() {
        this.state.exportList = Object.values(this.knownFields).filter(
            (e) => e.default_export || this.props.defaultExportList.find((i) => i.name === e.id)
        );
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
