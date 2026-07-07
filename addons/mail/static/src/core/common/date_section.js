import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class DateSection extends Component {
    static template = "mail.DateSection";

    setup() {
        super.setup(...arguments);
        this.className = propComputed("className", t.string().optional());
        this.date = propComputed("date", t.string());
    }

    get isMobileOS() {
        return isMobileOS();
    }
}
