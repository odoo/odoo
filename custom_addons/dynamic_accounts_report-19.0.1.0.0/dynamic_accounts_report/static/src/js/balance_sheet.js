/** @odoo-module **/
const { Component } = owl;
const now = new Date();
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class BalanceSheet extends owl.Component {
    async setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.posted = useRef('posted');
        this.period = useRef('periods');
        this.period_year = useRef('period_year');
        this.draft = useRef('draft');
        this.state = useState({
            data: null,
            filter_data: null,
            year : [now.getFullYear()],
            comparison: false,
            comparison_type: null,
        });
        this.wizard_id = await this.orm.call("dynamic.balance.sheet.report", "create", [{}]) | null;
        this.load_data(self.initial_render = true);
    }
    async load_data() {
    /**
     * Loads the data for the balance sheet report.
     */
        var self = this;
        var action_title = self.props.action.display_name;
        try {
            var self = this;
            let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
            self.state.data = data[0]
            self.state.datas = data[2]
            self.state.filter_data = data[1]
            self.state.title = action_title
        }
        catch (el) {
            window.location.href
        }
    }
    async show_gl(ev) {
    /**
        * Shows the General Ledger view by triggering an action.
        *
        * @param {Event} ev - The event object triggered by the action.
        * @returns {Promise} - A promise that resolves to the result of the action.
        */
        return this.action.doAction({
            type: 'ir.actions.client',
            name: 'General Ledger',
            tag: 'gen_l',
        });
    }
    async print_pdf(ev) {
        /**
        * Print PDF Method
        * This method is triggered when the "Print PDF" button is clicked.
        * It retrieves the report data and performs an action to generate and download a PDF report.
        */
        ev.preventDefault();
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0]
        self.state.datas = data[2]
        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.balance_sheet',
            'report_file': 'dynamic_accounts_report.balance_sheet',
            'data': {
                'data': self.state,
                'report_name': self.props.action.display_name
            },
            'display_name': self.props.action.display_name,
        });
    }
    async print_xlsx(ev) {
         /**
         * Generates and downloads an XLSX report based on the profit and loss data.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0]
        self.state.datas = data[2]
        var action = {
            'data': {
                'model': 'dynamic.balance.sheet.report',
                'data': JSON.stringify(self.state),
                'output_format': 'xlsx',
                'report_name': self.props.action.display_name,
                'report_action': self.props.action.xml_id,
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
    async apply_journal(ev) {
     /**
        * Applies journal filtering based on the selected option in an event target.
        *
        * @param {Event} ev - The event object triggered by the action.
        */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'journal_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.code').innerHTML = res[0].journal_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_account(ev) {
     /**
        * Applies account filtering based on the selected option in an event target.
        *
        * @param {Event} ev - The event object triggered by the action.
        */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'account_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.account').innerHTML = res[0].account_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_analytic_accounts(ev) {
    /**
     * Applies analytic accounts filtering based on the selected option in an event target.
     *
     * @param {Event} ev - The event object triggered by the action.
     */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'analytic_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.analytic').innerHTML = res[0].analytic_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_entries(ev) {
    /**
     * Applies the selected entries filter and triggers data loading based on the selected filter class.
     * @param {Event} ev - The event object triggered by the entries filter selection.
     * @returns {Promise<void>} - A promise that resolves when the data is loaded.
     */
        self = this;
        ev.target.classList.add('selected-filter')
        if (ev.target.value == 'draft') {
            this.posted.el.classList.remove('selected-filter')
        } else {
            this.draft.el.classList.remove('selected-filter')
        }
        this.filter = ({
            'target': ev.target.value
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.target').innerHTML = res[0].target_move;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async unfoldAll(ev) {
    /**
     * Unfolds or collapses all table rows based on the selected filter class.
     * @param {Event} ev - The event object triggered by the unfolding action.
     * @returns {void}
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
    async apply_date(ev){
    /**
     * Applies the selected date filter and triggers data loading based on the selected filter value.
     * @param {Event} ev - The event object triggered by the date selection.
     * @returns {Promise<void>} - A promise that resolves when the data is loaded.
     */
        self = this
        if (ev.target.name === 'start_date') {
                this.filter = {
                    ...this.filter,
                    date_from: ev.target.value
                };
        } else if (ev.target.name === 'end_date') {
                this.filter = {
                    ...this.filter,
                    date_to: ev.target.value
                };
        } else if (ev.target.attributes["data-value"].value == 'month') {
                this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'year') {
                this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'quarter') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-month') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-year') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-quarter') {
            this.filter = ev.target.attributes["data-value"].value
        }
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter]);
        self.initial_render = false;
        self.load_data(self.initial_render);
        this.load_data(this.initial_render);
    }
    onPeriodChange(ev){
        this.period_year.el.value = ev.target.value
    }
    onPeriodYearChange(ev){
        this.period.el.value = ev.target.value
    }
    async applyComparisonPeriod(){
        this.state.comparison  = this.period.el.value
        this.state.comparison_type = "month"
        let monthNamesShort = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ]
        let res = await this.orm.call("dynamic.balance.sheet.report", "comparison_filter", [this.wizard_id, this.state.comparison]);
        this.state.year = [monthNamesShort[now.getMonth()]+'  ' + now.getFullYear()]
        for (var length = 0; length < res.length; length++) {
                const dateObject = new Date(res[length]['date_to']);
                this.state.year.push(monthNamesShort[dateObject.getMonth()]+'  ' + dateObject.getFullYear())
            }
        this.load_data(self.initial_render);
    }
    async applyComparisonYear(){
        this.state.comparison = this.period_year.el.value
        this.state.comparison_type = "year"
        let res = await this.orm.call("dynamic.balance.sheet.report", "comparison_filter_year", [this.wizard_id, this.state.comparison]);
        this.state.year = [now.getFullYear()]
        for (var length = 0; length < res.length; length++) {
                const dateObject = new Date(res[length]['date_to']);
                this.state.year.push(dateObject.getFullYear())
            }
        this.load_data(self.initial_render);
    }
    apply_comparison() {
        this.state.comparison = false
        this.state.comparison_type = null
        this.state.year = [now.getFullYear()]
    }

}
BalanceSheet.template = 'bls_template_new';
actionRegistry.add("bl_s", BalanceSheet);