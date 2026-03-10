/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
import { formatFloat } from "@web/core/utils/numbers";
const actionRegistry = registry.category("actions");
const today = luxon.DateTime.now();

class AgedReceivable extends owl.Component {
    async setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.date_range = useRef('date_to');
        this.unfoldButton = useRef('unfoldButton');
        this.state = useState({
            move_line: null,
            data: null,
            total: null,
            currency: null,
            total_debit: null,
            diff0_sum: null,
            diff1_sum: null,
            diff2_sum: null,
            diff3_sum: null,
            diff4_sum: null,
            diff5_sum: null,
            selected_partner: [],
            selected_partner_rec: [],
        });
        this.load_data(self.initial_render = true);
    }
    async load_data() {
        /**
         * Loads the data for the bank book report.
         */
        let move_line_list = [];
        let move_lines_total = '';
        let diff0Sum = 0;
        let diff1Sum = 0;
        let diff2Sum = 0;
        let diff3Sum = 0;
        let diff4Sum = 0;
        let diff5Sum = 0;
        let TotalDebit = 0;
        let currency;
        var self = this;
        var action_title = self.props.action.display_name;
        try {
            self.state.data = await self.orm.call("age.receivable.report", "view_report", []);
            for (const index in self.state.data) {
                const value = self.state.data[index];
                if (index !== 'partner_totals') {
                    move_line_list.push(index);
                } else {
                    move_lines_total = value;
                    for (const moveLine of Object.values(move_lines_total)) {
                        currency = moveLine.currency_id;
                        // Use raw values for summation
                        diff0Sum += moveLine.diff0_sum || 0;
                        diff1Sum += moveLine.diff1_sum || 0;
                        diff2Sum += moveLine.diff2_sum || 0;
                        diff3Sum += moveLine.diff3_sum || 0;
                        diff4Sum += moveLine.diff4_sum || 0;
                        diff5Sum += moveLine.diff5_sum || 0;
                        TotalDebit += moveLine.debit_sum || 0;
                    }
                }
            }
            self.state.move_line = move_line_list;
            self.state.total = move_lines_total;
            self.state.currency = currency;
            self.state.total_debit = TotalDebit;
            self.state.diff0_sum = diff0Sum;
            self.state.diff1_sum = diff1Sum;
            self.state.diff2_sum = diff2Sum;
            self.state.diff3_sum = diff3Sum;
            self.state.diff4_sum = diff4Sum;
            self.state.diff5_sum = diff5Sum;
            // Format totals for display
            self.state.total_debit_display = formatFloat(TotalDebit, { digits: [0, 2] });
            self.state.diff0_sum_display = formatFloat(diff0Sum, { digits: [0, 2] });
            self.state.diff1_sum_display = formatFloat(diff1Sum, { digits: [0, 2] });
            self.state.diff2_sum_display = formatFloat(diff2Sum, { digits: [0, 2] });
            self.state.diff3_sum_display = formatFloat(diff3Sum, { digits: [0, 2] });
            self.state.diff4_sum_display = formatFloat(diff4Sum, { digits: [0, 2] });
            self.state.diff5_sum_display = formatFloat(diff5Sum, { digits: [0, 2] });
        } catch (el) {
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
            domain: [["partner_id", "=", parseInt(ev.target.attributes["data-id"].value, 10)], ['account_type', 'in', ['asset_receivable']]],
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
    async unfoldAll(ev) {
        /**
         * Unfolds all items in the table body if the event target does not have the 'selected-filter' class,
         * or folds all items if the event target has the 'selected-filter' class.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        if (!ev.target.classList.contains("selected-filter")) {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                 this.tbody.el.children[length].classList.add('show');
            }
            ev.target.classList.add("selected-filter");
        } else {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                this.tbody.el.children[length].classList.remove('show')
            }
            ev.target.classList.remove("selected-filter");
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
        var self = this;
        var action_title = self.props.action.display_name;
        let totals = {
            'diff0_sum':this.state.diff0_sum,
            'diff0_sum_display':this.state.diff0_sum_display,
            'diff1_sum':this.state.diff1_sum,
            'diff1_sum_display':this.state.diff1_sum_display,
            'diff2_sum':this.state.diff2_sum,
            'diff2_sum_display':this.state.diff2_sum_display,
            'diff3_sum':this.state.diff3_sum,
            'diff3_sum_display':this.state.diff3_sum_display,
            'diff4_sum':this.state.diff4_sum,
            'diff4_sum_display':this.state.diff4_sum_display,
            'diff5_sum':this.state.diff5_sum,
            'diff5_sum_display':this.state.diff5_sum_display,
            'total_debit':this.state.total_debit,
            'total_debit_display':this.state.total_debit_display,
            'currency':this.state.currency,
        }
        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.aged_receivable',
            'report_file': 'dynamic_accounts_report.aged_receivable',
            'data': {
                'move_lines': self.state.move_line,
                'data': self.state.data,
                'total': self.state.total,
                'filters': this.filter(),
                'grand_total': totals,
                'title': action_title,
                'report_name': self.props.action.display_name
            },
            'display_name': self.props.action.display_name,
        });
    }
    filter() {
        let filters = {
            'partner': this.state.selected_partner_rec,
            'end_date': this.date_range.el.value,
        };
        return filters
    }
    async print_xlsx() {
        /**
         * Generates and downloads an XLSX report for the partner ledger.
         */
        var self = this;
        var action_title = self.props.action.display_name;
        let totals = {
            'diff0_sum':this.state.diff0_sum,
            'diff1_sum':this.state.diff1_sum,
            'diff2_sum':this.state.diff2_sum,
            'diff3_sum':this.state.diff3_sum,
            'diff4_sum':this.state.diff4_sum,
            'diff5_sum':this.state.diff5_sum,
            'total_debit':this.state.total_debit,
        }
        var datas = {
            'move_lines': self.state.move_line,
            'data': self.state.data,
            'total': self.state.total,
            'filters': this.filter(),
            'grand_total': totals,
            'title': action_title,
        }
        var action = {
            'data': {
                'model': 'age.receivable.report',
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
    async applyFilter(ev, e, is_delete = false) {
        let move_line_list = []
        let move_lines_total = ''
        let diff0Sum = 0;
        let diff1Sum = 0;
        let diff2Sum = 0;
        let diff3Sum = 0;
        let diff4Sum = 0;
        let diff5Sum = 0;
        let TotalDebit = 0;
        if (ev.target && ev.target.attributes["data-value"]) {
            if (ev.target.attributes["data-value"].value == 'today') {
                this.date_range.el.value = today.toFormat('yyyy-MM-dd')
            } else if (ev.target.attributes["data-value"].value == 'last-month-end') {
                this.date_range.el.value = today.startOf('month').minus({ days: 1 }).toFormat('yyyy-MM-dd')
            } else if (ev.target.attributes["data-value"].value == 'last-quarter-end') {
                this.date_range.el.value = today.startOf('quarter').minus({ days: 1 }).toFormat('yyyy-MM-dd')
            } else if (ev.target.attributes["data-value"].value == 'last-year-end') {
                this.date_range.el.value = today.startOf('year').minus({ days: 1 }).toFormat('yyyy-MM-dd')
            }
        } else if (e && e.input && e.input.attributes.placeholder.value == 'Partner' && !is_delete) {
            this.state.selected_partner.push(ev[0].id)
            this.state.selected_partner_rec.push(ev[0])
        } else if (is_delete) {
            let index = this.state.selected_partner_rec.indexOf(ev)
            this.state.selected_partner_rec.splice(index, 1)
            this.state.selected_partner = this.state.selected_partner_rec.map((rec) => rec.id)
        }
        let filtered_data = await this.orm.call("age.receivable.report", "get_filter_values", [this.date_range.el.value, this.state.selected_partner,]);
        for (const index in filtered_data) {
            const value = filtered_data[index];
            if (index !== 'partner_totals') {
                move_line_list.push(index);
            } else {
                move_lines_total = value;
                for (const moveLine of Object.values(move_lines_total)) {
                    diff0Sum += moveLine.diff0_sum || 0;
                    diff1Sum += moveLine.diff1_sum || 0;
                    diff2Sum += moveLine.diff2_sum || 0;
                    diff3Sum += moveLine.diff3_sum || 0;
                    diff4Sum += moveLine.diff4_sum || 0;
                    diff5Sum += moveLine.diff5_sum || 0;
                    TotalDebit += moveLine.debit_sum || 0;
                }
            }
        }
        this.state.data = filtered_data
        this.state.move_line = move_line_list
        this.state.total = move_lines_total
        this.state.total_debit = TotalDebit
        this.state.diff0_sum = diff0Sum
        this.state.diff1_sum = diff1Sum
        this.state.diff2_sum = diff2Sum
        this.state.diff3_sum = diff3Sum
        this.state.diff4_sum = diff4Sum
        this.state.diff5_sum = diff5Sum
    }
    getDomain() {
        return [];
    }
}
AgedReceivable.template = 'age_r_template_new';
AgedReceivable.defaultProps = {
    resIds: [],
};
actionRegistry.add("age_r", AgedReceivable);
