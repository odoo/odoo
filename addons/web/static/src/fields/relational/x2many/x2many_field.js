// @ts-check
/** @odoo-module native */

import { Pager } from "@web/components/pager/pager";
import { useAction } from "@web/core/action_port";
import { makeContext } from "@web/core/context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { sharedComponents as shared } from "@web/core/shared_components";
import { _t } from "@web/core/translation";
import { shallowEqual } from "@web/core/utils/collections/objects";
import { useService } from "@web/core/utils/hooks";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { archAttribute } from "@web/fields/field_options";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { getFieldDomain } from "@web/model/relational_model";

import { useSelectCreate } from "../many2x_autocomplete.js";
import { useActiveActions } from "../relational_active_actions.js";
import { useAddInlineRecord, useX2ManyCrud } from "../x2many_crud.js";
import { useOpenX2ManyRecord } from "../x2many_dialog.js";

const views = registry.category("views");

const log = makeLogger("web.field.x2many");

export class X2ManyField extends FieldComponent {
    static template = "web.X2ManyField";
    static get components() {
        return {
            Pager,
            KanbanRenderer: views.contains("kanban")
                ? views.get("kanban").Renderer
                : undefined,
            ListRenderer: views.contains("list")
                ? views.get("list").Renderer
                : undefined,
            ViewButton: shared.contains("ViewButton")
                ? shared.get("ViewButton")
                : undefined,
        };
    }
    static props = {
        ...standardFieldProps,
        addLabel: { type: String, optional: true },
        editable: { type: String, optional: true },
        viewMode: { type: String, optional: true },
        widget: { type: String, optional: true },
        crudOptions: { type: Object, optional: true },
        string: { type: String, optional: true },
        relatedFields: { type: Object, optional: true },
        views: { type: Object, optional: true },
        domain: { type: [Array, Function], optional: true },
        context: { type: Object },
    };

    /** @type {any} */
    _openRecord;
    /** @type {any} */
    selectCreate;
    /** @type {any} */
    addInLine;
    /** @type {any} */
    activeActions;
    /** @type {import("@web/core/action_port").ActionPort} */
    action;
    /** @type {import("services").ServiceFactories["notification"]} */
    notificationService;

    /** @type {Record<string, any>} */
    fieldDefinition;

    /**
     * @type {{
     * openRecord: (record: any) => any,
     * onAdd: (params: any) => any,
     * onListAdd: (params: any) => any,
     * onOpenFormView: (record: any, options: any) => any,
     * deleteRecord: (record: any) => any,
     * }}
     */
    rendererCallbacks;

    /** @type {{ source: Record<string, any> | null, recordsDraggable: boolean | undefined, archInfo: Record<string, any> | null }} */
    _kanbanArchInfoMemo = { source: null, recordsDraggable: undefined, archInfo: null };

    /** @type {{ field: string, model: string, viewMode: string } | null} */
    _nestedKeyOptionalFieldsData = null;

    /** @type {Record<string, any> | null} */
    _rendererActiveActions = null;

    setup() {
        this.fieldDefinition = this.field.definition;
        this.rendererCallbacks = {
            openRecord: (record) => this.openRecord(record),
            onAdd: (params) => this.onAdd(params),
            onListAdd: (params) => {
                params.editable =
                    !this.props.readonly &&
                    ("editable" in params ? params.editable : this.listEditable);
                return this.onAdd(params);
            },
            onOpenFormView: (record, options) => this.switchToForm(record, options),
            deleteRecord: (record) => crud.removeRecord(record),
        };
        const crud = useX2ManyCrud(() => this.list, this.isMany2Many);

        this.setupSubView();
        this.activeActions = useActiveActions({
            crudOptions: (props) => ({
                ...props.crudOptions,
                onDelete: crud.removeRecord,
            }),
            fieldType: this.isMany2Many ? "many2many" : "one2many",
            subViewActiveActions: this.archInfo.activeActions,
            getEvalParams: (props) => ({
                evalContext: props.record.evalContext,
                readonly: props.readonly,
                edit: props.record.isInEdition,
            }),
        });
        this.addInLine = useAddInlineRecord({
            addNew: (params) => this.list.addNewRecord(params),
        });
        this.setupRecordOpeners(crud);

        this.action = useAction();
        this.notificationService = useService("notification");
    }

