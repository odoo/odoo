import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Displays the claimable rewards grouped by program (`reward_groups`) and lets select one option,
 * or none, in each group. The selected rewards are stored in the field (a many2many), and the
 * products chosen for them in `selected_product_ids`.
 */
export class RewardSelectionField extends Component {
    static template = "sale_loyalty.RewardSelectionField";
    props = useProps(standardFieldProps);

    get groups() {
        const noneOption = { label: _t("None") };
        return (this.props.record.data.reward_groups || []).map((group) => ({
            ...group,
            options: [noneOption, ...group.options],
        }));
    }

    /**
     * Return the option selected in the group, or its "None" option.
     */
    getSelectedOption(group) {
        const rewardIds = this.props.record.data[this.props.name].currentIds;
        const productIds = this.props.record.data.selected_product_ids.currentIds;
        const selected = group.options.find(
            (option) =>
                rewardIds.includes(option.reward_id) &&
                (!option.product_id || productIds.includes(option.product_id))
        );
        return selected || group.options[0];
    }

    async onSelect(group, option) {
        const groups = this.groups;
        const selectedOptions = groups
            .map((other) =>
                other.coupon_id === group.coupon_id ? option : this.getSelectedOption(other)
            )
            .filter((selected) => selected.reward_id);
        // Keep the rewards selected outside of the groups, i.e. the ones of the applied codes
        const groupRewardIds = groups.flatMap((other) => other.options.map((o) => o.reward_id));
        const otherRewardIds = this.props.record.data[this.props.name].currentIds.filter(
            (rewardId) => !groupRewardIds.includes(rewardId)
        );
        await this.props.record.data[this.props.name].set([
            ...otherRewardIds,
            ...selectedOptions.map((selected) => selected.reward_id),
        ]);
        await this.props.record.data.selected_product_ids.set(
            selectedOptions.map((selected) => selected.product_id).filter(Boolean)
        );
    }
}

registry.category("fields").add("sale_loyalty_reward_selection", {
    component: RewardSelectionField,
    supportedTypes: ["many2many"],
});
