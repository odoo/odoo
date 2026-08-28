import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { Component, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useViewButtonHandler } from "@web/views/view_button/view_button_hook";

class RedirectField extends Component {
    static template = "website.RedirectField";
    props = useProps({ ...standardFieldProps });

    handleViewButton = useViewButtonHandler();

    get info() {
        if (
            Object.hasOwn(this.props.record.data, "publish_on") &&
            this.props.record.data.publish_on
        ) {
            return _t("Scheduled");
        }
        return this.props.record.data[this.props.name] ? _t("Published") : _t("Unpublished");
    }

    onClick() {
        this.handleViewButton({
            clickParams: {
                type: "object",
                name: "open_website_url",
            },
            getResParams: () =>
                pick(this.props.record, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }
}

registry.category("fields").add("website_redirect_button", {
    component: RedirectField,
});
