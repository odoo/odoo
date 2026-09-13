// @ts-check
/** @odoo-module native */

import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/translation";
import { unique } from "@web/core/utils/collections/arrays";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useSortable } from "@web/core/utils/dnd/sortable_owl";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { useDebounced } from "@web/core/utils/timing";
import { Dialog } from "@web/ui/dialog/dialog";

const log = makeLogger("web.view.export");

class DeleteExportListDialog extends Component {
    static components = { Dialog };
    static template = "web.DeleteExportListDialog";
    static props = {
        text: String,
        close: Function,
        delete: Function,
    };
    async onDelete() {
        await this.props.delete();
        this.props.close();
    }
}

class ExportDataItem extends Component {
    static template = "web.ExportDataItem";
    static components = { ExportDataItem };
    static props = {
        exportList: { type: Object, optional: true },
        field: { type: Object, optional: true },
        filterSubfields: Function,
        isDebug: Boolean,
        isExpanded: Boolean,
        isFieldExpandable: Function,
        onAdd: Function,
        loadFields: Function,
    };

    setup() {
        this.state = useState({
            subfields: [],
        });
        onWillStart(() => {
            if (this.props.isExpanded) {
                return this.toggleItem(this.props.field.id, false);
            }
        });
    }

    /**
     * @param {string} id
     * @param {boolean} isUserToggle
     */
    async toggleItem(id, isUserToggle) {
        if (this.props.isFieldExpandable(id)) {
            if (this.expansion || this.state.subfields.length) {
                this.expansion = null;
                this.state.subfields = [];
            } else {
                const expansion = (this.expansion = {});
                try {
                    const subfields = await this.props.loadFields(id, !isUserToggle);
                    if (this.expansion !== expansion) {
                        return;
                    }
                    this.state.subfields = subfields
                        ? isUserToggle
                            ? subfields
                            : this.props.filterSubfields(subfields)
                        : [];
                } finally {
                    if (this.expansion === expansion) {
                        this.expansion = null;
                    }
                }
            }
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

export class ExportDataDialog extends Component {
    static template = "web.ExportDataDialog";
    static components = { CheckBox, Dialog, ExportDataItem };
    static props = {
        close: { type: Function },
        context: { type: Object, optional: true },
        defaultExportList: { type: Array },
        download: { type: Function },
        getExportedFields: { type: Function },
        root: { type: Object },
    };

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");
        this.searchRef = useRef("search");

        this.knownFields = {};
        this.expandedFields = {};
        this.availableFormats = [];
        this.templates = [];
        this.exportListKeepLast = new KeepLast({ rejectSuperseded: true });
        this.fetchFieldsKeepLast = new KeepLast({ rejectSuperseded: true });

        this.state = useState({
            /** @type {any[]} */
            exportList: [],
            isCompatible: false,
            isEditingTemplate: false,
            search: [],
            searchQuery: "",
            selectedFormat: 0,
            templateId: null,
            isSmall: this.env.isSmall,
            disabled: false,
        });

        this.newTemplateText = _t("New template");
        this.removeFieldText = _t("Remove field");

        this.debouncedOnResize = useDebounced(this.updateSize, 300);

        useSortable({
            ref: this.draggableRef,
            elements: ".o_export_field",
            enable: () => !this.state.isSmall,
            cursor: "grabbing",
            onDrop: async ({ element, previous, next }) => {
                const indexes = [element, previous, next].map(
                    (e) =>
                        e &&
                        Object.values(this.state.exportList).findIndex(
                            ({ id }) => id === e.dataset.field_id,
                        ),
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
            const [availableFormats, templates] = await Promise.all([
                rpc("/web/export/formats"),
                this.orm.searchRead(
                    "ir.exports",
                    [["resource", "=", this.props.root.resModel]],
                    [],
                    {
                        context: this.props.context,
                    },
                ),
                this.fetchFields(),
            ]);
            this.availableFormats = availableFormats;
            this.templates = templates;
        });

        onMounted(() => {
            browser.addEventListener("resize", this.debouncedOnResize);
            this.updateSize();
        });

        onWillUnmount(() =>
            browser.removeEventListener("resize", this.debouncedOnResize),
        );
    }

    /** @returns {boolean} */
    get isSearching() {
        return Boolean(this.state.searchQuery);
    }

    /** @returns {Array<Object>} */
    get fieldsAvailable() {
        if (this.isSearching) {
            return this.state.search;
        }
        return Object.values(this.knownFields);
    }

    get isDebug() {
        return Boolean(odoo.debug);
    }

    /** @returns {Array<Object>} */
    get rootFields() {
        if (this.isSearching) {
            const rootFromSearchResults = this.fieldsAvailable.map((f) => {
                if (f.parent) {
                    const parentEl = this.knownFields[f.parent.id];
                    return this.knownFields[
                        parentEl.parent ? parentEl.parent.id : parentEl.id
                    ];
                }
                return this.knownFields[f.id];
            });
            return unique(rootFromSearchResults);
        }
        return this.fieldsAvailable.filter(({ parent }) => !parent);
    }

    /**
     * @param {Array<Object>} subfields
     * @returns {Array<Object>}
     */
    filterSubfields(subfields) {
        let subfieldsFromSearchResults = [];
        const fieldsAvailable = this.fieldsAvailable;
        if (this.isSearching) {
            subfieldsFromSearchResults = fieldsAvailable
                .filter((f) => f.parent && this.knownFields[f.parent.id].parent)
                .map((f) => f.parent);
        }
        const availableSubFields = unique([
            ...fieldsAvailable,
            ...subfieldsFromSearchResults,
        ]);
        return subfields.filter((a) => availableSubFields.some((b) => a.id === b.id));
    }

    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }

    async fetchFields() {
        this.fieldsGeneration = (this.fieldsGeneration ?? 0) + 1;
        const isCompatible = this.state.isCompatible;
        const pending = { knownFields: {}, expandedFields: {} };
        try {
            await this.fetchFieldsKeepLast.add(
                this.loadFields(undefined, false, pending),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            throw error;
        }
        if (isCompatible !== this.state.isCompatible) {
            return;
        }
        this.knownFields = pending.knownFields;
        this.expandedFields = pending.expandedFields;
        this.state.search = [];
        this.state.searchQuery = "";
        if (this.searchRef.el) {
            /** @type {HTMLInputElement} */ (this.searchRef.el).value = "";
        }
        log.logic("fields published", () => ({
            isCompatible,
            fields: Object.keys(this.knownFields).length,
        }));
        await this.setDefaultExportList();
        if (this.state.templateId) {
            this.loadExportList(this.state.templateId);
        }
    }

    enterTemplateEdition() {
        if (this.state.templateId && !this.state.isEditingTemplate) {
            this.state.isEditingTemplate = true;
        }
    }

    /**
     * @param {string} id
     * @returns {boolean}
     */
    isFieldExpandable(id) {
        const field = this.knownFields[id];
        if (!field) {
            // A retiring tree item can render after its field cache was replaced.
            log.logic("field no longer available", () => ({ id }));
            return false;
        }
        return field.children && id.split("/").length < 3;
    }

    /** @param {string | number} value */
    async loadExportList(value) {
        this.state.templateId = value === "new_template" ? value : Number(value);
        this.state.isEditingTemplate = value === "new_template";
        if (!value || value === "new_template") {
            this.exportListKeepLast.cancel();
            return;
        }
        let fields;
        try {
            fields = await this.exportListKeepLast.add(
                rpc("/web/export/namelist", {
                    model: this.props.root.resModel,
                    export_id: Number(value),
                }),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            throw error;
        }
        this.state.exportList = fields;
    }

    /**
     * @param {string} [id]
     * @param {boolean} [preventLoad=false]
     * @param {{ knownFields: Object, expandedFields: Object }} [target]
     * @returns {Promise<Array<Object> | undefined>}
     */
    async loadFields(id, preventLoad = false, target) {
        const knownFields = target?.knownFields ?? this.knownFields;
        const expandedFields = target?.expandedFields ?? this.expandedFields;
        const generation = this.fieldsGeneration;
        let parentField, parentParams;
        if (id) {
            if (expandedFields[id]) {
                return expandedFields[id].fields;
            }
            parentField = knownFields[id];
            parentParams = {
                ...parentField.params,
                parent_field_type: parentField.field_type,
                parent_field: parentField,
                parent_name: parentField.string,
                exclude: [parentField.relation_field],
            };
        }
        if (preventLoad) {
            return;
        }
        const isCompatible = this.state.isCompatible;
        const fields = await this.props.getExportedFields(isCompatible, parentParams);
        if (
            isCompatible !== this.state.isCompatible ||
            generation !== this.fieldsGeneration ||
            (!target &&
                (knownFields !== this.knownFields ||
                    expandedFields !== this.expandedFields))
        ) {
            return;
        }
        for (const field of fields) {
            field.parent = parentField;
            if (!knownFields[field.id]) {
                knownFields[field.id] = field;
            }
        }
        if (id) {
            expandedFields[id] = { fields };
        }
        return fields;
    }

    /**
     * @param {number} item
     * @param {number} target
     */
    onDraggingEnd(item, target) {
        this.state.exportList.splice(
            target,
            0,
            this.state.exportList.splice(item, 1)[0],
        );
        this.enterTemplateEdition();
    }

    /** @param {string} fieldId */
    onAddItemExportList(fieldId) {
        this.state.exportList.push(this.knownFields[fieldId]);
        this.enterTemplateEdition();
    }

    /** @param {string} fieldId */
    onRemoveItemExportList(fieldId) {
        const item = this.state.exportList.findIndex(({ id }) => id === fieldId);
        this.state.exportList.splice(item, 1);
        this.enterTemplateEdition();
    }

    async onChangeExportList(ev) {
        this.loadExportList(ev.target.value);
    }

    async onSaveExportTemplate() {
        const name = /** @type {HTMLInputElement} */ (this.exportListRef.el).value;
        if (!name) {
            return this.notification.add(_t("Please enter save field list name"), {
                type: "danger",
            });
        }
        const [id] = await this.orm.create(
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
            { context: this.props.context },
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
                _t("Please select fields to save export list..."),
                {
                    type: "danger",
                },
            );
        }
        this.state.disabled = true;
        try {
            await this.props.download(
                this.state.exportList,
                this.state.isCompatible,
                this.availableFormats[this.state.selectedFormat].tag,
            );
        } finally {
            this.state.disabled = false;
        }
    }

    async onDeleteExportTemplate() {
        this.dialog.add(DeleteExportListDialog, {
            text: _t("Do you really want to delete this export template?"),
            delete: async () => {
                const id = Number(this.state.templateId);
                await this.orm.unlink("ir.exports", [id], {
                    context: this.props.context,
                });
                const index = this.templates.findIndex((i) => i.id === id);
                if (index !== -1) {
                    this.templates.splice(index, 1);
                }
                this.state.templateId = null;
                this.setDefaultExportList();
            },
        });
    }

    onSearch(ev) {
        this.state.searchQuery = ev.target.value;
        this.state.search = this.lookup(this.state.searchQuery);
        log.logic("search updated", () => ({
            queryLength: this.state.searchQuery.length,
            matches: this.state.search.length,
        }));
    }

    /**
     * @param {string} value
     * @returns {Array<Object>}
     */
    lookup(value) {
        let lookupResult = fuzzyLookup(
            value,
            Object.values(this.knownFields),
            (field) => field.string.split("/").reverse().join("/"),
        );
        if (this.isDebug) {
            lookupResult = unique([
                ...lookupResult,
                ...Object.values(this.knownFields).filter((f) => f.id.includes(value)),
            ]);
        }
        return lookupResult;
    }

    async onToggleCompatibleExport(value) {
        this.state.isCompatible = value;
        await this.fetchFields();
    }

    async setDefaultExportList() {
        const defaultExportList = this.props.defaultExportList
            .map((defaultField) => this.knownFields[defaultField.name])
            .filter((field) => field);

        const defaultExportfields = Object.values(this.knownFields).filter(
            (field) => field.default_export,
        );

        this.state.exportList = unique([...defaultExportList, ...defaultExportfields]);
    }

    setFormat(ev) {
        if (ev.target.checked) {
            this.state.selectedFormat = this.availableFormats.findIndex(
                ({ tag }) => tag === ev.target.value,
            );
        }
    }
}
