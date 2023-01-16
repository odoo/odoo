/** @odoo-module **/

import { onWillStart } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";

import { RadioField } from "@web/views/fields/radio/radio_field";

export class SelectRewardRadio extends RadioField {
    setup() {
        this.id = `select_reward_radio_${++SelectRewardRadio.nextId}`;
        this.orm = useService("orm");
        onWillStart(async () => {
            const orderId = this.props.record.data.order_id[0];
            this.data = await this.orm.call("sale.loyalty.reward.wizard", "get_reward_info", [[orderId]]);
        });
    }

    get items() {
        return this.data || [];
    }

    get value() {
        if (this.props.type === "many2one") {
            return Array.isArray(this.props.value) ? this.props.value[0] : this.props.value;
        }
        return null;
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        if (this.props.type === "many2one") {
            this.props.update(value);
        }
    }
}

SelectRewardRadio.additionalClasses = ["o_field_radio"];
SelectRewardRadio.nextId = 0;

SelectRewardRadio.template = "sale_loyalty.SelectRewardRadioField";

SelectRewardRadio.displayName = _lt("Select Reward Radio");
SelectRewardRadio.supportedTypes = ["many2one"];

registry.category("fields").add("select_reward_radio", SelectRewardRadio);
