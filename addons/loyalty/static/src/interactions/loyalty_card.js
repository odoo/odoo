import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from '@web/core/network/rpc';
import { PortalLoyaltyCardDialog } from '../js/portal/loyalty_card_dialog/loyalty_card_dialog';

export class LoyaltyCard extends Interaction {
    static selector = ".o_loyalty_container";
    dynamicContent = {
        ".o_loyalty_card": { "t-on-click.withTarget": this.onClickLoyaltyCard },
    };

    async onClickLoyaltyCard(ev, currentTargetEl) {
        const data = await this.waitFor(rpc(`/my/loyalty_card/${currentTargetEl.dataset.card_id}/values`));
        this.services.dialog.add(PortalLoyaltyCardDialog, data);
    }
}

registry
    .category("public.interactions")
    .add("loyalty.loyalty_card", LoyaltyCard);
