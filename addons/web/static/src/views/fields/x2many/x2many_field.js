/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { registry } from "@web/core/registry";
import { Pager } from "@web/core/pager/pager";
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

const { Component } = owl;

export class X2ManyField extends Component {
    setup() {
        this.activeField = this.props.record.activeFields[this.props.name];
        this.field = this.props.record.fields[this.props.name];

        this.isMany2Many =
            this.field.type === "many2many" || this.activeField.widget === "many2many";

        this.addButtonText = this.props.addLabel || this.env._t("Add");

        this.viewMode = this.activeField.viewMode;

        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        let archInfo;
        if (this.viewMode) {
            archInfo = this.activeField.views[this.viewMode];
        } else {
            archInfo = {};
        }
        const subViewActiveActions = archInfo.activeActions;
        this.activeActions = useActiveActions({
            crudOptions: Object.assign({}, this.activeField.options, {
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
            withParentId: this.activeField.widget !== "many2many",
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
        const selectCreate = useSelectCreate({
            resModel: this.props.value.resModel,
            activeActions: this.activeActions,
            onSelected: (resIds) => saveRecord(resIds),
            onCreateEdit: ({ context }) => this._openRecord({ context }),
        });

        this.selectCreate = (params) => {
            const p = Object.assign({}, params);
            p.domain = [...(p.domain || []), "!", ["id", "in", this.props.value.currentIds]];
            return selectCreate(p);
        };
    }

    get displayAddButton() {
        return (
            this.viewMode === "kanban" &&
            ("link" in this.activeActions ? this.activeActions.link : this.activeActions.create) &&
            !this.props.readonly
        );
    }

    get list() {
        return this.props.value;
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
        const archInfo = this.activeField.views[this.viewMode];
        const props = {
            archInfo,
            list: this.list,
            openRecord: this.openRecord.bind(this),
        };

        if (this.viewMode === "kanban") {
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
            const { string } = this.props.record.activeFields[this.props.name];
            const title = sprintf(this.env._t("Add: %s"), string);
            return this.selectCreate({ domain, context, title });
        }
        if (editable) {
            if (this.list.editedRecord) {
                const proms = [];
                this.list.model.env.bus.trigger("RELATIONAL_MODEL:NEED_LOCAL_CHANGES", { proms });
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
        return this._openRecord({ record, mode: this.props.readonly ? "readonly" : "edit" });
    }
}
X2ManyField.components = { Pager, KanbanRenderer, ListRenderer };
X2ManyField.props = {
    ...standardFieldProps,
    addLabel: { type: "string", optional: true },
    editable: { type: "string", optional: true },
};
X2ManyField.supportedTypes = ["one2many"];
X2ManyField.template = "web.X2ManyField";
X2ManyField.useSubView = true;
X2ManyField.extractProps = ({ attrs }) => {
    return {
        addLabel: attrs["add-label"],
    };
};

registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
