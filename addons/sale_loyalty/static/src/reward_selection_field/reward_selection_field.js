import { Component, useProps } from "@odoo/owl";
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
        return this.props.record.data.reward_groups || [];
    }

    get rewardIds() {
        return this.props.record.data[this.props.name].currentIds;
    }

    get productIds() {
        return this.props.record.data.selected_product_ids.currentIds;
    }

    getSelectedOption(group) {
        return group.options.find(
            (option) =>
                this.rewardIds.includes(option.reward_id) &&
                (!option.product_id || this.productIds.includes(option.product_id))
        );
    }

    isSelected(group, option) {
        return this.getSelectedOption(group) === (option || undefined);
    }

    async onSelect(group, option) {
        const previous = this.getSelectedOption(group);
        const otherGroups = this.groups.filter((other) => other !== group);
        // Keep the product if the option selected in another group gives it too
        const isProductUsedElsewhere = otherGroups.some(
            (other) => this.getSelectedOption(other)?.product_id === previous?.product_id
        );
        if (option?.reward_id !== previous?.reward_id) {
            await this.props.record.data[this.props.name].addAndRemove({
                add: option ? [option.reward_id] : [],
                remove: previous ? [previous.reward_id] : [],
            });
        }
        await this.props.record.data.selected_product_ids.addAndRemove({
            add: option?.product_id ? [option.product_id] : [],
            remove: previous?.product_id && !isProductUsedElsewhere ? [previous.product_id] : [],
        });
    }
}

registry.category("fields").add("sale_loyalty_reward_selection", {
    component: RewardSelectionField,
    supportedTypes: ["many2many"],
});