    setupSubView() {
        this.archInfo = this.props.viewMode
            ? this.props.views[this.props.viewMode]
            : {};
        const classes = this.props.viewMode
            ? ["o_field_x2many", `o_field_x2many_${this.props.viewMode}`]
            : ["o_field_x2many"];
        this.className = shared.get("computeViewClassName")(
            this.props.viewMode,
            this.archInfo.xmlDoc,
            classes,
        );
        if (this.props.viewMode === "kanban") {
            this.controls = this.archInfo.controls || [];
        }
    }

    /** @returns {string | undefined} */
    getOpenRecordTitle() {
        return undefined;
    }

    /** @param {{ linkRecords: Function, saveAndLink: Function, updateRecord: Function }} crud */
    setupRecordOpeners({ linkRecords, saveAndLink, updateRecord }) {
        const openRecord = useOpenX2ManyRecord({
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: saveAndLink,
            updateRecord,
            isMany2Many: this.isMany2Many,
        });
        this._openRecord = (params) => {
            const activeElement = document.activeElement;
            openRecord({
                title: this.getOpenRecordTitle(),
                ...params,
                controls: this.controls,
                onClose: () => {
                    if (activeElement?.isConnected) {
                        /** @type {HTMLElement} */ (activeElement).focus();
                    }
                },
            });
        };
        this.canOpenRecord =
            this.props.viewMode === "list"
                ? !(this.archInfo.editable || this.props.editable)
                : true;

        const selectCreate = useSelectCreate({
            resModel: this.list.resModel,
            activeActions: this.activeActions,
            isToMany: this.isMany2Many,
            onSelected: (resIds) => linkRecords?.(resIds),
            onCreateEdit: ({ context }) => this._openRecord({ context }),
            onUnselect: this.isMany2Many ? undefined : () => saveAndLink?.(),
        });
        this.selectCreate = (params) => {
            const p = { ...params };
            const currentIds = this.list.currentIds.filter(
                (id) => typeof id === "number",
            );
            p.domain = [...(p.domain || []), "!", ["id", "in", currentIds]];
            return selectCreate(p);
        };
    }

    /** @returns {{ fields: Object, views: Object, viewMode: string, string: string }} */
    get activeField() {
        return {
            fields: this.props.relatedFields,
            views: this.props.views,
            viewMode: this.props.viewMode,
            string: this.props.string,
        };
    }

    /** @returns {boolean} */
    get displayControlPanelButtons() {
        return Boolean(
            this.props.viewMode === "kanban" && this.canCreate && this.controls.length,
        );
    }

    /** @returns {boolean} */
    get canCreate() {
        return (
            ("link" in this.activeActions
                ? this.activeActions.link
                : this.activeActions.create) && !this.props.readonly
        );
    }

    /** @returns {boolean} */
    get isMany2Many() {
        return (
            this.fieldDefinition.type === "many2many" ||
            this.props.widget === "many2many"
        );
    }

    /** @returns {import("@web/model/relational_model/static_list").StaticList} */
    get list() {
        return this.field.value;
    }

    /** @returns {{ field: string, model: string, viewMode: string }} */
    get nestedKeyOptionalFieldsData() {
        const { name: field } = this.props;
        const { resModel: model } = this.props.record;
        const memo = this._nestedKeyOptionalFieldsData;
        if (memo && memo.field === field && memo.model === model) {
            return memo;
        }
        this._nestedKeyOptionalFieldsData = { field, model, viewMode: "form" };
        return this._nestedKeyOptionalFieldsData;
    }

    /** @returns {string | false | undefined} */
    get listEditable() {
        return (
            (this.archInfo.activeActions.edit && this.archInfo.editable) ||
            this.props.editable
        );
    }

