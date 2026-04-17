import { Component } from "@odoo/owl";
import { formatCurrency } from '@web/core/currency';
import { SectionDropdown } from "../section_dropdown/section_dropdown";

export class SectionRow extends Component {
    static template = "account.SectionRow";

    static components = {
        SectionRow,
        SectionDropdown,
    };

    static props = {
        section: Object,
        state: Object,
    };

    get selectedSection() {
        return this.env.searchModel.selectedSection;
    }

    getFormattedSubTotal(section) {
        return formatCurrency(section.subtotal, section.currency_id);
    }

    toggle(section) {
        section.isOpen = !section.isOpen;
    }
}
