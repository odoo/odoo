/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class RedirectField extends Component {
    static props = {...standardFieldProps};
    get info() {
        return this.props.record.data[this.props.name] ? _t("Published") : _t("Unpublished");
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

registry.category("fields").add("website_redirect_button", {
    component: RedirectField,
});
