import { Component, computed, onWillStart, proxy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { AccountDashboardKpiCard } from "./account_dashboard_kpi_card";

export class AccountDashboardKpis extends Component {
    static template = "account.AccountDashboardKpis";
    static components = {
        AccountDashboardKpiCard,
    };

    hasInvoiceLayoutCard = computed(() =>
        this.state.cards.some((card) => card.is_invoice_layout_card)
    );

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({
            cards: [],
        });

        onWillStart(async () => {
            await this.loadCards();
        });
    }

    async loadCards() {
        this.state.cards = await this.orm
            .cache({
                type: "disk",
                update: "always",
                callback: (cards, hasChanged) => {
                    if (hasChanged) {
                        this.state.cards = cards;
                    }
                },
            })
            .call("account.journal", "get_account_dashboard_kpis", []);
    }

    async onClickCard(card) {
        if (!card.action_id) {
            return;
        }

        if (card.is_invoice_layout_card) {
            this.action.doAction(card.action_id, {
                onClose: async () => {
                    await this.loadCards();
                },
            });
            return;
        }

        return this.action.doAction(card.action_id);
    }
}
