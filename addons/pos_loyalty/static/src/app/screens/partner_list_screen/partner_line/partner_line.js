import { _t } from "@web/core/l10n/translation";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";

patch(PartnerLine.prototype, {
    /**
     * Loyalty points to display for this partner, one entry per loyalty program,
     * and eWallet balances (as currency).
     *
     * For the current order's customer the live total is shown (balance + points
     * earned - spent on this order, via program.getPoints); for anyone else, the
     * balance of their loaded card. Loyalty cards aren't loaded into the POS, so
     * relying on getPoints for the order's customer avoids needing the card in
     * memory. Programs the partner has neither a card nor points for are skipped.
     * @returns {{id: number, repr: string}[]}
     */
    getLoyaltyPoints() {
        const order = this.pos.getOrder();
        const isOrderPartner = order?.partner_id?.id === this.props.partner.id;
        const entries = [];
        for (const program of this.pos.models["loyalty.program"].filter((p) =>
            ["loyalty", "ewallet"].includes(p.program_type)
        )) {
            const card = this.pos.models["loyalty.card"].find(
                (c) => c.program_id?.id === program.id && c.partner_id?.id === this.props.partner.id
            );
            if (program.program_type === "ewallet") {
                if (!card) {
                    continue;
                }
                entries.push({
                    id: program.id,
                    repr: `${program.name}: ${this.pos.formatCurrency(card.points)}`,
                });
                continue;
            }
            const points = isOrderPartner ? program.getNewBalance(order) : card?.points || 0;
            if (!card && !points) {
                continue;
            }
            const balanceRepr = formatFloat(points, { digits: [69, 2] });
            entries.push({
                id: program.id,
                repr: program.portal_visible
                    ? `${balanceRepr} ${program.portal_point_name}`
                    : _t("%s Points", balanceRepr),
            });
        }
        return entries;
    },
});
