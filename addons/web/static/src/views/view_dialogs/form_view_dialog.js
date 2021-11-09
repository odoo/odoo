/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormArchParser } from "@web/views/form/form_view";
import { sprintf } from "@web/core/utils/strings";

export class FormViewDialog extends Dialog {
    setup() {
        super.setup();
        this.archInfo = new FormArchParser().parse(this.props.arch, this.props.fields);
        this.title = sprintf(this.env._t("Open: %s"), this.props.title);
        // FIXME: probably not at the right place (also necessary for main form views)
        if (!this.archInfo.fields.display_name) {
            this.archInfo.fields.display_name = { name: "display_name", type: "char" };
        }
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
