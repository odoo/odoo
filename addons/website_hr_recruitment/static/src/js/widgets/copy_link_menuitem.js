import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { Component, usePlugin, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CopyButtonJob extends CopyButton {
    static template = "website_hr_recruitment.CopyButtonJob";

    notification = usePlugin(NotificationPlugin);

    showTooltip() {
        this.notification.add(_t("The job link has been copied to the clipboard."), { type: 'success', });
    }
}
export class CopyClipboardCharField extends Component {
    static components = { CopyButtonJob };
    static template = "website_hr_recruitment.CopyJobLinkButton";
    props = useProps(standardFieldProps);

    setup() {
        this.copyText = _t("Share Job");
        this.successText = _t("Copied");
    }
}

export const copyClipboardJobLinkButton = {
    component: CopyClipboardCharField,
};

registry.category("fields").add("CopyClipboardJobLinkButton", copyClipboardJobLinkButton);
