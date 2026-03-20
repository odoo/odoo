import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { redirect } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

export class SlideInstallModule extends Component {
    static components = {};
    static props = {
        moduleData: {
            name: String,
            id: Number,
            default_slide_category: { type: String, optional: true },
        },
    };
    static template = "website_slides.SlideInstallModule";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            status: "start", // "failure", "installing"
            message: _t('Do you want to install "%s"?', this.props.moduleData.name),
        });
    }

    async installModule() {
        if (this.state.status === "installing") {
            return;
        }
        this.state.status = "installing";
        this.state.message = _t('Installing "%s"...', this.props.moduleData.name);
        try {
            await this.orm.call("ir.module.module", "button_immediate_install", [
                [this.props.moduleData.id],
            ]);
        } catch {
            this.state.hasFailed = "failure";
            this.state.message = _t('Failed to install "%s"', this.props.moduleData.name);
            return;
        }
        let redirectUrl = window.location.origin + window.location.pathname;
        if (this.props.moduleData.default_slide_category) {
            redirectUrl += "?enable_slide_upload=" + this.props.moduleData.default_slide_category;
        }
        redirect(redirectUrl);
    }
}
