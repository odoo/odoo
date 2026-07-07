import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CountryFlag extends Component {
    static template = "mail.CountryFlag";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.class = propComputed("class", t.string().optional());
        this.country = propComputed("country", t.instanceOf(this.store["res.country"]));
    }
}
