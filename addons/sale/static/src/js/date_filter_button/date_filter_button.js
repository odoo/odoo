import { Component, t, useProps } from '@odoo/owl';
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { _t } from '@web/core/l10n/translation';

export const DATE_OPTIONS = [
	{ id: 'last_7_days', label: _t("Last 7 days"), periodDays: 7 },
	{ id: 'last_30_days', label: _t("Last 30 days"), periodDays: 30 },
	{ id: 'last_90_days', label: _t("Last 90 days"), periodDays: 90 },
	{ id: 'last_365_days', label: _t("Last 365 days"), periodDays: 365 },
];

export class DateFilterButton extends Component {
	static template = 'sale.DateFilterButton';
	static components = { Dropdown, DropdownItem };
	props = useProps({
		selectedDateFilter: t
			.object({
				id: t.string(),
				label: t.string(),
				periodDays: t.number(),
			})
			.optional(),
		update: t.function(),
	});

	get dateFilters() {
		return DATE_OPTIONS;
	}
}
