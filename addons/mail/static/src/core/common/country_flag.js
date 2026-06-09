import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CountryFlag extends Component {
    static template = "mail.CountryFlag";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            "class?": types.string(),
            country: types.instanceOf(this.store["res.country"].Class),
        });
    }
}
