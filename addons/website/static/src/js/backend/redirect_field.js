/** @odoo-module **/

import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";

const { Component } = owl;

class RedirectField extends Component {
    get info() {
        return this.props.value ? this.env._t("Published") : this.env._t("Unpublished");
    }

    onClick() {
        this.env.onClickViewButton({
            clickParams: {
                type: "object",
                name: "open_website_url",
            },
            getResParams: () =>
                pick(this.props.record, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }
}

RedirectField.template = "website.RedirectField";
registry.category("fields").add("website_redirect_button", RedirectField);
