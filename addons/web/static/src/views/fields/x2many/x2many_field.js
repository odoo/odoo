/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { _t } from "@web/core/l10n/translation";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import {
    useActiveActions,
    useAddInlineRecord,
    useOpenX2ManyRecord,
    useSelectCreate,
    useX2ManyCrud,
} from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { computeViewClassName } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class X2ManyField extends Component {
    static template = "web.X2ManyField";
    static components = { Pager, KanbanRenderer, ListRenderer, ViewButton };
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

    setup() {
        this.field = this.props.record.fields[this.props.name];
        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        this.archInfo = this.props.views?.[this.props.viewMode] || {};
        const classes = this.props.viewMode
            ? ["o_field_x2many", `o_field_x2many_${this.props.viewMode}`]
            : ["o_field_x2many"];
        this.className = computeViewClassName(this.props.viewMode, this.archInfo.xmlDoc, classes);

        const { activeActions, creates } = this.archInfo;
        if (this.props.viewMode === "kanban") {
            this.creates = creates.length
                ? creates
                : [
                      {
                          type: "create",
                          string: this.props.addLabel || _t("Add"),
                          class: "o-kanban-button-new",
                      },
                  ];
        }
        const subViewActiveActions = activeActions;
        this.activeActions = useActiveActions({
            crudOptions: Object.assign({}, this.props.crudOptions, {
                onDelete: removeRecord,
            }),
            fieldType: this.isMany2Many ? "many2many" : "one2many",
            subViewActiveActions,
            getEvalParams: (props) => {
                return {
                    evalContext: props.record.evalContext,
                    readonly: props.readonly,
                };
            },
        });

        this.addInLine = useAddInlineRecord({
            addNew: (...args) => this.list.addNewRecord(...args),
        });

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord,
            updateRecord,
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
        this.canOpenRecord =
            this.props.viewMode === "list"
                ? !(this.archInfo.editable || this.props.editable)
                : true;

        const selectCreate = useSelectCreate({
            resModel: this.props.record.data[this.props.name].resModel,
            activeActions: this.activeActions,
            onSelected: (resIds) => saveRecord(resIds),
            onCreateEdit: ({ context }) => this._openRecord({ context }),
            onUnselect: this.isMany2Many ? undefined : () => saveRecord(),
        });

        this.selectCreate = (params) => {
            const p = Object.assign({}, params);
            p.domain = [
                ...(p.domain || []),
                "!",
                ["id", "in", this.props.record.data[this.props.name].currentIds],
            ];
            return selectCreate(p);
        };
        this.action = useService("action");
    }

    get activeField() {
        return {
            fields: this.props.relatedFields,
            views: this.props.views,
            viewMode: this.props.viewMode,
            string: this.props.string,
        };
    }

    get displayControlPanelButtons() {
        return (
            this.props.viewMode === "kanban" &&
            ("link" in this.activeActions ? this.activeActions.link : this.activeActions.create) &&
            !this.props.readonly
        );
    }

    get isMany2Many() {
        return this.field.type === "many2many" || this.props.widget === "many2many";
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get nestedKeyOptionalFieldsData() {
        return {
            field: this.props.name,
            model: this.props.record.resModel,
            viewMode: "form",
        };
    }

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
                    if (initialLimit === limit && initialLimit === this.list.limit + 1) {
                        // Unselecting the edited record might have abandonned it. If the page
                        // size was reached before that record was created, the limit was temporarily
                        // increased to keep that new record in the current page, and abandonning it
                        // decreased this limit back to it's initial value, so we keep this into
                        // account in the offset/limit update we're about to do.
                        offset -= 1;
                        limit -= 1;
                    }
                    await list.load({ limit, offset });
                    this.render();
                }
            },
            withAccessKey: false,
        };
    }

    get rendererProps() {
        const { archInfo } = this;
        const props = {
            archInfo,
            list: this.list,
            openRecord: this.openRecord.bind(this),
            evalViewModifier: (modifier) => {
                return evaluateBooleanExpr(modifier, this.list.evalContext);
            },
        };

        if (this.props.viewMode === "kanban") {
            const recordsDraggable = !this.props.readonly && archInfo.recordsDraggable;
            props.archInfo = { ...archInfo, recordsDraggable };
            props.readonly = this.props.readonly;
            // TODO: apply same logic in the list case
            props.deleteRecord = (record) => {
                if (this.isMany2Many) {
                    return this.list.forget(record);
                }
                return this.list.delete(record);
            };
            return props;
        }

        const editable =
            (this.archInfo.activeActions.edit && archInfo.editable) || this.props.editable;
        props.activeActions = this.activeActions;
        props.cycleOnTab = false;
        props.editable = !this.props.readonly && editable;
        props.nestedKeyOptionalFieldsData = this.nestedKeyOptionalFieldsData;
        props.onAdd = (params) => {
            params.editable =
                !this.props.readonly && ("editable" in params ? params.editable : editable);
            this.onAdd(params);
        };
        const openFormView = props.editable ? archInfo.openFormView : false;
        props.onOpenFormView = openFormView ? this.switchToForm.bind(this) : undefined;
        return props;
    }

    switchToForm(record) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                res_id: record.resId,
                res_model: this.list.resModel,
            },
            {
                props: { resIds: this.list.resIds },
            }
        );
    }

    async onAdd({ context, editable } = {}) {
        const domain =
            typeof this.props.domain === "function" ? this.props.domain() : this.props.domain;
        context = makeContext([this.props.context, context]);
        if (this.isMany2Many) {
            const { string } = this.props;
            const title = _t("Add: %s", string);
            return this.selectCreate({ domain, context, title });
        }
        if (editable) {
            if (this.list.editedRecord) {
                const proms = [];
                this.list.model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
                await Promise.all([...proms, this.list.editedRecord._updatePromise]);
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
        if (this.canOpenRecord) {
            return this._openRecord({ record, mode: this.props.readonly ? "readonly" : "edit" });
        }
    }
}

export const x2ManyField = {
    component: X2ManyField,
    displayName: _t("Relational table"),
    supportedTypes: ["one2many", "many2many"],
    useSubView: true,
    extractProps: (
        { attrs, relatedFields, viewMode, views, widget, options, string },
        dynamicInfo
    ) => {
        const props = {
            addLabel: attrs["add-label"],
            context: dynamicInfo.context,
            domain: dynamicInfo.domain,
            crudOptions: options,
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

registry.category("fields").add("one2many", x2ManyField);
registry.category("fields").add("many2many", x2ManyField);
