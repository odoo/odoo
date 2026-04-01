import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CopyButtonJob extends CopyButton {
    static template = "website_hr_recruitment.CopyButtonJob";

    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    showTooltip() {
        this.notification.add(_t("The job link has been copied to the clipboard."), { type: 'success', });
    }
}
export class CopyClipboardCharField extends Component {
    static components = { CopyButtonJob };
    static template = "website_hr_recruitment.CopyJobLinkButton";
    static props = { ...standardFieldProps }

    setup() {
        this.copyText = _t("Share Job");
        this.successText = _t("Copied");
    }
}

export const copyClipboardJobLinkButton = {
    component: CopyClipboardCharField,
};

registry.category("fields").add("CopyClipboardJobLinkButton", copyClipboardJobLinkButton);
