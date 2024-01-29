import { FormLabel } from "@web/views/form/form_label";
import { HighlightText } from "./highlight_text";

export class FormLabelHighlightText extends FormLabel {
    static template = "web.FormLabelHighlightText";
    static components = { HighlightText };
    setup() {
        super.setup();
        const isEnterprise = odoo.info && odoo.info.isEnterprise;
        if (
            this.props.fieldInfo &&
            this.props.fieldInfo.field &&
            this.props.fieldInfo.field.isUpgradeField &&
            !isEnterprise
        ) {
            this.upgradeEnterprise = true;
        }
    }
}
