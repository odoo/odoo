/** @odoo-module **/
import {registry} from "@web/core/registry";
import {Component} from "@odoo/owl";
import {onWillStart, onMounted, useState, useRef, useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class CrmDashboard extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.Leadstage = useRef('leads_stage')
        this.LeadByMonth = useRef('leads_by_month')
        this.CrmActivities = useRef('crm_activities')
        this.LeadByCampaign = useRef('leads_campaign')
        this.LeadByMedium = useRef('leads_medium')
        this.LeadBySource = useRef('leads_source')
        this.LostLead = useRef('leads_lost')
        this.TotalRevenue = useRef('total_revenue')
        this.state = useState({
            period: 'month',
            leads: null,
            opportunities: null,
            exp_revenue: null,
            revenue: null,
            win_ratio: null,
            avg_close_time: null,
            opportunity_ratio: null,
            unassigned_leads: null,
            charts: [],
            upcoming_events: [],
            current_lang: [],
            top_sp_revenue: [],
            country_count: [],
            country_revenue: [],
            recent_activities:[],

        })
        onWillStart(async () => {
            await this.fetch_data();
            await this.UpcomingEvents();
            await this.TopSpRevenue();
            await this.TopCountryRevenue();
            await this.TopCountryCount();
            await this.RecentActivities();
            // Destroy existing chart if it exists

        });

        useEffect(() => {
            if (this.state.charts.length > 0) {
                this.state.charts.forEach(chart => {
                    chart.destroy();
                });
            }
            if (this.state.period) {
                this.fetch_data();
                this.render_leads_by_stage();
                this.render_leads_by_month();
                this.render_crm_activities();
                this.render_lead_by_campaign();
                this.render_lead_by_medium();
                this.render_lead_by_source();
                this.render_lost_lead();
                this.render_total_revenue();
            }
        }, () => [this.state.period]);
    }

    async fetch_data() {
        var self = this
        var result = await this.orm.call('crm.lead', "get_data", [this.state.period])
        this.state.leads = result['leads']
        this.state.opportunities = result['opportunities']
        this.state.exp_revenue = result['exp_revenue']
        this.state.revenue = result['revenue']
        this.state.win_ratio = result['win_ratio']
        this.state.opportunity_ratio = result['opportunity_ratio']
        this.state.avg_close_time = result['avg_close_time']
        this.state.unassigned_leads = result['unassigned_leads']

    }

    async UpcomingEvents() {
        var result = await this.orm.call('crm.lead', "get_upcoming_events", [])
        this.state.upcoming_events = result['event']
        this.state.current_lang = result['cur_lang']
    }

    async TopSpRevenue() {
        var result = await this.orm.call('crm.lead', "get_top_sp_revenue", [this.state.period])
        this.state.top_sp_revenue = result['top_revenue']
        // this.state.current_lang = result['cur_lang']
    }

    async TopCountryCount() {
        var result = await this.orm.call('crm.lead', "get_top_country_count", [this.state.period])
        this.state.country_count = result['country_count']

    }

    async TopCountryRevenue() {
        var result = await this.orm.call('crm.lead', "get_top_country_revenue", [this.state.period])
        this.state.country_revenue = result['country_revenue']
    }
    async RecentActivities() {
        var result = await this.orm.call('crm.lead', "get_recent_activities", [this.state.period])
        this.state.recent_activities = result['activities']
    }


    SetPeriods() {
        var today = new Date();
        var start_date;

        if (this.state.period == 'month') {
            start_date = new Date(today.getFullYear(), today.getMonth(), 1); // Start of the month
        } else if (this.state.period == 'year') {
            start_date = new Date(today.getFullYear(), 0, 1); // Start of the year
        } else if (this.state.period == 'quarter') {
            var startMonth = Math.floor(today.getMonth() / 3) * 3; // Start month of the quarter
            start_date = new Date(today.getFullYear(), startMonth, 1); // Start of the quarter
        } else if (this.state.period == 'week') {
            var dayOfWeek = today.getDay();
            var diff = today.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1); // Adjust when day is Sunday
            start_date = new Date(today.setDate(diff)); // Start of the week (Monday)
        }

        return start_date.getFullYear() + '-' + (start_date.getMonth() + 1).toString().padStart(2, '0') + '-' + start_date.getDate().toString().padStart(2, '0');
    }


    OnChangePeriods() {

    }

    onClickLeads() {
        var date = this.SetPeriods()
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Leads",
            res_model: 'crm.lead',
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
            domain: [['type', '=', 'lead'], ['create_date', '>=', date]]
        });
    }

    onClickOpportunities() {
        var date = this.SetPeriods()
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Opportunities",
            res_model: 'crm.lead',
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
            domain: [['type', '=', 'opportunity'], ['create_date', '>=', date]]
        });
    }

    onClickExpRevenue() {
        var date = this.SetPeriods()
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Expense Revenue",
            res_model: 'crm.lead',
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['type', '=', 'opportunity'], ['active', '=', true], ['create_date', '>=', date]]
        });
    }

    onClickRevenue() {
        var date = this.SetPeriods()
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Revenue",
            res_model: 'crm.lead',
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['type', '=', 'opportunity'], ['active', '=', true], ['stage_id', '=', 4], ['create_date', '>=', date]]
        });
    }

    onClickUnAssignedLeads() {
        var date = this.SetPeriods()
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Unassigned Leads",
            res_model: 'crm.lead',
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['user_id', '=', false], ['type', '=', 'lead'], ['create_date', '>=', date]]
        });
    }

    async render_leads_by_stage() {

        var self = this;
        var ctx = this.Leadstage.el;
        const arrays = await this.orm.call('crm.lead', "get_lead_stage_data", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Leads',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };

        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'polarArea',
            data: data,

            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_leads_by_month() {

        var self = this;
        var ctx = this.LeadByMonth.el;
        const arrays = await this.orm.call('crm.lead', "get_lead_by_month", []);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Leads',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_crm_activities() {

        var self = this;
        var ctx = this.CrmActivities.el;
        const arrays = await this.orm.call('crm.lead', "get_crm_activities", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Activity',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'pie',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_lead_by_campaign() {

        var self = this;
        var ctx = this.LeadByCampaign.el;
        const arrays = await this.orm.call('crm.lead', "get_the_campaign_pie", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Activity',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'pie',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_lead_by_medium() {

        var self = this;
        var ctx = this.LeadByMedium.el;
        const arrays = await this.orm.call('crm.lead', "get_the_medium_pie", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Activity',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'pie',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_lead_by_source() {

        var self = this;
        var ctx = this.LeadBySource.el;
        const arrays = await this.orm.call('crm.lead', "get_the_source_pie", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Activity',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'pie',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_lost_lead() {

        var self = this;
        var ctx = this.LostLead.el;
        const arrays = await this.orm.call('crm.lead', "get_total_lost_crm", [this.state.period]);
        const data = {
            labels: arrays['month'],
            datasets: [{
                label: 'Activity',
                data: arrays['count'],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'bar',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }

    async render_total_revenue() {

        var self = this;
        var ctx = this.TotalRevenue.el;
        const arrays = await this.orm.call('crm.lead', "total_revenue_by_sales", [this.state.period]);
        const data = {
            labels: arrays[1],
            datasets: [{
                label: 'Activity',
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
            }]
        };


        //create Chart class object
        var chart = new Chart(ctx, {
            type: 'pie',
            data: data,
            // options: options
        });
        this.state.charts.push(chart)
    }
}


CrmDashboard.template = 'CrmDashboard'
registry.category("actions").add("crm_dashboard", CrmDashboard)
