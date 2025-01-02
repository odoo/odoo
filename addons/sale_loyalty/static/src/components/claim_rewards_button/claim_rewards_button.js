import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { useService } from '@web/core/utils/hooks';
import { Component, useState } from "@odoo/owl";
import { ViewButton } from '@web/views/view_button/view_button';
import { useRecordObserver } from '@web/model/relational_model/utils';

export class ClaimRewardsButton extends Component {
    static template = 'sale_loyalty.ClaimRewardsButton';
    static components = { ViewButton };
    static props = { ...standardWidgetProps };

    setup() {
        this.clickParams = {
            name: 'action_open_reward_wizard',
            type: 'object',
            help: _t("Update current promotional lines and select new rewards if applicable."),
        };
        this.orm = useService('orm');
        this.state = useState({ hasClaimableRewards: false });
        useRecordObserver(async (record) => {
            record.data;
            this.state.hasClaimableRewards = false;
            await this._fetchRewardsCount(record.resId);
        });
    }

    get className() {
        return `btn btn-secondary ${this.state.hasClaimableRewards && 'highlight text-action'}`
    }

    async _fetchRewardsCount(orderId) {
        if (!orderId) return;
        const { claimable_rewards_count } = await this.orm.call(
            'sale.order', 'get_rewards_data', [orderId]
        );
        this.state.hasClaimableRewards = !!claimable_rewards_count;
    }
}

export const claimRewardsButton = {
    component: ClaimRewardsButton,
};

registry.category('view_widgets').add('claim_rewards_button', claimRewardsButton);
