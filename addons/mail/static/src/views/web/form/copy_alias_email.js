import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

export class CopyClipboardAliasEmail extends Component {
    static template = "mail.CopyClipboardAliasEmail";
    static props = {
        ...standardWidgetProps,
    };
    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
    }

    async copyEmail() {
        const { alias_name, alias_domain } = this.props.record.data;
        if (alias_name && alias_domain) {
            const email = `${alias_name}@${alias_domain}`;
            await browser.navigator.clipboard.writeText(email);
            this.notification.add(_t("Email alias copied to clipboard!"), { type: "success" });
        }
    }
}

export const copyClipboardAliasEmail = {
    component: CopyClipboardAliasEmail,
    additionalClasses: ["d-inline"],
};
registry.category("view_widgets").add("copy_alias_email", copyClipboardAliasEmail);
