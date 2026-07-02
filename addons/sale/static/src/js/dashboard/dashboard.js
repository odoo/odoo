import { _t } from '@web/core/l10n/translation';
import { Component, onWillStart, proxy } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import { useService, useBus } from '@web/core/utils/hooks';
import { DateFilterButton, DATE_OPTIONS } from '../date_filter_button/date_filter_button';

export const CARD_COLORS_MAPPING = {
    'to_confirm': 'orange',
    'to_fulfill': 'purple',
    'to_invoice': 'cyan',
    'to_upsell': 'red',
};

export const CARD_FILTERS_MAPPING = {
    'to_confirm': ['to_confirm'],
    'to_fulfill': ['to_fulfill', 'sales'],
    'to_invoice': ['to_invoice', 'sales'],
    'to_upsell': ['to_upsell', 'sales'],
};

export const DEFAULT_FILTERS = ['sales'];

export class Dashboard extends Component {
    static template = 'sale.Dashboard';
    static props = {};
    static components = { DateFilterButton };

    get cardFiltersMapping() {
        return CARD_FILTERS_MAPPING;
    }

    get defaultFilters() {
        return DEFAULT_FILTERS;
    }

    get dashboardCards() {
        return [
            { key: 'to_confirm', label: _t("To Confirm"), title: _t("Orders to Confirm")},
            { key: 'to_fulfill', label: _t("To Fulfill"), title: _t("Orders to Fulfill")},
            { key: 'to_invoice', label: _t("To Invoice"), title: _t("Orders to Invoice")},
            { key: 'to_upsell', label: _t("To Upsell"), title: _t("Orders to Upsell")},
        ];
    }

    get dashboardPeriodCards() {
        return [
            { key: 'orders', title: _t("Sales Orders"), monetary: false },
            { key: 'sales_amount', title: _t("Sales Revenue"), monetary: true },
        ];
    }

    setup() {
        this.state = proxy({
            dashboardData: {},
            selectedDateFilter: DATE_OPTIONS[0],
            selectedCard: '',
        });
        this.orm = useService('orm');

        useBus(this.env.searchModel, 'update', () => {
            for (const [cardName, filters] of Object.entries(this.cardFiltersMapping)) {
                if (this.isSameFilter(filters)) {
                    this.state.selectedCard = cardName;
                    return;
                }
            }
            this.state.selectedCard = '';
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData(filter = false) {
        if (filter) {
            this.state.selectedDateFilter = filter;
        }
        this.state.dashboardData = await this.fetchDashboardData();
    }

    async fetchDashboardData() {
        return this.orm.call(
            'sale.order',
            'retrieve_sale_dashboard',
            [this.state.selectedDateFilter.periodDays],
        );
    }

    isCardVisible(card) {
        return this.state.dashboardData[card.key] > 0;
    }

    isCardDisabled(cardName) {
        return false;
    }

    handleCardClick(ev) {
        const cardName = ev.currentTarget.getAttribute('card_name');
        if (this.isCardDisabled(cardName)) {
            return;
        }
        if (this.state.selectedCard === cardName) {
            this.setFilters(this.defaultFilters);
        } else {
            const filters = this.cardFiltersMapping[cardName];
            this.setFilters(filters);
        }
    }

    setFilters(filters) {
        const searchItems = this.env.searchModel.getSearchItems((item) =>
            filters.includes(item.name)
        );
        this.env.searchModel.query = [];
        for (const item of searchItems) {
            this.env.searchModel.toggleSearchItem(item.id);
        }
    }

    isSameFilter(filters) {
        const activeFilters = this.env.searchModel.getSearchItems(
            (el) => el.isActive && el.type === 'filter'
        );
        const activeFilterNames = activeFilters && activeFilters.map((el) => el.name);
        if (filters.length !== activeFilterNames.length) {
            return false;
        }
        const activeFilterSet = new Set(activeFilterNames);
        return filters.every(val => activeFilterSet.has(val));
    }

    getPeriodCardClass(cardName) {
        const periodGain = this.state.dashboardData[cardName]['gain'];
        if (periodGain > 0) {
            return 'text-success';
        } else if (periodGain < 0) {
            return 'text-danger';
        }
        return 'text-muted';
    }

    getDashboardCardAdditionalClass(cardName) {
        let dashboardCardClasses = [];
        if (this.isCardDisabled(cardName)) {
            dashboardCardClasses.push('bg-secondary text-secondary-emphasis disabled');
        } else {
            dashboardCardClasses.push('o_dashboard_card_' + CARD_COLORS_MAPPING[cardName]);
        }
        if (this.state.selectedCard === cardName) {
            dashboardCardClasses.push('active');
        }
        return dashboardCardClasses.join(' ');
    }

    formatCurrency(value) {
        return formatCurrency(value, this.state.dashboardData.currency_id);
    }
}
