import { _t } from '@web/core/l10n/translation';
import { Dashboard as SaleDashboard, CARD_COLORS_MAPPING } from '@sale/js/dashboard/dashboard';

export { CARD_COLORS_MAPPING };

export const CARD_FILTERS_MAPPING = {
    'to_fulfill': ['to_fulfill', 'from_website', 'order_confirmed'],
    'to_confirm': ['to_confirm', 'from_website'],
    'to_invoice': ['to_invoice', 'from_website', 'order_confirmed'],
};

export const DEFAULT_FILTERS = ['from_website', 'order_confirmed'];

export class Dashboard extends SaleDashboard {
    get cardFiltersMapping() {
        return CARD_FILTERS_MAPPING;
    }

    get defaultFilters() {
        return DEFAULT_FILTERS;
    }

    get dashboardCards() {
        return [
            { key: 'to_fulfill', label: _t("To Fulfill"), title: _t("Orders to Fulfill") },
            { key: 'to_confirm', label: _t("To Confirm"), title: _t("Orders to Confirm") },
            { key: 'to_invoice', label: _t("To Invoice"), title: _t("Orders to Invoice") },
        ];
    }

    get dashboardPeriodCards() {
        return [
            { key: 'visitors', title: _t("Visitors"), monetary: false },
            { key: 'orders', title: _t("Orders"), monetary: false },
            { key: 'sales', title: _t("Sales"), monetary: true },
        ];
    }

    isCardVisible() {
        return true;
    }

    isCardDisabled(cardName) {
        return this.state.dashboardData[cardName] == 0;
    }

    async fetchDashboardData() {
        return this.orm.call(
            'sale.order',
            'retrieve_ecommerce_dashboard',
            [this.state.selectedDateFilter.periodDays],
        );
    }
}
