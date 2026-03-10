/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class BankBook extends owl.Component {
    async setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.dialog = useService("dialog");
        this.tbody = useRef('tbody');
        this.unfoldButton = useRef('unfoldButton');
        this.state = useState({
            move_line: null,
            data: null,
            total: null,
            accounts: null,
            filter_applied: null,
            selected_partner: [],
            selected_partner_rec: [],
            date_range: null,
            options: null,
            selected_account_list: [],
            total_debit: null,
            total_debit_display: null,
            total_credit: null,
            total_credit_display: null,
            currency: null,
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
         * Loads the data for the bank book report.
         */
        let move_line_list = []
        let move_lines_total = ''
        let accounts = [];
        var self = this;
        let totalDebitSum = 0;
        let totalCreditSum = 0;
        let currency;
        var action_title = self.props.action.display_name;
        try {
            var self = this;
            self.state.data = await self.orm.call("bank.book.report", "view_report", []);


            for (const index in self.state.data) {
                const value = self.state.data[index];
                if (index !== 'move_lines_total' && index !== 'accounts') {
                    move_line_list.push(index);
                } else if (index === 'accounts') {
                    self.state.accounts = value;
                } else {
                    move_lines_total = value;
                    for (const moveLine of Object.values(move_lines_total)) {
                        currency = moveLine.currency_id;
                        totalDebitSum += moveLine.total_debit || 0;
                        totalCreditSum += moveLine.total_credit || 0;
                        moveLine.total_debit_display = this.formatNumberWithSeparators(moveLine.total_debit || 0);
                        moveLine.total_credit_display = this.formatNumberWithSeparators(moveLine.total_credit || 0);
                        moveLine.balance = this.formatNumberWithSeparators(moveLine.total_debit - moveLine.total_credit || 0);
                    }

                }
            }



            self.state.move_line = move_line_list
            for (const key of move_line_list) {
                for (const line of self.state.data[key]) {
                    if (line.debit !== undefined) {
                        line.debit_display = this.formatNumberWithSeparators(line.debit || 0);
                    }
                    if (line.credit !== undefined) {
                        line.credit_display = this.formatNumberWithSeparators(line.credit || 0);
                    }
                    if (line.balance !== undefined) {
                        line.balance_display = this.formatNumberWithSeparators(line.balance || 0);
                    }
                }
            }
            self.state.total = move_lines_total
            self.state.currency = currency
            self.state.total_debit = totalDebitSum.toFixed(2)
            self.state.total_debit_display = this.formatNumberWithSeparators(self.state.total_debit)
            self.state.total_credit = totalCreditSum.toFixed(2)
            self.state.total_credit_display = this.formatNumberWithSeparators(self.state.total_credit)
        }
        catch (el) {
            window.location.href;
        }
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
    getDomain() {
        return [];
    }
    async printPdf(ev) {
        /**
         * Generates and displays a PDF report for the bank book.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        ev.preventDefault();
        var self = this;
        let totals = {
            'total_debit':this.state.total_debit,
            'total_debit_display':this.state.total_debit_display,
            'total_credit':this.state.total_credit,
            'total_credit_display':this.state.total_credit_display,
            'currency':this.state.currency,
        }
        var action_title = self.props.action.display_name;
        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.bank_book',
            'report_file': 'dynamic_accounts_report.bank_book',
            'data': {
                'move_lines': self.state.move_line,
                'filters': this.filter(),
                'grand_total': totals,
                'data': self.state.data,
                'total': self.state.total,
                'title': action_title,
                'report_name': self.props.action.display_name
            },
            'display_name': self.props.action.display_name,
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
            else{
                 startDate = new Date(self.state.date_range.start_date);
                 endDate = new Date(self.state.date_range.end_date);
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
        const selectedAccountIDs = Object.values(self.state.selected_account_list);
        const selectedAccountNames = selectedAccountIDs.map((accountID) => {
            const matchingAccount = Object.values(self.state.accounts).find(account => account.id === accountID);
            return matchingAccount ? matchingAccount.display_name : '';
        });
        let filters = {
            'partner': self.state.selected_partner_rec,
            'account': selectedAccountNames,
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
         * Generates and downloads an XLSX report for the bank book.
         */
        var self = this;
        var action_title = self.props.action.display_name;
        let totals = {
            'total_debit':this.state.total_debit,
            'total_debit_display':this.state.total_debit_display,
            'total_credit':this.state.total_credit,
            'total_credit_display':this.state.total_credit_display,
            'currency':this.state.currency,
        }
        var datas = {
            'move_lines': self.state.move_line,
            'data': self.state.data,
            'total': self.state.total,
            'title': action_title,
            'filters': this.filter(),
            'grand_total': totals,
        }
        var action = {
            'data': {
                'model': 'bank.book.report',
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
    async applyFilter(val, ev, is_delete = false) {
        /**
         * Applies filters to the bank book report based on the provided values.
         *
         * @param {any} val - The value of the filter.
         * @param {Event} ev - The event object triggered by the action.
         * @param {boolean} is_delete - Indicates whether the filter value is being deleted.
         * @returns {void}
         */
        let move_line_list = []
        let move_line_value = []
        let move_line_totals = ''
        this.state.move_line = null
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
            } else if (val.target.attributes["data-value"].value === 'draft') {
                if (val.target.classList.contains("selected-filter")) {
                    const { draft, ...updatedAccount } = this.state.options;
                    this.state.options = updatedAccount;
                    val.target.classList.remove("selected-filter");
                } else {
                    this.state.options = {
                        ...this.state.options,
                        'draft': true
                    };
                    val.target.classList.add("selected-filter");
                }
            } else if (val.target.attributes["data-value"].value == 'account') {
                if (!val.target.classList.contains("selected-filter")) {
                    this.state.selected_account_list.push(parseInt(val.target.attributes["data-id"].value, 10))
                    val.target.classList.add("selected-filter");
                } else {
                    const updatedList = this.state.selected_account_list.filter(item => item !== parseInt(val.target.attributes["data-id"].value, 10));
                    this.state.selected_account_list = updatedList
                    val.target.classList.remove("selected-filter");
                }
            }
        }
        let filtered_data = await this.orm.call("bank.book.report", "get_filter_values", [this.state.selected_partner, this.state.date_range, this.state.selected_account_list, this.state.options,]);
        for (const index in filtered_data) {
            const value = filtered_data[index];

            if (index !== 'move_lines_total') {
                move_line_list.push(index);
            } else {
                move_line_totals = value;

                for (const moveLine of Object.values(move_line_totals)) {
                    totalDebitSum += moveLine.total_debit || 0;
                    totalCreditSum += moveLine.total_credit || 0;
                }
            }
        }
        this.state.move_line = move_line_list
        this.state.data = filtered_data
        this.state.total = move_line_totals
        this.state.total_debit = totalDebitSum.toFixed(2)
        this.state.total_credit = totalCreditSum.toFixed(2)
        if (this.unfoldButton.el.classList.contains("selected-filter")) {
              this.unfoldButton.el.classList.remove("selected-filter");
        }
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
BankBook.defaultProps = {
    resIds: [],
};
BankBook.template = 'bnk_b_template_new';
actionRegistry.add("bnk_b", BankBook);
