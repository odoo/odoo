/** @odoo-module **/

import { createElement } from "@web/core/utils/xml";
import { Dialog } from "@web/core/dialog/dialog";
import { evalDomain } from "@web/views/relational_model";
import { FormArchParser, loadSubViews } from "@web/views/form/form_view";
import { FormRenderer } from "@web/views/form/form_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { makeContext } from "@web/core/context";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { useViewButtons } from "@web/views/view_button/hook";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, onWillUnmount } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

function useOwnedDialogs() {
    const dialogService = useService("dialog");
    const cbs = [];
    onWillUnmount(() => {
        cbs.forEach((cb) => cb());
    });
    const addDialog = (...args) => {
        const close = dialogService.add(...args);
        cbs.push(close);
    };
    return addDialog;
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

        this.viewMode = this.activeField.viewMode;
        this.Renderer = X2M_RENDERERS[this.viewMode];
    }

    get list() {
        return this.props.value;
    }

    get rendererProps() {
        const archInfo = this.activeField.views[this.viewMode];
        let columns;
        if (this.viewMode === "list") {
            // handle column_invisible modifiers
            // first remove (column_)invisible buttons in button_groups
            columns = archInfo.columns.map((col) => {
                if (col.type === "button_group") {
                    const buttons = col.buttons.filter((button) => {
                        return !this.evalColumnInvisibleModifier(button.modifiers);
                    });
                    return { ...col, buttons };
                }
                return col;
            });
            // then filter out (column_)invisible fields and empty button_groups
            columns = columns.filter((col) => {
                if (col.type === "field") {
                    return !this.evalColumnInvisibleModifier(col.modifiers);
                } else if (col.type === "button_group") {
                    return col.buttons.length > 0;
                }
                return true;
            });
        }
        const props = {
            activeActions: this.activeActions,
            editable: this.props.record.isInEdition && archInfo.editable,
            archInfo: { ...archInfo, columns },
            list: this.list,
            openRecord: this.openRecord.bind(this),
            onAdd: this.onAdd.bind(this),
        };
        if (this.viewMode === "kanban") {
            props.readonly = this.props.readonly;
        }
        return props;
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

        let canDelete = "delete" in options ? evalDomain(options.delete, evalContext) : true;
        canDelete = canDelete && subViewInfo.activeActions.delete;
        const deleteFn = this.removeRecordFromList.bind(this);

        let canLink = "link" in options ? evalDomain(options.link, evalContext) : true;
        let canUnlink = "unlink" in options ? evalDomain(options.unlink, evalContext) : true;

        const result = { canCreate, canDelete };
        if (this.isMany2Many) {
            Object.assign(result, { canLink, canUnlink });
        }
        if ((this.isMany2Many && canUnlink) || (!this.isMany2Many && canDelete)) {
            result.onDelete = deleteFn;
        }
        return result;
    }

    get displayAddButton() {
        const { canCreate, canLink } = this.activeActions;
        return (
            this.viewMode === "kanban" &&
            (canLink !== undefined ? canLink : canCreate) &&
            !this.props.readonly
        );
    }

    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                const initialLimit = this.list.limit;
                const unselected = await list.unselectRecord();
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

    evalColumnInvisibleModifier(modifiers) {
        if ("column_invisible" in modifiers) {
            return evalDomain(modifiers.column_invisible, this.list.evalContext);
        }
        return false;
    }

    async openRecord(record) {
        const form = await this._getFormViewInfo();
        const newRecord = await this.list.model.duplicateDatapoint(record, {
            mode: this.props.readonly ? "readonly" : "edit",
            viewMode: "form",
            fields: { ...form.fields },
            views: { form },
        });
        const { canDelete, onDelete } = this.activeActions;
        this.addDialog(X2ManyFieldDialog, {
            archInfo: form,
            record: newRecord,
            save: async (record, { saveAndNew }) => {
                if (record.id === newRecord.id) {
                    await this.updateRecord(record);
                } else {
                    await this.saveRecordToList(record);
                }
                if (saveAndNew) {
                    return this.list.model.addNewRecord(this.list, {
                        context: this.list.context,
                        resModel: this.list.resModel,
                        activeFields: form.activeFields,
                        fields: { ...form.fields },
                        views: { form },
                        mode: "edit",
                        viewType: "form",
                    });
                }
            },
            title: sprintf(
                this.env._t("Open: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
            delete: this.viewMode === "kanban" && canDelete ? () => onDelete(record) : null,
        });
    }

    updateRecord(record) {
        this.list.model.updateRecord(this.list, record);
    }

    async onAdd(context) {
        const archInfo = this.activeField.views[this.viewMode];
        const editable = archInfo.editable;
        if (editable) {
            if (!this.creatingRecord) {
                this.creatingRecord = true;
                try {
                    await this.list.addNew({ context, mode: "edit", position: editable });
                } finally {
                    this.creatingRecord = false;
                }
            }
        } else {
            const form = await this._getFormViewInfo();
            const recordParams = {
                context: makeContext([this.list.context, context]),
                resModel: this.list.resModel,
                activeFields: form.activeFields,
                fields: { ...form.fields },
                views: { form },
                mode: "edit",
                viewType: "form",
            };
            const record = await this.list.model.addNewRecord(this.list, recordParams);
            this.addDialog(X2ManyFieldDialog, {
                archInfo: form,
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

    async removeRecordFromList(record) {
        const list = this.list;
        const operation = this.isMany2Many ? "FORGET" : "DELETE";
        await list.delete(record.id, operation);
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
        const { record, name } = this.props;
        const domain = [
            ...record.getFieldDomain(name).toList(),
            "!",
            ["id", "in", this.list.currentIds],
        ];
        context = makeContext([record.getFieldContext(name), context]);
        this.addDialog(SelectCreateDialog, {
            title: this.env._t("Select records"),
            noCreate: !this.activeActions.canCreate,
            multiSelect: this.activeActions.canLink, // LPE Fixme
            resModel: this.list.resModel,
            context,
            domain,
            onSelected: (resIds) => {
                this.list.add(resIds, { isM2M: true });
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

class X2ManyFieldDialog extends Component {
    setup() {
        super.setup();
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;

        useBus(this.record.model, "update", () => this.render(true));

        this.modalRef = useChildRef();

        const reload = () => this.record.load();
        useViewButtons(this.props.record.model, this.modalRef, { reload }); // maybe pass the model directly in props

        if (this.archInfo.xmlDoc.querySelector("footer")) {
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(
                ...[...this.archInfo.xmlDoc.querySelectorAll("footer")]
            );
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            [...this.archInfo.xmlDoc.querySelectorAll("footer")].forEach((x) => x.remove());
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }
    }

    disableButtons() {
        const btns = this.modalRef.el.querySelectorAll(".modal-footer button");
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        return btns;
    }

    discard() {
        if (this.record.isInEdition) {
            this.record.discard();
        }
        this.props.close();
    }

    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }

    async save({ saveAndNew }) {
        if (this.record.checkValidity()) {
            this.record = await this.props.save(this.record, { saveAndNew });
        } else {
            return false;
        }
        if (!saveAndNew) {
            this.props.close();
        }
        return true;
    }

    async remove() {
        await this.props.delete();
        this.props.close();
    }

    async saveAndNew() {
        const disabledButtons = this.disableButtons();
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            this.enableButtons(disabledButtons);
            if (this.title) {
                this.title = this.title.replace(this.env._t("Open:"), this.env._t("New:"));
            }
            this.render(true);
        }
    }
}
X2ManyFieldDialog.components = { Dialog, FormRenderer, ViewButton };
X2ManyFieldDialog.props = {
    archInfo: Object,
    close: Function,
    record: Object,
    save: Function,
    title: String,
    delete: { optional: true },
};
X2ManyFieldDialog.template = "web.X2ManyFieldDialog";
