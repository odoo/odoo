/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormArchParser } from "@web/views/form/form_view";

const { onWillStart } = owl;

export class FormViewDialog extends Dialog {
    setup() {
        super.setup();
        this.viewService = useService("view");
        this.archInfo = this.props.archInfo;
        this.title = sprintf(this.env._t("Open: %s"), this.props.title);

        onWillStart(async () => {
            if (!this.archInfo) {
                const { form } = await this.viewService.loadViews({
                    resModel: this.props.record.resModel,
                    context: this.props.record.context,
                    views: [[this.props.viewId || false, "form"]],
                });
                const archInfo = new FormArchParser().parse(form.arch, form.fields);
                this.archInfo = {
                    ...archInfo,
                    fields: form.fields,
                };
            }
            // FIXME: here we override the fields of the list/kanban view
            Object.assign(this.props.record.activeFields, this.archInfo.activeFields);
            Object.assign(this.props.record.fields, this.archInfo.fields);
            this.props.record.fieldNames = Object.keys(this.props.record.activeFields);
            await this.props.record.load();
        });
    }

    save() {
        const { record, relatedRecord } = this.props;
        Object.assign(relatedRecord._values, record._values);
        Object.assign(relatedRecord._changes, record._changes); // don't work with x2many inside,...
        this.close();
    }

    cancel() {
        this.close(); // if this remains like that put this in template direclty
    }
}
FormViewDialog.bodyTemplate = "web.FormViewDialogBody";
FormViewDialog.footerTemplate = "web.FormViewDialogFooter";
FormViewDialog.components = { FormRenderer };
FormViewDialog.contentClass = "o_form_view_dialog";
FormViewDialog.props = {
    ...Dialog.props,
    record: true,
    archInfo: true,
};
