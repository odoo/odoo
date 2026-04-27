/** @odoo-module **/

import { onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { useService } from '@web/core/utils/hooks';


class OnlineAccountRadio extends RadioField {
    static template = "account_online_synchronization.OnlineAccountRadio";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({balances: {}});

        onMounted(async () => {
            this.state.balances = await this.loadData();
            // Make sure the first option is selected by default.
            this.onChange(this.items[0]);
        });
    }

    async loadData() {
        const ids = this.items.map(i => i[0]);
        return await this.orm.call("account.online.account", "get_formatted_balances", [ids]);
    }

    getBalanceName(itemID) {
        return this.state.balances?.[itemID]?.[0] ?? "Loading ...";
    }

    isNegativeAmount(itemID) {
        // In case of the value is undefined, it will return false as intended.
        return this.state.balances?.[itemID]?.[1] < 0;
    }
}

registry.category("fields").add("online_account_radio", {
    ...radioField,
    component: OnlineAccountRadio,
});
