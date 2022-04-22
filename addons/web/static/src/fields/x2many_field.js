/** @odoo-module **/

import { evalDomain } from "@web/views/relational_model";
import { FormArchParser, loadSubViews } from "@web/views/form/form_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { makeContext } from "@web/core/context";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

function useOwnedDialogs() {
    const addDialog = useService("dialog").add;
    const cbs = [];
    owl.onWillUnmount(() => cbs.forEach((cb) => cb()));

    const add = (...args) => {
        const close = addDialog(...args);
        cbs.push(close);
        return close;
    };
    return add;
}

export class X2ManyField extends Component {
    setup() {
        this.user = useService("user");
        this.viewService = useService("view");

        this.addDialog = useOwnedDialogs();

        this.activeField = this.props.record.activeFields[this.props.name];
        this.field = this.props.record.fields[this.props.name];

        this.isMany2Many =
            this.field.type === "many2many" || this.activeField.widget === "many2many";

        this.addButtonText = this.activeField.attrs["add-label"] || this.env._t("Add");

        // FIXME WOWL: is it normal to get here without activeField.views?
        if (this.activeField.views && this.activeField.viewMode in this.activeField.views) {
            this.Renderer = X2M_RENDERERS[this.activeField.viewMode];
            this.viewMode = this.activeField.viewMode;
        }
    }

    get list() {
        return this.props.value;
    }

    get rendererProps() {
        const archInfo = this.activeField.views[this.viewMode];
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
        const { options, views } = this.activeField;
        const subViewInfo = views[this.viewMode];

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
        this.addDialog(FormViewDialog, {
            archInfo: form, // FIXME: might not be there
            record: newRecord,
            save: () => this.updateRecord(record),
            title: sprintf(
                this.env._t("Open: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
        });
    }

    updateRecord(record) {
        this.list.model.updateRecord(this.list, record);
    }

    async onAdd(context) {
        const archInfo = this.activeField.views[this.viewMode];
        const editable = archInfo.editable;
        if (editable) {
            this.list.addNew({ context, mode: "edit", position: editable });
        } else {
            const form = await this._getFormViewInfo();
            const recordParams = {
                context: makeContext([this.list.context, context]),
                resModel: this.list.resModel,
                fields: {
                    ...form.fields,
                    id: { name: "id", type: "integer", readonly: true },
                },
                activeFields: form.activeFields,
                views: { form },
                mode: "edit",
                viewType: "form",
            };
            const record = await this.list.model.addNewRecord(this.list, recordParams);
            this.addDialog(FormViewDialog, {
                archInfo: form, // FIXME: might not be there
                record,
                save: async (record, { saveAndNew }) => {
                    await this.saveRecordToList(record);
                    if (saveAndNew) {
                        return this.list.model.addNewRecord(this.list, recordParams);
                    }
                },
                title: sprintf(
                    this.env._t("Open: %s"),
                    this.props.record.activeFields[this.props.name].string
                ),
            });
        }
    }

    async saveRecordToList(record) {
        await this.list.add(record);
    }

    async _getFormViewInfo() {
        let formViewInfo = this.activeField.views.form;
        const comodel = this.list.resModel;
        if (!formViewInfo) {
            const { fields, views } = await this.viewService.loadViews({
                context: {},
                resModel: comodel,
                views: [[false, "form"]],
            });
            const archInfo = new FormArchParser().parse(views.form.arch, fields);
            formViewInfo = { ...archInfo, fields }; // should be good to memorize this on activeField
        }

        await loadSubViews(
            formViewInfo.activeFields,
            formViewInfo.fields,
            {}, // context
            comodel,
            this.viewService,
            this.user
        );

        return formViewInfo;
    }
}

X2ManyField.components = { Pager };
X2ManyField.props = { ...standardFieldProps };
X2ManyField.template = "web.X2ManyField";
X2ManyField.useSubView = true;
registry.category("fields").add("one2many", X2ManyField);

export class Many2ManyField extends X2ManyField {
    onAdd(context) {
        const list = this.list;
        const { record, name } = this.props;
        let domain = record.getFieldDomain(name).toList();
        domain = [...domain, "!", ["id", "in", list.currentIds]];
        context = makeContext([record.getFieldContext(name), context]);
        this.addDialog(SelectCreateDialog, {
            title: this.env._t("Select records"),
            noCreate: !this.activeActions.canCreate,
            multiSelect: this.activeActions.canLink, // LPE Fixme
            resModel: list.resModel,
            context,
            domain: domain,
            onSelected: (resIds) => {
                list.add(resIds, { isM2M: true });
            },
            onCreateEdit: super.onAdd.bind(this, context),
        });
    }

    async saveRecordToList(record) {
        await this.list.add(record, { isM2M: true });
    }

    updateRecord(record) {
        this.list.model.updateRecord(this.list, record, { isM2M: true });
    }
}

registry.category("fields").add("many2many", Many2ManyField);
