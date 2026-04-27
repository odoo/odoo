import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class CopyButtonReferral extends Component {
    static template = "hr_referral.CopyButtonReferral";
    static props = { ...standardFieldProps }

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick() {
        const referral_link = await this.orm.call(
            "hr.job",
            "get_referral_link",
            [this.props.record.data.id, "direct"]
        );
        try{
            await browser.navigator.clipboard.writeText(referral_link);
            this.notification.add(
                _t("Referral link: %s has been copied to clipboard", referral_link),
                { type: "success" }
            );
        } catch (error) {
            this.notification.add(
                _t("Error while copying the Referral link: %s to clipboard", referral_link),
                { type: "danger", sticky: true }
            );
            browser.console.warn(error);
        }
    }
}


export const copyClipboardReferralButton = {
    component: CopyButtonReferral,
};

registry.category("fields").add("CopyClipboardReferralButton", copyClipboardReferralButton);
