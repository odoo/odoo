/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { FormRenderer } from "@web/views/form/form_renderer";
import { sprintf } from "@web/core/utils/strings";

export class FormViewDialog extends Dialog {
    setup() {
        super.setup();
        this.archInfo = this.props.archInfo;
        this.title = sprintf(this.env._t("Open: %s"), this.props.title);
    }

    async willStart() {
        Object.assign(this.props.record.activeFields, this.archInfo.fields);
        Object.assign(this.props.record.fields, this.archInfo.fields);
        this.props.record.fieldNames = Object.keys(this.props.record.activeFields);
        await this.props.record.load();
    }

    save() {
        console.log("TODO: savepoint");
        this.close();
    }

    cancel() {
        console.log("TODO: go back to savepoint");
        this.close();
    }
}
FormViewDialog.bodyTemplate = "web.FormViewDialogBody";
FormViewDialog.footerTemplate = "web.FormViewDialogFooter";
FormViewDialog.components = { FormRenderer };
FormViewDialog.contentClass = "o_form_view_dialog";
