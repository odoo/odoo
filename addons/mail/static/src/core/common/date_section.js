import { Component, t, useProps } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class DateSection extends Component {
    static template = "mail.DateSection";

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            className: t.string().optional(),
            date: t.string(),
        });
    }

    get isMobileOS() {
        return isMobileOS();
    }
}
