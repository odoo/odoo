import { Component, props, t } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class DateSection extends Component {
    static template = "mail.DateSection";

    setup() {
        super.setup(...arguments);
        this.props = props({
            className: t.string().optional(),
            date: t.string(),
        });
    }

    get isMobileOS() {
        return isMobileOS();
    }
}
