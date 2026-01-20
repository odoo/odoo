import { _t } from '@web/core/l10n/translation';
import { Component, onWillStart, useState } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import { useService, useBus } from '@web/core/utils/hooks';
import { DateFilterButton, DATE_OPTIONS } from '../date_filter_button/date_filter_button';

export const CARD_COLORS_MAPPING = {
    'to_fulfill': 'purple',
    'to_confirm': 'orange',
    'to_invoice': 'cyan',
};

export const CARD_FILTERS_MAPPING = {
    'to_fulfill': ['to_fulfill', 'from_website', 'order_confirmed'],
    'to_confirm': ['to_confirm', 'from_website'],
    'to_invoice': ['to_invoice', 'from_website', 'order_confirmed'],
};

export const DEFAULT_FILTERS = ['from_website', 'order_confirmed'];

export class Dashboard extends Component {
	static template = 'website_sale.Dashboard';
    static props = {};
	static components = { DateFilterButton };

	setup() {
		this.state = useState({
			dashboardData: {},
			selectedDateFilter: DATE_OPTIONS[0],
			selectedCard: '',
		});
		this.orm = useService('orm');
		this.dashboardCards = [
			{ key: 'to_fulfill', label: _t("To Fulfill"), title: _t("Orders to Fulfill"), alwaysVisible: true },
			{ key: 'to_confirm', label: _t("To Confirm"), title: _t("Orders to Confirm"), alwaysVisible: false },
			{ key: 'to_invoice', label: _t("To Invoice"), title: _t("Orders to Invoice"), alwaysVisible: true },
		]

        this.dashboardPeriodCards = [
            { key: 'visitors', title: _t("Visitors"), monetary: false },
            { key: 'orders', title: _t("Orders"), monetary: false },
            { key: 'sales', title: _t("Sales"), monetary: true },
        ]

		useBus(this.env.searchModel, 'update', () => {
            for (const [cardName, filters] of Object.entries(CARD_FILTERS_MAPPING)) {
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
		this.state.dashboardData = await this.orm.call(
            'sale.order',
            'retrieve_ecommerce_dashboard',
            [this.state.selectedDateFilter.periodDays],
        );
	}

	handleCardClick(ev) {
        const cardName = ev.currentTarget.getAttribute('card_name');

		if (this.state.selectedCard === cardName) {
			this.setFilters(DEFAULT_FILTERS);
		} else {
			const filters = CARD_FILTERS_MAPPING[cardName];
            this.setFilters(filters);
		}
	}

	/**
	 * This method clears the current search query and activates
	 * the filters found in `filters`.
	 */
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
		const cardDataCount = this.state.dashboardData[cardName];
		if (cardDataCount == 0) {
			dashboardCardClasses.push('bg-secondary text-secondary-emphasis disabled')
		} else {
			dashboardCardClasses.push('o_dashboard_card_' + CARD_COLORS_MAPPING[cardName])
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
