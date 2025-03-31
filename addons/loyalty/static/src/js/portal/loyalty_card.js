import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

import { PortalLoyaltyCardDialog } from './loyalty_card_dialog/loyalty_card_dialog'

publicWidget.registry.PortalLoyaltyWidget = publicWidget.Widget.extend({
    selector: '.o_loyalty_container',
    events: {
        'click .o_loyalty_card': '_onClickLoyaltyCard',
    },

    async _onClickLoyaltyCard(ev) {
        const card_id = ev.currentTarget.dataset.card_id;
        let data = await rpc(`/my/loyalty_card/${card_id}/values`);
        this.call("dialog", "add", PortalLoyaltyCardDialog, data);
    },

});
