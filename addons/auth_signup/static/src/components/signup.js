import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class ResetPasswordLinkButton extends Component {
    static template = "auth_signup.reset_password_link_button";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async copyResetPasswordLink() {
        const resetPasswordLink = await this.orm.call("res.users", "get_reset_password_link", [
            this.props.record.resId,
        ]);
        setTimeout(async () => {
            await browser.navigator.clipboard.writeText(resetPasswordLink);
            this.notification.add(_t("Link copied to clipboard!"), { type: "success" });
        });
    }
}

export const buttonResetPasswordLink = {
    component: ResetPasswordLinkButton,
    additionalClasses: ["h-100", "ms-2", "my-auto"],
};
registry
    .category("view_widgets")
    .add("auth_signup.button_reset_password_link", buttonResetPasswordLink);
