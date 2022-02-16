/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { Pager } from "@web/core/pager/pager";

const { Component } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

export class X2ManyField extends Component {
    setup() {
        this.dialogService = useService("dialog");
        const fieldInfo = this.props.record.activeFields[this.props.name];
        if (fieldInfo.views && fieldInfo.viewMode in fieldInfo.views) {
            const subViewInfo = fieldInfo.views[fieldInfo.viewMode];
            this.Renderer = X2M_RENDERERS[fieldInfo.viewMode];
            this.viewType = fieldInfo.viewMode;
            this.editable = subViewInfo.editable;
            this.rendererProps = {
                info: subViewInfo,
                fields: subViewInfo.fields, // is this necessary?
                list: this.props.value,
                readonly: true,
                openRecord: this.openRecord.bind(this),
            };
            if (this.viewType === "list") {
                this.rendererProps.leaveEdition = () => {
                    // TODO: send changes to the model
                    this.rendererProps.editedRecordId = null;
                    this.render();
                };
            }
        }
    }

    get pagerProps() {
        const list = this.props.value;
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
        if (this.viewType === "list" && !this.props.readonly && this.editable) {
            this.rendererProps.editedRecordId = record.id;
            this.render();
        } else {
            this.dialogService.add(FormViewDialog, {
                archInfo: this.props.value.views.form, // FIXME: might not be there
                record,
                readonly: this.props.readonly,
                title: this.props.record.activeFields[this.props.name].string,
            });
        }
    }
}

X2ManyField.useSubView = true;
X2ManyField.components = { Pager };
X2ManyField.props = {
    ...standardFieldProps,
    viewMode: { type: Array, optional: true }, // check this
};
X2ManyField.template = "web.X2ManyField";

registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
