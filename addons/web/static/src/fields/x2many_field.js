/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { evalDomain } from "@web/views/relational_model";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { FormArchParser } from "@web/views/form/form_view";

const { Component, onWillDestroy } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

export class X2ManyField extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.viewService = useService("view");

        this.dialogClose = [];
        this.fieldInfo = this.props.record.activeFields[this.props.name];

        this.isMany2Many =
            this.props.record.fields[this.props.name].type === "many2many" ||
            this.fieldInfo.widget === "many2many";

        // FIXME WOWL: is it normal to get here without fieldInfo.views?
        if (this.fieldInfo.views && this.fieldInfo.viewMode in this.fieldInfo.views) {
            this.Renderer = X2M_RENDERERS[this.fieldInfo.viewMode];
            this.viewMode = this.fieldInfo.viewMode;
        }
        onWillDestroy(() => {
            this.dialogClose.forEach((close) => close());
        });
    }

    get list() {
        return this.props.value;
    }

    get rendererProps() {
        const archInfo = this.fieldInfo.views[this.viewMode];
        let columns;
        if (this.viewMode === "list") {
            columns = archInfo.columns.filter((col) => {
                if (col.type === "field" && "column_invisible" in col.modifiers) {
                    const invisible = evalDomain(
                        col.modifiers.column_invisible,
                        this.list.evalContext
                    );
                    return !invisible;
                }
                return true;
            });
        }
        return {
            activeActions: this.activeActions,
            editable: this.props.record.isInEdition && archInfo.editable,
            archInfo: { ...archInfo, columns },
            list: this.list,
            openRecord: this.openRecord.bind(this),
            onAdd: this.onAdd.bind(this),
        };
    }

    get activeActions() {
        // activeActions computed by getActiveActions is of the form
        // interface ActiveActions {
        //     edit: Boolean;
        //     create: Boolean;
        //     delete: Boolean;
        //     duplicate: Boolean;
        // }

        // options set on field is of the form
        // interface Options {
        //     create: Boolean;
        //     delete: Boolean;
        //     link: Boolean;
        //     unlink: Boolean;
        // }

        // We need to take care of tags "control" and "create" to set create stuff

        const { evalContext } = this.props.record;
        const { options } = this.fieldInfo;
        const subViewInfo = this.fieldInfo.views[this.viewMode];

        let canCreate = "create" in options ? evalDomain(options.create, evalContext) : true;
        canCreate = canCreate && subViewInfo.activeActions.create;

        if (this.viewMode !== "list") {
            return { canCreate };
        }

        let canDelete = "delete" in options ? evalDomain(options.delete, evalContext) : true;
        canDelete = canDelete && subViewInfo.activeActions.delete;

        const canLink = "link" in options ? evalDomain(options.link, evalContext) : true;
        const canUnlink = "unlink" in options ? evalDomain(options.unlink, evalContext) : true;

        // We need to compute some object used by (x2many renderers) based on that

        const result = { canCreate, canLink, canUnlink };

        const onDelete = (record) => {
            const list = this.list;
            const operation = this.isMany2Many ? "FORGET" : "DELETE";
            list.delete(record.id, operation);
            // + update pager info
            this.render();
        }; // use this in kanban and adapt (forget,...)?

        if (canDelete) {
            result.onDelete = onDelete;
        }

        return result;
    }

    get displayAddButton() {
        return (
            this.viewMode === "kanban" && this.activeActions.canCreate
            // && this.props.record.mode === "readonly"
        );
    }

    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                await list.load({ limit, offset });
                this.render();
            },
            withAccessKey: false,
        };
    }

    async openRecord(record) {
        const form = await this._getFormViewInfo();
        const newRecord = await this.list.model.duplicateDatapoint(record, {
            mode: this.props.readonly ? "readonly" : "edit",
            viewMode: "form",
            fields: { ...form.fields, id: { name: "id", type: "integer", readonly: true } },
            views: { form },
        });
        this.dialogClose.push(
            this.dialogService.add(FormViewDialog, {
                archInfo: form, // FIXME: might not be there
                record: newRecord,
                save: () => {
                    newRecord.save({ savePoint: true, stayInEdition: true });
                    record.__syncData();
                    record.model.notify();
                },
                title: sprintf(
                    this.env._t("Open: %s"),
                    this.props.record.activeFields[this.props.name].string
                ),
            })
        );
    }

    async onAdd(context) {
        const archInfo = this.fieldInfo.views[this.viewMode];
        const editable = archInfo.editable;
        if (editable) {
            this.list.addNew({ context, mode: "edit", position: editable });
        } else {
            const form = await this._getFormViewInfo();
            const record = this.list.model.createDataPoint("record", {
                context: makeContext([this.list.context, context]),
                resModel: this.list.resModel,
                fields: {
                    ...form.fields,
                    id: { name: "id", type: "integer", readonly: true },
                },
                activeFields: form.activeFields || {},
                views: { form },
                mode: "edit",
                viewType: "form",
            });
            await record.load(); //AAB TO DISCUSS
            this.dialogClose.push(
                this.dialogService.add(FormViewDialog, {
                    archInfo: form, // FIXME: might not be there
                    record,
                    save: async () => {
                        record.switchMode("readonly");
                        await this.list.add(record);
                    },
                    title: sprintf(
                        this.env._t("Open: %s"),
                        this.props.record.activeFields[this.props.name].string
                    ),
                })
            );
        }
    }

    async _getFormViewInfo() {
        let formViewInfo = this.fieldInfo.views.form;
        if (formViewInfo) {
            return formViewInfo;
        }

        const comodel = this.list.resModel;
        const { fields: comodelFields, views } = await this.viewService.loadViews({
            context: {},
            resModel: comodel,
            views: [[false, "form"]],
        });
        const archInfo = new FormArchParser().parse(views.form.arch, comodelFields);
        return { ...archInfo, fields: comodelFields }; // should be good to memorize this on activeField
        // fieldInfo.relatedFields = comodelFields;
    }
}

X2ManyField.components = { Pager };
X2ManyField.props = { ...standardFieldProps };
X2ManyField.template = "web.X2ManyField";
X2ManyField.useSubView = true;

registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
