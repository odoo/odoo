/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { evalDomain } from "@web/views/relational_model";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

const { Component } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

export class X2ManyField extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.fieldInfo = this.props.record.activeFields[this.props.name];
        // FIXME WOWL: is it normal to get here without fieldInfo.views?
        if (this.fieldInfo.views && this.fieldInfo.viewMode in this.fieldInfo.views) {
            this.Renderer = X2M_RENDERERS[this.fieldInfo.viewMode];
            this.viewMode = this.fieldInfo.viewMode;
        }
    }

    get list() {
        return this.props.value;
    }

    get rendererProps() {
        const archInfo = this.fieldInfo.views[this.viewMode];
        return {
            activeActions: this.activeActions,
            editable: this.props.record.isInEdition && archInfo.editable,
            archInfo,
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
        if (this.viewMode !== "list") {
            return null;
        }
        const { evalContext } = this.props.record;
        const { options } = this.fieldInfo;
        const subViewInfo = this.fieldInfo.views[this.viewMode];
        // options set on field is of the form
        // interface Options {
        //     create: Boolean;
        //     delete: Boolean;
        //     link: Boolean;
        //     unlink: Boolean;
        // }

        // We need to take care of tags "control" and "create" to set create stuff

        let canCreate = "create" in options ? evalDomain(options.create, evalContext) : true;
        let canDelete = "delete" in options ? evalDomain(options.delete, evalContext) : true;
        const canLink = "link" in options ? evalDomain(options.link, evalContext) : true;
        const canUnlink = "unlink" in options ? evalDomain(options.unlink, evalContext) : true;

        canCreate = canCreate && subViewInfo.activeActions.create;
        canDelete = canDelete && subViewInfo.activeActions.delete;

        // We need to compute some object used by (x2many renderers) based on that

        const result = { canCreate, canLink, canUnlink };

        const onDelete = (record) => {
            const list = this.list;
            list.delete(record.id);
            // + update pager info
            this.render();
        };

        if (canDelete) {
            result.onDelete = onDelete;
        }

        return result;
    }

    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                list.offset = offset;
                list.limit = limit;
                await list.load();
                this.render();
            },
            withAccessKey: false,
        };
    }

    openRecord(record) {
        const form = this.list.views.form;
        const newRecord = this.list.model.createDataPoint("record", {
            context: record.context,
            resModel: record.resModel,
            fields: { ...form.fields, id: { name: "id", type: "integer", readonly: true } },
            activeFields: form.activeFields,
            views: { form },
            mode: "edit",
            viewMode: "form",
            values: record._values,
            changes: record._changes,
            resId: record.resId,
        });
        this.dialogService.add(FormViewDialog, {
            parent: this,
            archInfo: form, // FIXME: might not be there
            record: newRecord,
            save: () => {
                Object.assign(record._values, newRecord._values);
                Object.assign(record._changes, newRecord._changes); // don't work with x2many inside,...
                record.data = { ...record._values, ...record._changes };
                record.onChanges();
                record.model.notify();
            },
            title: sprintf(
                this.env._t("Open: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
        });
    }

    onAdd(context) {
        const archInfo = this.fieldInfo.views[this.viewMode];
        if (archInfo.editable) {
            this.list.addNew({ context, mode: "edit" });
        } else {
            const form = this.list.views.form;
            const record = this.list.model.createDataPoint("record", {
                context: makeContext([this.list.context, context]),
                resModel: this.list.resModel,
                fields: {
                    ...(form || {}).fields,
                    id: { name: "id", type: "integer", readonly: true },
                },
                activeFields: (form || {}).activeFields || {},
                views: { form },
                mode: "edit",
                viewMode: "form",
            });
            this.dialogService.add(FormViewDialog, {
                parent: this,
                archInfo: form, // FIXME: might not be there
                record,
                save: () => {
                    record.switchMode("readonly");
                    this.list.addNew({
                        context: this.list.context,
                        resModel: this.list.resModel,
                        fields: this.list.fields,
                        activeFields: this.list.activeFields,
                        views: this.list.views,
                        mode: "readonly",
                        values: record._values,
                        changes: record._changes,
                    });
                },
                title: sprintf(
                    this.env._t("Open: %s"),
                    this.props.record.activeFields[this.props.name].string
                ),
            });
        }
    }
}

X2ManyField.components = { Pager };
X2ManyField.props = { ...standardFieldProps };
X2ManyField.template = "web.X2ManyField";
X2ManyField.useSubView = true;

registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
