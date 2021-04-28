/** @odoo-module **/

import publicWidget from 'web.public.widget';
import wUtils from 'website.utils';

publicWidget.registry.websiteSaleLoyaltyAddReward = publicWidget.Widget.extend({
    selector: '.o_wloyalty_add_reward_button',
    events: {
        'click': '_onClickAdd',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickAdd: async function () {
        const params = {
            reward_id: this.$el.data('rewardId'),
            add_qty: 1,
        };
        return wUtils.sendRequest('/shop/cart/update_reward', params);
    },
});

export default publicWidget.registry.websiteSaleLoyaltyAddReward;
