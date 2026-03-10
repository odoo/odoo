/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class PartnerLedger extends owl.Component {
    setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.unfoldButton = useRef('unfoldButton');
        this.dialog = useService("dialog");
        this.state = useState({
            partners: null,
            data: null,
            total: null,
            title: null,
            currency: null,
            filter_applied: null,
            selected_partner: [],
            selected_partner_rec: [],
            total_debit: null,
            total_debit_display:null,
            total_credit: null,
            partner_list: null,
            total_list: null,
            date_range: null,
            account: null,
            options: null,
            message_list : [],
        });
        this.load_data(self.initial_render = true);
    }

    formatNumberWithSeparators(number) {
        const parsedNumber = parseFloat(number);
        if (isNaN(parsedNumber)) {
            return "0.00"; // Fallback to 0.00 if the input is invalid
        }
        return parsedNumber.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    async load_data() {
        /**
         * Loads the data for the partner ledger report.
         */
        let partner_list = []
        let partner_totals = ''
        let totalDebitSum = 0;
        let totalCreditSum = 0;
        let currency;
        var self = this;
        var action_title = self.props.action.display_name;
        try {
            var self = this;
            self.state.data = await self.orm.call("account.partner.ledger", "view_report", [[this.wizard_id], action_title,]);
            const dataArray = self.state.data;
             Object.entries(dataArray).forEach(([key, value]) => {
            if (key !== 'partner_totals') {
                partner_list.push(key);
                value.forEach(entry => {
                    entry[0].debit_display = this.formatNumberWithSeparators(entry[0].debit || 0);
                    entry[0].credit_display = this.formatNumberWithSeparators(entry[0].credit || 0);
                    entry[0].amount_currency_display = this.formatNumberWithSeparators(entry[0].amount_currency || 0);
        });
            } else {
                partner_totals = value;
            }
            });
            Object.values(partner_totals).forEach(partner => {
                currency = partner.currency_id;
                totalDebitSum += partner.total_debit || 0;
                totalCreditSum += partner.total_credit || 0;
                partner.total_debit_display = this.formatNumberWithSeparators(partner.total_debit || 0)
                partner.total_credit_display = this.formatNumberWithSeparators(partner.total_credit || 0)
            });
            self.state.partners = partner_list
            self.state.partner_list = partner_list
            self.state.total_list = partner_totals
            self.state.total = partner_totals
            self.state.currency = currency
            self.state.total_debit = totalDebitSum
            self.state.total_debit_display = this.formatNumberWithSeparators(self.state.total_debit || 0)
            self.state.total_credit = totalCreditSum
            self.state.total_credit_display = this.formatNumberWithSeparators(self.state.total_credit || 0)
            self.state.title = action_title
        }
        catch (el) {
            window.location.href;
        }
    }
        async printPdf(ev) {
        /**
         * Generates and displays a PDF report for the partner ledger.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        ev.preventDefault();
        let partner_list = []
        let partner_value = []
        let partner_totals = ''
        let totals = {
            'total_debit':this.state.total_debit,
            'total_debit_display':this.state.total_debit_display,
            'total_credit':this.state.total_credit,
            'total_credit_display':this.state.total_credit_display,
            'currency':this.state.currency,
        }
        var action_title = this.props.action.display_name;
        return this.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.partner_ledger',
            'report_file': 'dynamic_accounts_report.partner_ledger',
            'data': {
                'partners': this.state.partners,
                'filters': this.filter(),
                'grand_total': totals,
                'data': this.state.data,
                'total': this.state.total,
                'title': action_title,
                'report_name': this.props.action.display_name
            },
            'display_name': this.props.action.display_name,
        });
    }
    filter() {
    var self=this;
    let startDate, endDate;
    let startYear, startMonth, startDay, endYear, endMonth, endDay;
        if (self.state.date_range){
            const today = new Date();
            if (self.state.date_range === 'year') {
                startDate = new Date(today.getFullYear(), 0, 1);
                endDate = new Date(today.getFullYear(), 11, 31);
            } else if (self.state.date_range === 'quarter') {
                const currentQuarter = Math.floor(today.getMonth() / 3);
                startDate = new Date(today.getFullYear(), currentQuarter * 3, 1);
                endDate = new Date(today.getFullYear(), (currentQuarter + 1) * 3, 0);
            } else if (self.state.date_range === 'month') {
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            } else if (self.state.date_range === 'last-month') {
                startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                endDate = new Date(today.getFullYear(), today.getMonth(), 0);
            } else if (self.state.date_range === 'last-year') {
                startDate = new Date(today.getFullYear() - 1, 0, 1);
                endDate = new Date(today.getFullYear() - 1, 11, 31);
            } else if (self.state.date_range === 'last-quarter') {
                const lastQuarter = Math.floor((today.getMonth() - 3) / 3);
                startDate = new Date(today.getFullYear(), lastQuarter * 3, 1);
                endDate = new Date(today.getFullYear(), (lastQuarter + 1) * 3, 0);
            }
        // Get the date components for start and end dates
        if (startDate) {
        startYear = startDate.getFullYear();
        startMonth = startDate.getMonth() + 1;
        startDay = startDate.getDate();
        }
        if (endDate) {
        endYear = endDate.getFullYear();
        endMonth = endDate.getMonth() + 1;
        endDay = endDate.getDate();
        }
        }
        let filters = {
            'partner': self.state.selected_partner_rec,
            'account': self.state.account,
            'options': self.state.options,
            'start_date': null,
            'end_date': null,
        };
        // Check if start and end dates are available before adding them to the filters object
        if (startYear !== undefined && startMonth !== undefined && startDay !== undefined &&
            endYear !== undefined && endMonth !== undefined && endDay !== undefined) {
            filters['start_date'] = `${startYear}-${startMonth < 10 ? '0' : ''}${startMonth}-${startDay < 10 ? '0' : ''}${startDay}`;
            filters['end_date'] = `${endYear}-${endMonth < 10 ? '0' : ''}${endMonth}-${endDay < 10 ? '0' : ''}${endDay}`;
        }
        return filters
    }
    async print_xlsx() {
        /**
         * Generates and downloads an XLSX report for the partner ledger.
         */
        var self = this;

        let partner_list = []
        let partner_value = []
        let partner_totals = ''
        let totals = {
            'total_debit':this.state.total_debit,
            'total_credit':this.state.total_credit,
            'currency':this.state.currency,
        }
        var action_title = self.props.action.display_name;
        var datas = {
            'partners': self.state.partners,
            'data': self.state.data,
            'total': self.state.total,
            'title': action_title,
            'filters': this.filter(),
            'grand_total': totals,
        }
        var action = {
            'data': {
                'model': 'account.partner.ledger',
                'data': JSON.stringify(datas),
                'output_format': 'xlsx',
                'report_action': self.props.action.xml_id,
                'report_name': action_title,
            },
        };
        BlockUI;
        await download({
            url: '/xlsx_report',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
    }
    gotoJournalEntry(ev) {
        /**
         * Navigates to the journal entry form view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move',
            res_id: parseInt(ev.target.attributes["data-id"].value, 10),
            views: [[false, "form"]],
            target: "current",
        });
    }
    gotoJournalItem(ev) {
        /**
         * Navigates to the journal items list view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move.line',
            name: "Journal Items",
            views: [[false, "list"]],
            domain: [["partner_id", "=", parseInt(ev.target.attributes["data-id"].value, 10)], ['account_type', 'in', ['liability_payable', 'asset_receivable']]],
            target: "current",
        });
    }
    openPartner(ev) {
        /**
         * Opens the partner form view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'res.partner',
            res_id: parseInt(ev.target.attributes["data-id"].value, 10),
            views: [[false, "form"]],
            target: "current",
        });
    }
    async applyFilter(val, ev, is_delete = false) {
        /**
         * Applies filters to the partner ledger report based on the provided values.
         *
         * @param {any} val - The value of the filter.
         * @param {Event} ev - The event object triggered by the action.
         * @param {boolean} is_delete - Indicates whether the filter value is being deleted.
         */
        let partner_list = []
        let partner_value = []
        let partner_totals = ''
        let month = null
        this.state.partners = null
        this.state.data = null
        this.state.total = null
        this.state.filter_applied = true;
        let totalDebitSum = 0;
        let totalCreditSum = 0;
        if (ev) {
            if (ev.input && ev.input.attributes.placeholder.value == 'Partner' && !is_delete) {
                this.state.selected_partner.push(val[0].id)
                this.state.selected_partner_rec.push(val[0])
            } else if (is_delete) {
                let index = this.state.selected_partner_rec.indexOf(val)
                this.state.selected_partner_rec.splice(index, 1)
                this.state.selected_partner = this.state.selected_partner_rec.map((rec) => rec.id)
            }
        }
        else {
            if (val.target.name === 'start_date') {
                this.state.date_range = {
                    ...this.state.date_range,
                    start_date: val.target.value
                };
            } else if (val.target.name === 'end_date') {
                this.state.date_range = {
                    ...this.state.date_range,
                    end_date: val.target.value
                };
            } else if (val.target.attributes["data-value"].value == 'month') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value == 'year') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value == 'quarter') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value == 'last-month') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value == 'last-year') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value == 'last-quarter') {
                this.state.date_range = val.target.attributes["data-value"].value
            } else if (val.target.attributes["data-value"].value === 'receivable') {
                // Check if the target has 'selected-filter' class
                if (val.target.classList.contains("selected-filter")) {
                    // Remove 'receivable' key from account
                    const { Receivable, ...updatedAccount } = this.state.account;
                    this.state.account = updatedAccount;
                    val.target.classList.remove("selected-filter");
                } else {
                    // Update receivable property in account
                    this.state.account = {
                        ...this.state.account,
                        'Receivable': true
                    };
                    val.target.classList.add("selected-filter"); // Add class "selected-filter"
                }
            } else if (val.target.attributes["data-value"].value === 'payable') {
                // Check if the target has 'selected-filter' class
                if (val.target.classList.contains("selected-filter")) {
                    // Remove 'receivable' key from account
                    const { Payable, ...updatedAccount } = this.state.account;
                    this.state.account = updatedAccount;
                    val.target.classList.remove("selected-filter");
                } else {
                    // Update receivable property in account
                    this.state.account = {
                        ...this.state.account,
                        'Payable': true
                    };
                    val.target.classList.add("selected-filter"); // Add class "selected-filter"
                }
            } else if (val.target.attributes["data-value"].value === 'draft') {
                // Check if the target has 'selected-filter' class
                if (val.target.classList.contains("selected-filter")) {
                    // Remove 'receivable' key from account
                    const { draft, ...updatedAccount } = this.state.options;
                    this.state.options = updatedAccount;
                    val.target.classList.remove("selected-filter");
                } else {
                    // Update receivable property in account
                    this.state.options = {
                        ...this.state.options,
                        'draft': true
                    };
                    val.target.classList.add("selected-filter"); // Add class "selected-filter"
                }
            }
        }
        let filtered_data = await this.orm.call("account.partner.ledger", "get_filter_values", [this.state.selected_partner, this.state.date_range, this.state.account, this.state.options,]);
        for (let index in filtered_data) {
            const value = filtered_data[index];
            if (index !== 'partner_totals') {
                partner_list.push(index)
            }
            else {
                partner_totals = value
                Object.values(partner_totals).forEach(partner_list => {
                        totalDebitSum += partner_list.total_debit || 0;
                        totalCreditSum += partner_list.total_credit || 0;
                    });
            }
        }
        this.state.partners = partner_list
        this.state.data = filtered_data
        this.state.total = partner_totals
        this.state.total_debit = totalDebitSum
        this.state.total_credit = totalCreditSum
        if (this.unfoldButton.el.classList.contains("selected-filter")) {
            this.unfoldButton.el.classList.remove("selected-filter");
        }
    }
    getDomain() {
        return [];
    }
    async unfoldAll(ev) {
        /**
         * Unfolds all items in the table body if the event target does not have the 'selected-filter' class,
         * or folds all items if the event target has the 'selected-filter' class.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        if (!ev.target.classList.contains("selected-filter")) {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                this.tbody.el.children[length].classList.add('show')
            }
            ev.target.classList.add("selected-filter");
        } else {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                  this.tbody.el.children[length].classList.remove('show')
            }
            ev.target.classList.remove("selected-filter");
        }
    }
}
PartnerLedger.defaultProps = {
    resIds: [],
};
PartnerLedger.template = 'pl_template_new';
actionRegistry.add("p_l", PartnerLedger);