    /** @returns {Record<string, any>} */
    get rendererActiveActions() {
        const memo = this._rendererActiveActions;
        if (memo && shallowEqual(memo, this.activeActions)) {
            return memo;
        }
        const actions = { ...this.activeActions };
        this._rendererActiveActions = actions;
        return actions;
    }

    /**
     * @param {boolean} recordsDraggable
     * @returns {Record<string, any>}
     */
    kanbanArchInfo(recordsDraggable) {
        const { archInfo } = this;
        const memo = this._kanbanArchInfoMemo;
        if (memo.source === archInfo && memo.recordsDraggable === recordsDraggable) {
            return /** @type {Record<string, any>} */ (memo.archInfo);
        }
        const next = { ...archInfo, recordsDraggable };
        this._kanbanArchInfoMemo = {
            source: archInfo,
            recordsDraggable,
            archInfo: next,
        };
        return next;
    }

    /** @returns {{ offset: number, limit: number, total: number, onUpdate: Function, withAccessKey: boolean }} */
    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                const initialLimit = this.list.limit;
                const leaved = await list.leaveEditMode();
                if (leaved) {
                    if (
                        initialLimit === limit &&
                        initialLimit === this.list.limit + 1
                    ) {
                        offset -= 1;
                        limit -= 1;
                    }
                    await list.load({ limit, offset });
                }
            },
            withAccessKey: false,
        };
    }

    /** @returns {typeof import("@odoo/owl").Component | undefined} */
    get kanbanRenderer() {
        const ctor = /** @type {typeof X2ManyField} */ (this.constructor);
        return (
            ctor.components.KanbanRenderer ??
            (views.contains("kanban") ? views.get("kanban").Renderer : undefined)
        );
    }

    /** @returns {Object} */
    get rendererProps() {
        const { archInfo, rendererCallbacks } = this;
        const props = {
            archInfo,
            list: this.list,
            openRecord: rendererCallbacks.openRecord,
            readonly: this.props.readonly || !this.activeActions.write,
        };

        if (this.props.viewMode === "kanban") {
            const recordsDraggable = Boolean(
                !this.props.readonly && archInfo.recordsDraggable,
            );
            props.archInfo = this.kanbanArchInfo(recordsDraggable);
            props.Compiler = views.get("kanban").Compiler;
            props.deleteRecord = rendererCallbacks.deleteRecord;
            if (this.canCreate && !this.controls.length) {
                props.addLabel =
                    this.props.addLabel || _t("Add %s", this.fieldDefinition.string);
                props.onAdd = rendererCallbacks.onAdd;
            }
            return props;
        }

        props.activeActions = this.rendererActiveActions;
        props.cycleOnTab = false;
        props.editable = !this.props.readonly && this.listEditable;
        props.nestedKeyOptionalFieldsData = this.nestedKeyOptionalFieldsData;
        props.onAdd = rendererCallbacks.onListAdd;
        props.onOpenFormView = rendererCallbacks.onOpenFormView;
        props.hasOpenFormViewButton = Boolean(
            archInfo.editable ? archInfo.openFormView : false,
        );
        return props;
    }

    /**
     * @param {string} invisible
     * @returns {boolean}
     */
    evalInvisible(invisible) {
        return evaluateBooleanExpr(invisible, this.list.evalContext);
    }

    /**
     * @param {Object} record
     * @param {{ newWindow?: boolean }} [options]
     */
    async switchToForm(record, { newWindow = false } = {}) {
        log.logic("switchToForm", () => ({
            name: this.props.name,
            resId: record.resId,
            isNew: record.isNew,
            newWindow,
        }));
        let resId;
        if (record.isNew) {
            const reconciliation = this.list.snapshotCreateReconciliation();
            const saved = await this.props.record.save();
            if (!saved) {
                return;
            }
            if (record.resId) {
                resId = record.resId;
            } else {
                resId = this.list.resolveCreatedResId(reconciliation, record);
                if (resId === undefined) {
                    return this.notificationService.add(
                        _t("Please save your changes first"),
                        {
                            type: "danger",
                        },
                    );
                }
            }
        } else {
            const saved = await this.props.record.save();
            if (!saved) {
                return;
            }
            resId = record.resId;
        }

        this.action.doAction(
            {
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                res_id: resId,
                res_model: this.list.resModel,
                context: this.getFormActionContext(),
            },
            {
                props: { resIds: this.list.resIds },
                newWindow,
            },
        );
    }

    /** @returns {Object} */
    getFormActionContext() {
        return this.props.context;
    }

    /** @param {{ context?: Object, editable?: string }} [params] */
    async onAdd({ context, editable } = {}) {
        log.logic("onAdd", () => ({
            name: this.props.name,
            many2many: this.isMany2Many,
            editable,
        }));
        context = makeContext([this.props.context, context]);
        if (this.isMany2Many) {
            const domain = getFieldDomain(
                this.props.record,
                this.props.name,
                this.props.domain,
            );
            const { string } = this.props;
            const title = _t("Add: %s", string);
            return this.selectCreate({ domain, context, title });
        }
        if (editable) {
            const editedRecord = this.list.editedRecord;
            if (editedRecord) {
                // leaveEditMode asks the fields for their pending changes itself
                await this.list.leaveEditMode({ canAbandon: false });
            }
            if (!this.list.editedRecord) {
                return this.addInLine({ context, editable });
            }
            return;
        }
        return this._openRecord({ context });
    }

    async openRecord(record) {
        log.logic("openRecord", () => ({
            name: this.props.name,
            resId: record.resId,
            canOpen: this.canOpenRecord,
        }));
        if (this.canOpenRecord) {
            return this._openRecord({
                record,
                context: this.props.context,
                readonly: this.props.readonly,
            });
        }
    }
}

