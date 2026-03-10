/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, useEffect } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");
const today = luxon.DateTime.now();
let monthNamesShort = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

class TrialBalance extends owl.Component {
    async setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.end_date = useRef('date_to');
        this.start_date = useRef('date_from');
        this.period = useRef('periods');
        this.period_year = useRef('period_year');
        this.unfoldButton = useRef('unfoldButton');
        this.state = useState({
            move_line: null,
            default_report: true,
            data: null,
            total: null,
            journals: null,
            accounts: null,
            selected_analytic: [],
            analytic_account: null,
            selected_journal_list: [],
            selected_analytic_account_rec: [],
            date_range: 'month',
            date_type: 'month',
            apply_comparison: false,
            comparison_type: null,
            date_viewed: [],
            comparison_number: null,
            options: null,
            method: {
                        'accural': true
                    },
        });
        this.load_data(self.initial_render = true);

    }
    async load_data() {
        /**
         * Loads the data for the trial balance report.
         */
        let move_line_list = []
        let move_lines_total = ''
        var self = this;
        var action_title = self.props.action.display_name;
        try {
            var self = this;
            var today = new Date();
            var startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            var endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            self.state.data = await self.orm.call("account.trial.balance", "view_report", []);
            self.start_date.el.value = startOfMonth.getFullYear() + '-' + String(startOfMonth.getMonth() + 1).padStart(2, '0') + '-' + String(startOfMonth.getDate()).padStart(2, '0');
            self.end_date.el.value = endOfMonth.getFullYear() + '-' + String(endOfMonth.getMonth() + 1).padStart(2, '0') + '-' + String(endOfMonth.getDate()).padStart(2, '0');
            self.state.date_viewed.push(monthNamesShort[today.getMonth()] + '  ' + today.getFullYear())
            self.state.journals = self.state.data[1]['journal_ids']
            self.state.accounts = self.state.data[0]
            $.each(self.state.data, function (index, value) {
                self.state.journals = value.journal_ids
            })
        }
        catch (el) {
            window.location.href;
        }
    }
    async applyFilter(val, ev, is_delete) {
        /**
         * Asynchronously applies filters and loads data for the trial balance report.
         * Modifies state variables based on the selected filter options.
         * Updates 'move_line_list' and 'move_lines_total'.
         * Sets the start and end date inputs based on selected filter options.
         * Appends the selected date ranges to 'state.date_viewed'.
         * Updates 'state.journals' based on the selected journal filter.
         * Retrieves data using the 'account.trial.balance' API with the selected filter values.
         * Updates 'state.data' with the retrieved data.
         * Handles the comparison logic and updates 'state.date_viewed' accordingly.
         * Reverses the order of 'state.date_viewed' if data exists.
         *
         * @param {any} val - The selected filter value or event.
         * @param {Event} ev - The event object triggered by the filter.
         * @param {boolean} is_delete - Flag indicating if the filter is being deleted.
         * @returns {Promise<void>} Resolves when the filter is applied and data is loaded.
         */
        if (ev && ev.target && ev.target.attributes["data-value"] && ev.target.attributes["data-value"].value == 'no comparison') {
            const lastIndex = this.state.date_viewed.length - 1;
            this.state.date_viewed.splice(0, lastIndex);
        }
        if (ev) {
            if (ev.input && ev.input.attributes.placeholder.value == 'Account' && !is_delete) {
                this.state.selected_analytic.push(val[0].id)
                this.state.selected_analytic_account_rec.push(val[0])
            } else if (is_delete) {
                let index = this.state.selected_analytic_account_rec.indexOf(val)
                this.state.selected_analytic_account_rec.splice(index, 1)
                this.state.selected_analytic = this.state.selected_analytic_account_rec.map((rec) => rec.id)
            }
        }
        else {
            if (val && val.target.name === 'start_date') {
                this.state.date_viewed = []
                this.state.date_viewed.push('From' + ' ' + this.formatDate(this.start_date.el.value) + ' ' + 'To' + ' ' + this.formatDate(this.end_date.el.value))
                this.state.date_range = {
                    ...this.state.date_range,
                    start_date: val.target.value
                };
            } else if (val && val.target.name === 'end_date') {
                this.state.date_viewed = []
                this.state.date_viewed.push('From' + ' ' + this.formatDate(this.start_date.el.value) + 'To' + ' ' + this.formatDate(this.end_date.el.value))
                this.state.date_range = {
                    ...this.state.date_range,
                    end_date: val.target.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'month') {
                this.start_date.el.value = today.startOf('month').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.endOf('month').toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push(today.monthShort + ' ' + today.c.year)
                this.state.date_type = val.target.attributes["data-value"].value
                this.state.comparison_type = this.state.date_type
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'year') {
                this.start_date.el.value = today.startOf('year').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.endOf('year').toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push(today.c.year)
                this.state.date_type = val.target.attributes["data-value"].value
                this.state.comparison_type = this.state.date_type
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'quarter') {
                this.start_date.el.value = today.startOf('quarter').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.endOf('quarter').toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push('Q' + ' ' + today.quarter)
                this.state.comparison_type = this.state.date_type
                this.state.date_type = val.target.attributes["data-value"].value
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'last-month') {
                this.start_date.el.value = today.startOf('month').minus({ days: 1 }).startOf('month').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.startOf('month').minus({ days: 1 }).toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push(today.startOf('month').minus({ days: 1 }).monthShort + ' ' + today.startOf('month').minus({ days: 1 }).c.year)
                this.state.date_type = 'month'
                this.state.comparison_type = this.state.date_type
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'last-year') {
                this.start_date.el.value = today.startOf('year').minus({ days: 1 }).startOf('year').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.startOf('year').minus({ days: 1 }).toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push(today.startOf('year').minus({ days: 1 }).c.year)
                this.state.date_type = 'year'
                this.state.comparison_type = this.state.date_type
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'last-quarter') {
                this.start_date.el.value = today.startOf('quarter').minus({ days: 1 }).startOf('quarter').toFormat('yyyy-MM-dd')
                this.end_date.el.value = today.startOf('quarter').minus({ days: 1 }).toFormat('yyyy-MM-dd')
                this.state.date_viewed = []
                this.state.date_viewed.push('Q' + ' ' + today.startOf('quarter').minus({ days: 1 }).quarter)
                this.state.date_type = 'quarter'
                this.state.comparison_type = this.state.date_type
                this.state.date_range = {
                    start_date: this.start_date.el.value,
                    end_date: this.end_date.el.value
                };
            } else if (val && val.target.attributes["data-value"].value == 'journal') {
                if (!val.target.classList.contains("selected-filter")) {
                    this.state.selected_journal_list.push(parseInt(val.target.attributes["data-id"].value, 10))
                    val.target.classList.add("selected-filter");
                } else {
                    const updatedList = this.state.selected_journal_list.filter(item => item !== parseInt(val.target.attributes["data-id"].value, 10));
                    this.state.selected_journal_list = updatedList
                    val.target.classList.remove("selected-filter");
                }
            } else if (val && val.target.attributes["data-value"].value === 'draft') {
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
            }else if (val.target.attributes["data-value"].value === 'cash-basis') {
                if (val.target.classList.contains("selected-filter")) {
                    const { cash, ...updatedAccount } = this.state.method;
                    this.state.method = updatedAccount;
                    val.target.classList.remove("selected-filter");
                } else {
                    this.state.method = {
                        ...this.state.method,
                        'cash': true
                    };
                    val.target.classList.add("selected-filter");
                }
            }
        }
        if (this.state.apply_comparison == true) {
            if (this.state.comparison_type == 'year') {
                this.state.date_viewed = []
                if (this.start_date.el.value) {
                    var current_year = new Date(this.start_date.el.value).getFullYear();
                    var month = new Date(this.start_date.el.value).getMonth();
                } else {
                    var current_year = new Date(today).getFullYear();
                    var month = new Date(today).getMonth()
                }
                this.state.comparison_number = this.period_year.el.value
                for (var i = this.state.comparison_number; i >= 0; i--) {
                    var date = monthNamesShort[month] + ' ' + (current_year - i);
                    this.state.date_viewed.push(date);
                }
            } else if (this.state.comparison_type == 'month') {
                this.state.date_viewed = []
                this.state.comparison_number = this.period.el.value
            } else if (this.state.comparison_type == 'quarter') {
                this.state.date_viewed = []
                this.state.comparison_number = this.period.el.value
            }
        }
        this.state.data = await this.orm.call("account.trial.balance", "get_filter_values", [this.start_date.el.value, this.end_date.el.value, this.state.comparison_number, this.state.comparison_type, this.state.selected_journal_list, this.state.selected_analytic, this.state.options,this.state.method,]);
        this.state.default_report = false
        var date_viewed = []
        if (date_viewed.length !== 0) {
            this.state.date_viewed = date_viewed.reverse()
        }
    }
    onPeriodChange(ev) {
        /**
         * Event handler for period change.
         * Updates the value of 'period_year' element based on the event target value.
         *
         * @param {Event} ev - Event object triggered by the period change.
         * @returns {void} No explicit return value.
         */
        this.period_year.el.value = ev.target.value
    }
    onPeriodYearChange(ev) {
        /**
         * Event handler for period year change.
         * Updates the value of 'period' element based on the event target value.
         *
         * @param {Event} ev - Event object triggered by the period year change.
         * @returns {void} No explicit return value.
         */
        this.period.el.value = ev.target.value
    }
    applyComparisonPeriod(ev) {
        /**
         * Applies a comparison period and triggers data filtering.
         * Sets 'apply_comparison' flag to true and updates 'comparison_type'.
         * Invokes 'applyFilter' method to apply filters and load data.
         *
         * @param {Event} ev - Event object triggering the comparison period application.
         * @returns {void} No explicit return value.
         */
        this.state.apply_comparison = true
        this.state.comparison_type = this.state.date_type
        this.applyFilter(null, ev)
    }
    applyComparisonYear(ev) {
        /**
         * Applies a comparison year and triggers data filtering.
         * Sets 'apply_comparison' flag to true and updates 'comparison_type' to 'year'.
         * Invokes 'applyFilter' method to apply filters and load data.
         *
         * @param {Event} ev - Event object triggering the comparison year application.
         * @returns {void} No explicit return value.
         */
        this.state.apply_comparison = true
        this.state.comparison_type = 'year'
        this.applyFilter(null, ev)
    }
    sumByKey(data, key) {
        if (!Array.isArray(data)) return 0;
        return data.reduce((acc, item) => {
            let raw = item[key];
            if (typeof raw === 'string') {
                raw = raw.replace(/,/g, ''); // remove commas
            }
            const val = parseFloat(raw);
            return acc + (isNaN(val) ? 0 : val);
        }, 0);
    }
    get comparison_number_range() {
        /**
         * Generates an array of numbers representing a comparison number range.
         * The range includes numbers from 1 up to the 'comparison_number' value in the state.
         *
         * @returns {Array} An array of numbers representing the comparison number range.
         */
        const range = [];
        for (let i = 1; i <= this.state.comparison_number; i++) {
            range.push(i);
        }
        return range;
    }
    async applyComparison(ev) {
        /**
         * Disables comparison mode, resets comparison settings, and triggers data filtering.
         * Sets 'apply_comparison' flag to false and clears 'comparison_type' and 'comparison_number'.
         * Removes all date view entries except the current month/year.
         * Invokes 'applyFilter' method to apply filters and load data.
         *
         * @param {Event} ev - Event object triggering the comparison mode removal.
         * @returns {void} No explicit return value.
         */
        this.state.apply_comparison = false
        this.state.comparison_type = null
        this.state.comparison_number = null
        const lastIndex = this.state.date_viewed.length - 1;
        this.state.date_viewed.splice(0, lastIndex);
        this.applyFilter(null, ev)
    }
    getDomain() {
        return [];
    }
    async printPdf(ev) {
        /**
         * Asynchronously generates and prints a PDF report.
         * Triggers an action to generate a PDF report based on the current state and settings.
         *
         * @param {Event} ev - Event object triggering the PDF report generation.
         * @returns {Promise} A promise that resolves after the PDF report action is triggered.
         */
        ev.preventDefault();
        var self = this;
        var action_title = self.props.action.display_name;
        let comparison_number_range = self.comparison_number_range
        let data_viewed = self.state.date_viewed
        if (self.state.apply_comparison) {
             if (self.comparison_number_range.length > 10) {
                comparison_number_range = self.comparison_number_range.slice(-10);
                data_viewed = self.state.date_viewed.slice(-11);
             }
         }

        // 🔥 Normalize data before sending to QWeb
        let normalizedData = self.state.data;
        if (normalizedData && !Array.isArray(normalizedData)) {
            // case: dict → wrap as [[dict]]
            normalizedData = [[normalizedData]];
        } else if (Array.isArray(normalizedData) && normalizedData.length && !Array.isArray(normalizedData[0])) {
            // case: [dict, dict] → wrap as [[dict, dict]]
            normalizedData = [normalizedData];
        }
        // if already [[dict, dict]], leave as is

        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.trial_balance',
            'report_file': 'dynamic_accounts_report.trial_balance',
            'data': {
                'data': normalizedData,   // ✅ always consistent
                'date_viewed': data_viewed,
                'filters': this.filter(),
                'apply_comparison': self.state.apply_comparison,
                'comparison_number_range': comparison_number_range,
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
        const selectedJournalIDs = Object.values(self.state.selected_journal_list);
        const selectedJournalNames = selectedJournalIDs.map((journalID) => {
          const journal = self.state.journals[journalID];
          return journal ? journal.name : ''; // Return the name if journal exists, otherwise an empty string
        });
        let filters = {
            'journal': selectedJournalNames,
            'account': self.state.selected_analytic_account_rec,
            'options': self.state.options,
            'comparison_type': self.state.comparison_type,
            'comparison_number_range': self.state.comparison_number,
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

    async print_xlsx(ev) {
        ev?.preventDefault && ev.preventDefault();
        const self = this;
        const action_title = self.props.action.display_name;

        // Normalize data like PDF
        let normalizedData = self.state.data;
        if (normalizedData && !Array.isArray(normalizedData)) {
            normalizedData = [[normalizedData]];
        } else if (Array.isArray(normalizedData) && normalizedData.length && !Array.isArray(normalizedData[0])) {
            normalizedData = [normalizedData];
        }

        // Limit comparison range if too long
        let comparison_number_range = self.comparison_number_range;
        let data_viewed = self.state.date_viewed;
        if (self.state.apply_comparison && self.comparison_number_range.length > 10) {
            comparison_number_range = self.comparison_number_range.slice(-10);
            data_viewed = self.state.date_viewed.slice(-11);
        }

        const datas = {
            data: normalizedData,
            date_viewed: data_viewed,
            filters: self.filter(),
            apply_comparison: self.state.apply_comparison,
            comparison_number_range: comparison_number_range,
            title: action_title,
            report_name: action_title,
        };

        const action = {
            data: {
                model: 'account.trial.balance',
                data: JSON.stringify(datas),
                output_format: 'xlsx',
                report_action: self.props.action.xml_id,
                report_name: action_title,
            },
        };

        const block = new BlockUI();

        await download({
            url: '/xlsx_report',
            data: action.data,
            complete: () => block.unblock(),
            error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
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
    formatDate(dateString) {
    /**
     * Formats a date string in "YYYY-MM-DD" format to "DD/MM/YYYY" format.
     *
     * @param {string} dateString - The date string to be formatted.
     * @returns {string} The formatted date in "DD/MM/YYYY" format.
     */
        const date = new Date(dateString);
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
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
            domain: [["account_id", "=", parseInt(ev.target.attributes["data-id"].value, 10)]],
            context: { group_by: ["account_id"] },
            target: "current",
        });
    }
}
TrialBalance.template = 'trl_b_template_new';
actionRegistry.add("trl_b", TrialBalance);