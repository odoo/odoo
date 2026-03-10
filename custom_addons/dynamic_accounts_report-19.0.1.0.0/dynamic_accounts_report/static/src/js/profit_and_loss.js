/** @odoo-module **/
const { Component } = owl;
const now = new Date();
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class ProfitAndLoss extends owl.Component {
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
            date_range: null,
            date_from: null,
            date_to: null,
            journal_ids: [],
            account_ids: [],
            analytic_ids: [],
            target_move: 'posted',
        });
        this.wizard_id = await this.orm.call("dynamic.balance.sheet.report", "create", [{}]) | null;
        this.load_data(self.initial_render = true);
    }
    async load_data() {
        /**
         * Loads the data for the profit and loss report.
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
    async print_pdf(ev) {
        /**
         * Generates and displays a PDF report based on the profit and loss data.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        ev.preventDefault();
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0];
        self.state.datas = data[2];
        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-html',
            'report_name': 'dynamic_accounts_report.profit_loss',
            'report_file': 'dynamic_accounts_report.profit_loss',
            'data': {
                'data': self.state,
                'account_ids': self.state.account_ids || [],
                'journal_ids': self.state.journal_ids || [],
                'analytic_ids': self.state.analytic_ids || [],
                'target': self.state.target || "",
                'date_from': self.state.date_from || "",
                'date_to': self.state.date_to || "",
                'date_range': self.state.date_range || "",
                'comparison': self.state.comparison || "",
                'comparison_type': self.state.comparison_type || "",
                'report_name': self.props.action.display_name
            },
            'display_name': self.props.action.display_name,
        });
    }

    _getFilters() {
        const self = this;
        const today = new Date();
        let startDate = null, endDate = null;

        // --- Handle Date Range ---
        if (self.state.date_range) {
            const currentMonth = today.getMonth();
            const currentYear = today.getFullYear();

            switch (self.state.date_range) {
                case 'year':
                    startDate = new Date(currentYear, 0, 1);
                    endDate = new Date(currentYear, 11, 31);
                    break;
                case 'quarter':
                    const currentQuarter = Math.floor(currentMonth / 3);
                    startDate = new Date(currentYear, currentQuarter * 3, 1);
                    endDate = new Date(currentYear, (currentQuarter + 1) * 3, 0);
                    break;
                case 'month':
                    startDate = new Date(currentYear, currentMonth, 1);
                    endDate = new Date(currentYear, currentMonth + 1, 0);
                    break;
                case 'last-month':
                    startDate = new Date(currentYear, currentMonth - 1, 1);
                    endDate = new Date(currentYear, currentMonth, 0);
                    break;
                case 'last-year':
                    startDate = new Date(currentYear - 1, 0, 1);
                    endDate = new Date(currentYear - 1, 11, 31);
                    break;
                case 'last-quarter':
                    const lastQuarter = Math.floor((currentMonth - 3) / 3);
                    startDate = new Date(currentYear, lastQuarter * 3, 1);
                    endDate = new Date(currentYear, (lastQuarter + 1) * 3, 0);
                    break;
            }
        }

        // --- Helper to format date properly ---
        const formatDate = (d) => {
            if (!d) return null;
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${y}-${m}-${day}`;
        };

        // --- Build Filters Dict ---
        return {
            date_range: self.state.date_range || null,
            date_from: formatDate(startDate),
            date_to: formatDate(endDate),
            journal_ids: self.state.journal_ids && self.state.journal_ids.length
                ? self.state.journal_ids.map(j => j.name).join(', ')
                : null,
            account_ids: self.state.account_ids && self.state.account_ids.length
                ? self.state.account_ids.map(a => a.name).join(', ')
                : null,
            analytic_ids: self.state.analytic_ids && self.state.analytic_ids.length
                ? self.state.analytic_ids.map(a => a.name).join(', ')
                : null,
            target: self.state.target_move || 'posted',
            comparison: self.state.comparison || null,
            comparison_type: self.state.comparison_type || null,
        };
    }

    async print_xlsx(ev) {
        /**
         * Generates and downloads an XLSX report based on the profit and loss data.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0];
        self.state.datas = data[2];

        var action = {
            'data': {
                'model': 'dynamic.balance.sheet.report',
                'data': JSON.stringify(self.state),
                'output_format': 'xlsx',
                'report_action': self.props.action.xml_id,
                'report_name': self.props.action.display_name,
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
        self = this;

        // Toggle visual selection
        ev.target.classList.toggle("selected-filter");

        // Extract info from DOM
        const journalId = ev.target.getAttribute("data-id") ||
                          ev.target.querySelector("span")?.getAttribute("data-id");
        const journalName = ev.target.querySelector("span")?.textContent?.trim();

        // Prepare filter for backend
        this.filter = { journal_ids: journalId || journalName };

        // Call backend
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [
            this.wizard_id,
            this.filter,
        ]);

        // Update HTML (if your backend sends updated data)
        ev.delegateTarget.querySelector(".code").innerHTML = res[0].journal_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);

        // ✅ Ensure state array exists
        if (!Array.isArray(self.state.journal_ids)) {
            self.state.journal_ids = [];
        }

        // ✅ Normalize names from res (same logic as accounts)
        const journalNames = (res || [])
            .map(r => (r.journal_ids || []).flat())
            .flat()
            .filter(n => typeof n === "string");

        // ✅ Update state cleanly
        if (ev.target.classList.contains("selected-filter")) {
            for (const jName of journalNames) {
                if (!self.state.journal_ids.includes(jName)) {
                    self.state.journal_ids.push(jName);
                }
            }
        } else {
            self.state.journal_ids = self.state.journal_ids.filter(j => !journalNames.includes(j));
        }

        // ✅ Flatten state in case of any nesting
        self.state.journal_ids = self.state.journal_ids.flat();

    }

    async apply_account(ev) {
        const self = this;

        // Keep existing behavior (toggle + backend call)
        ev.target.classList.toggle("selected-filter");

        const accountId = ev.target.getAttribute("data-id") ||
                          ev.target.querySelector("span")?.getAttribute("data-id") || null;
        const domAccountName = ev.target.querySelector("span")?.textContent?.trim() || null;

        this.filter = { account_ids: accountId || domAccountName };

        // Call backend
        const res = await self.orm.call("dynamic.balance.sheet.report", "filter", [
            this.wizard_id,
            this.filter,
        ]);

        // Update view + reload as before
        try {
            ev.delegateTarget.querySelector(".account").innerHTML = res[0].account_ids;
        } catch (e) {
            // ignore if structure unexpected
        }
        self.initial_render = false;
        self.load_data(self.initial_render);

        // --- Normalization routine ---
        const normalizeAccountNames = (raw) => {
            if (!raw) return [];

            // Case: res is array and first element has account_ids as array or string
            if (Array.isArray(raw)) {
                // try to find the first element that contains 'account_ids'
                const itemWithKey = raw.find(item => item && (item.account_ids !== undefined || item.account_ids !== null));
                const item = itemWithKey || raw[0];

                if (!item) return [];

                const val = item.account_ids !== undefined ? item.account_ids : item;

                // If it's already an array of strings
                if (Array.isArray(val) && val.every(v => typeof v === 'string')) {
                    return val;
                }

                // If it's an array of arrays or objects, attempt to flatten and extract strings
                if (Array.isArray(val)) {
                    const flattened = val.flat(Infinity).filter(v => typeof v === 'string');
                    if (flattened.length) return flattened;
                }

                // If val is an object like {account_ids: ['A']} wrapped, try to extract
                if (typeof val === 'object') {
                    // collect string leaves
                    const collected = [];
                    const collectStrings = (o) => {
                        if (Array.isArray(o)) return o.flat(Infinity).filter(x => typeof x === 'string');
                        if (typeof o === 'object') {
                            Object.values(o).forEach(v => {
                                collectStrings(v).forEach(s => collected.push(s));
                            });
                        }
                        return collected;
                    };
                    collectStrings(val);
                    if (collected.length) return collected;
                }

                // If it's a comma-separated string
                if (typeof val === 'string') {
                    return val.split(',').map(s => s.trim()).filter(Boolean);
                }

                // fallback: flatten raw and extract strings
                const flat = raw.flat(Infinity).filter(x => typeof x === 'string');
                return flat;
            }

            // If raw is an object with account_ids
            if (typeof raw === 'object' && raw.account_ids !== undefined) {
                const v = raw.account_ids;
                if (Array.isArray(v)) return v.filter(x => typeof x === 'string');
                if (typeof v === 'string') return v.split(',').map(s => s.trim()).filter(Boolean);
            }

            // If raw is a string (comma separated names)
            if (typeof raw === 'string') {
                return raw.split(',').map(s => s.trim()).filter(Boolean);
            }

            return [];
        };

        // Use normalization
        const accountNames = normalizeAccountNames(res);

        // If normalization failed (empty), fallback to DOM name
        const finalNames = (accountNames && accountNames.length) ? accountNames : (domAccountName ? [domAccountName] : []);

        // Ensure state array exists and is flat
        if (!Array.isArray(self.state.account_ids)) self.state.account_ids = [];

        if (ev.target.classList.contains("selected-filter")) {
            finalNames.forEach(name => {
                if (!self.state.account_ids.includes(name)) {
                    self.state.account_ids.push(name);
                }
            });
        } else {
            self.state.account_ids = self.state.account_ids.filter(n => !finalNames.includes(n));
        }

        // Keep state flat
        self.state.account_ids = self.state.account_ids.flat();
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
    async apply_analytic_accounts(ev) {
        /**
         * Applies analytic accounts filtering based on the selected option in an event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        self = this;

        // Toggle the 'selected-filter' class on the event target
        ev.target.classList.toggle('selected-filter');

        // Extract the name/id from the DOM
        const analyticName = ev.target.querySelector('span')?.textContent?.trim();
        const analyticId = ev.target.getAttribute('data-id') ||
                           ev.target.querySelector('span')?.getAttribute('data-id');

        // Set the filter object with the 'analytic_ids'
        this.filter = { 'analytic_ids': analyticId || analyticName };

        // Call the backend
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [
            this.wizard_id,
            this.filter,
        ]);

        // Update the HTML with backend response
        ev.delegateTarget.querySelector('.analytic').innerHTML = res[0].analytic_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);

        // ✅ Maintain clean state (non-blocking)
        if (!Array.isArray(self.state.analytic_ids)) {
            self.state.analytic_ids = [];
        }

        // Get analytic names cleanly from backend
        const analyticNames =
            res
                ?.map(r => (r.analytic_ids ? r.analytic_ids : []))
                .flat()
                .filter(Boolean);

        // Update state
        if (ev.target.classList.contains('selected-filter')) {
            analyticNames.forEach(name => {
                if (!self.state.analytic_ids.includes(name)) {
                    self.state.analytic_ids.push(name);
                }
            });
        } else {
            self.state.analytic_ids = self.state.analytic_ids.filter(
                n => !analyticNames.includes(n)
            );
        }
    }

    async apply_entries(ev) {
        /**
         * Applies entries filtering based on the selected option in an event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        self = this;

        // Keep your existing toggle logic intact
        ev.target.classList.add('selected-filter');
        if (ev.target.value === 'draft') {
            this.posted.el.classList.remove('selected-filter');
        } else {
            this.draft.el.classList.remove('selected-filter');
        }

        // Prepare filter object
        this.filter = {
            target: ev.target.value,
        };

        // Backend call (unchanged)
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [
            this.wizard_id,
            this.filter,
        ]);

        // Update DOM
        ev.delegateTarget.querySelector('.target').innerHTML = res[0].target_move;

        // Refresh data
        self.initial_render = false;
        self.load_data(self.initial_render);

        // ✅ Maintain filter state
        if (!self.state.entries) self.state.entries = [];

        const selectedValue = ev.target.value;

        // Since entries are mutually exclusive (posted OR draft)
        self.state.entries = [selectedValue];

    }

    async unfoldAll(ev) {
        /**
         * Unfolds or collapses all elements in a table body based on the given event target's class.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        if (!ev.target.classList.contains("selected-filter")) {
            // Unfold all elements
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                  this.tbody.el.children[length].classList.add('show')
            }
            ev.target.classList.add("selected-filter");
        } else {
            // Collapse all elements
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
                // ✅ store start date in state
                self.state.date_from = ev.target.value

        } else if (ev.target.name === 'end_date') {
                this.filter = {
                    ...this.filter,
                    date_to: ev.target.value
                };
                // ✅ store end date in state
                self.state.date_to = ev.target.value

        } else if (ev.target.attributes["data-value"].value == 'month') {
                this.filter = ev.target.attributes["data-value"].value
                // ✅ store date range type
                self.state.date_range = 'month'

        } else if (ev.target.attributes["data-value"].value == 'year') {
                this.filter = ev.target.attributes["data-value"].value
                self.state.date_range = 'year'

        } else if (ev.target.attributes["data-value"].value == 'quarter') {
            this.filter = ev.target.attributes["data-value"].value
            self.state.date_range = 'quarter'

        } else if (ev.target.attributes["data-value"].value == 'last-month') {
            this.filter = ev.target.attributes["data-value"].value
            self.state.date_range = 'last-month'

        } else if (ev.target.attributes["data-value"].value == 'last-year') {
            this.filter = ev.target.attributes["data-value"].value
            self.state.date_range = 'last-year'

        } else if (ev.target.attributes["data-value"].value == 'last-quarter') {
            this.filter = ev.target.attributes["data-value"].value
            self.state.date_range = 'last-quarter'
        }

        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter]);
        self.initial_render = false;
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
    sumGrossProfit(op_inc, cor) {
        /**
         * Calculates the sum of values in an array of objects by a specified key.
         *
         * @param {Array} data - Array of objects containing numeric values.
         * @param {string} key - The key to access the numeric value in each object.
         * @returns {number} The sum of the numeric values.
         */
         const stringValue = cor;
         const floatValue = parseFloat(stringValue.replace(/,/g, ''));
        return parseFloat(op_inc) + floatValue;
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
ProfitAndLoss.template = 'dfr_template_new';
actionRegistry.add("dfr_n", ProfitAndLoss);