/** @type {WeakMap<object, Record<string, any>>} */
const CRUD_OPTIONS = new WeakMap();

/**
 * @param {Record<string, any>} options
 * @returns {Record<string, any>}
 */
function crudOptionsFor(options) {
    let crudOptions = CRUD_OPTIONS.get(options);
    if (!crudOptions) {
        crudOptions = {
            create: options.create,
            delete: options.delete,
            link: options.link,
            unlink: options.unlink,
            write: options.write,
        };
        CRUD_OPTIONS.set(options, crudOptions);
    }
    return crudOptions;
}

export const x2ManyField = {
    component: X2ManyField,
    displayName: _t("Relational table"),
    supportedAttributes: [
        archAttribute("add-label", _t("Add button label"), {
            help: _t('Text of the row/card creation button, replacing "Add a line".'),
        }),
    ],
    supportedOptions: [
        {
            label: _t("Can create"),
            name: "create",
            type: "string",
            help: _t(
                "Python domain; creation is offered only for records it matches. `False` forbids it outright.",
            ),
        },
        {
            label: _t("Can delete"),
            name: "delete",
            type: "string",
            help: _t("Python domain gating the per-row delete action."),
        },
        {
            label: _t("Can link"),
            name: "link",
            type: "string",
            help: _t("many2many only: Python domain gating 'Add' / the select dialog."),
        },
        {
            label: _t("Can unlink"),
            name: "unlink",
            type: "string",
            help: _t(
                "many2many only: Python domain gating removal of an existing link.",
            ),
        },
        {
            label: _t("Can write"),
            name: "write",
            type: "string",
            help: _t(
                "Python domain; when it does not match, the sub-view is read-only.",
            ),
        },
    ],
    supportedTypes: ["one2many", "many2many"],
    useSubView: true,
    extractProps: (
        /** @type {Record<string, any>} */ {
            attrs,
            relatedFields,
            viewMode,
            views,
            widget,
            options,
            string,
        },
        /** @type {Record<string, any>} */ dynamicInfo,
    ) => {
        const props = {
            addLabel: attrs["add-label"],
            context: dynamicInfo.context,
            domain: dynamicInfo.domain,
            crudOptions: crudOptionsFor(options),
            string,
        };
        if (viewMode) {
            props.views = views;
            props.viewMode = viewMode;
            props.relatedFields = relatedFields;
        }
        if (widget) {
            props.widget = widget;
        }
        return props;
    },
};

registerField({ name: "one2many", aliases: ["many2many"] }, x2ManyField);
