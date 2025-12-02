import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from '@web/core/network/rpc';
import { PortalLoyaltyCardDialog } from '../js/portal/loyalty_card_dialog/loyalty_card_dialog';

export class LoyaltyCard extends Interaction {
    static selector = ".o_loyalty_container .o_loyalty_card";
    dynamicContent = {
        _root: { "t-on-click": this.onLoyaltyCardClick },
    };

    async onLoyaltyCardClick() {
        const data = await this.waitFor(rpc(`/my/loyalty_card/${this.el.dataset.card_id}/values`));
        this.services.dialog.add(PortalLoyaltyCardDialog, data);
    }
}

registry
    .category("public.interactions")
    .add("loyalty.loyalty_card", LoyaltyCard);
