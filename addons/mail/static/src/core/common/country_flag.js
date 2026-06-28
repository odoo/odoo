import { Component, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CountryFlag extends Component {
    static template = "mail.CountryFlag";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            class: t.string().optional(),
            country: t.instanceOf(this.store["res.country"].Class),
        });
    }
}
