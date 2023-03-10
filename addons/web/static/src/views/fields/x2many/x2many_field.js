/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { _lt } from "@web/core/l10n/translation";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
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
import { evalDomain } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";

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
        views: { type: Object, optional: true },
    };
    static defaultProps = {
        archInfo: {},
    };

    setup() {
        this.field = this.props.record.fields[this.props.name];
        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        this.archInfo = this.props.views[this.props.viewMode] || {};

        const { activeActions, creates } = this.archInfo;
        if (this.props.viewMode === "kanban") {
            this.creates = creates.length
                ? creates
                : [
                      {
                          type: "create",
                          string: this.props.addLabel || this.env._t("Add"),
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
            addNew: (...args) => this.list.addNew(...args),
        });

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord,
            updateRecord,
            withParentId: this.props.widget !== "many2many",
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
    }

    get activeField() {
        return {
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
            viewMode: this.props.record.viewMode || this.props.record.__viewType,
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
                const unselected = await list.unselectRecord(true);
                if (unselected) {
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
        };

        if (this.props.viewMode === "kanban") {
            const recordsDraggable = !this.props.readonly && archInfo.recordsDraggable;
            props.archInfo = { ...archInfo, recordsDraggable };
            props.readonly = this.props.readonly;
            return props;
        }

        // handle column_invisible modifiers
        const columns = archInfo.columns
            .map((col) => {
                // first remove (column_)invisible buttons in button_groups
                if (col.type === "button_group") {
                    const buttons = col.buttons.filter((button) => {
                        return !this.evalColumnInvisibleModifier(button.modifiers);
                    });
                    return { ...col, buttons };
                }
                return col;
            })
            .filter((col) => {
                // filter out (column_)invisible fields and empty button_groups
                if (col.type === "field") {
                    return !this.evalColumnInvisibleModifier(col.modifiers);
                } else if (col.type === "button_group") {
                    return col.buttons.length > 0;
                }
                return true;
            });

        const editable = archInfo.editable || this.props.editable;
        props.activeActions = this.activeActions;
        props.archInfo = { ...archInfo, columns };
        props.cycleOnTab = false;
        props.editable = !this.props.readonly && editable;
        props.nestedKeyOptionalFieldsData = this.nestedKeyOptionalFieldsData;
        props.onAdd = (params) => {
            params.editable =
                !this.props.readonly && ("editable" in params ? params.editable : editable);
            this.onAdd(params);
        };
        return props;
    }

    evalColumnInvisibleModifier(modifiers) {
        if ("column_invisible" in modifiers) {
            return evalDomain(modifiers.column_invisible, this.list.evalContext);
        }
        return false;
    }

    async onAdd({ context, editable } = {}) {
        const record = this.props.record;
        const domain = record.getFieldDomain(this.props.name).toList();
        context = makeContext([record.getFieldContext(this.props.name), context]);
        if (this.isMany2Many) {
            const { string } = this.props;
            const title = sprintf(this.env._t("Add: %s"), string);
            return this.selectCreate({ domain, context, title });
        }
        if (editable) {
            if (this.list.editedRecord) {
                const proms = [];
                this.list.model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
                await Promise.all([...proms, this.list.editedRecord._updatePromise]);
                await this.list.editedRecord.switchMode("readonly", { checkValidity: true });
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
    displayName: _lt("Relational table"),
    supportedTypes: ["one2many", "many2many"],
    useSubView: true,
    extractProps: ({ attrs, viewMode, views, widget, options, string }) => {
        const props = {
            addLabel: attrs["add-label"],
            viewMode,
            views,
            crudOptions: options,
            string,
        };
        if (widget) {
            props.widget = widget;
        }
        return props;
    },
};

registry.category("fields").add("one2many", x2ManyField);
registry.category("fields").add("many2many", x2ManyField);
