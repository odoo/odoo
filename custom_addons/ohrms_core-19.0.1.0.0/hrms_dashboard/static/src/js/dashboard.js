/** @odoo-module **/
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { onMounted, Component, useRef } from "@odoo/owl";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";
const actionRegistry = registry.category("actions");
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";
export class HrDashboard extends Component{
    static template = 'HrDashboardMain';
    static props = ["*"];
    setup() {
        this.effect = useService("effect");
        this.action = useService("action");
        this.log_in_out = useRef("log_in_out")
        this.emp_graph = useRef("emp_graph")
        this.leave_graph = useRef("leave_graph")
        this.join_resign_trend = useRef("join_resign_trend")
        this.attrition_rate = useRef("attrition_rate")
        this.leave_trend = useRef("leave_trend")
        this.orm = useService("orm");
        this.state = useState({
            is_manager: false,
            date_range: 'week',
            dashboards_templates: ['LoginEmployeeDetails','ManagerDashboard', 'EmployeeDashboard'],
            employee_birthday: [],
            upcoming_events: [],
            announcements: [],
            login_employee: [],
            templates: [],
        })
        onWillStart(async () => {
            this.isHrManager = await user.hasGroup("hr.group_hr_manager");
            this.state.login_employee = {}
            if ( await this.orm.call('hr.employee', 'check_user_group', []) ) {
                this.state.is_manager = true
            }
            else {
                this.state.is_manager = false
            }
            var empDetails = await this.orm.call('hr.employee', 'get_user_employee_details', [])
            if ( empDetails ){
                this.state.login_employee = empDetails[0]
            }
            var res = await this.orm.call('hr.employee', 'get_upcoming', [])
            if ( res ) {
                this.state.employee_birthday = res['birthday'];
                this.state.upcoming_events = res['event'];
                this.state.announcements = res['announcement'];
            }
            var projectTaskDetails = await this.orm.call('hr.employee', 'get_employee_project_tasks', [])
            if (projectTaskDetails) {
                this.state.login_employee['project_task_lines'] = projectTaskDetails;
            }
        });
        onMounted(() => {
            this.title = 'Dashboard'
            this.render_graphs();
        });
    }
    add_project_task() {
            console.log("add_project_task:", user)
                this.action.doAction({
                    name: _t("Project Task"),
                    type: 'ir.actions.act_window',
                    res_model: 'project.task',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        'default_user_ids': [user.userId]
                    }
                });
            }
    view_project_tasks() {
                this.action.doAction({
                    name: _t("My Tasks"),
                    type: 'ir.actions.act_window',
                    res_model: 'project.task',
                    view_mode: 'tree,form,kanban',
                    views: [[false, 'list'],[false, 'form'],[false, 'kanban']],
                    domain: [['user_ids','in', session.uid]],
                    target: 'current'
                });
            }
    render_graphs(){
        var self = this;
        if (this.state.login_employee){
            if (this.state.is_manager) {
             self.render_department_employee();
                self.render_leave_graph();
                self.update_join_resign_trends();
                self.update_monthly_attrition();
            }
            self.update_leave_trend();
            self.render_employee_skill();
        }
    }
    async render_department_employee() {
        const colors = [
            '#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999',
            '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433',
            '#ffc25b', '#f8e54b'
        ];
        const data = await this.orm.call('hr.employee', 'get_dept_employee', []);
        if (data) {
            const labels = data.map(d => d.label);
            const values = data.map(d => d.value);
            const pieCtx = document.getElementById('employeePieChart').getContext('2d');
            const pieChart = new Chart(pieCtx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'right',
                            labels: {
                                color: 'black',
                                usePointStyle: true,
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const percentage = (value / values.reduce((a, b) => a + b, 0) * 100).toFixed(2);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    async render_leave_graph() {
        const colors = [
            '#ffbf00','#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999',
            '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433',
            '#ffc25b', '#f8e54b'
        ];
        const data = await this.orm.call('hr.employee', 'get_department_leave', []);
        if (data) {
            const fData = data[0];
            const dept = data[1];
            const id = this.leave_graph.el;
            const barColor = '#ff618a';
            fData.forEach(function (d) {
                let total = 0;
                for (const dpt in dept) {
                    total += d.leave[dept[dpt]];
                }
                d.total = total;
            });
            const labels = fData.map(d => d.l_month);
             const barData = fData.map(d => d.total);
            const barCtx = document.getElementById('leave_barChart').getContext('2d');
            const barChart = new Chart(barCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Leaves',
                        data: barData,
                        backgroundColor: barColor,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const st = fData[context.dataIndex];
                                    const nD = Object.keys(st.leave).map(key => ({
                                        type: key,
                                        leave: st.leave[key]
                                    }));
                                    updatePieChart(nD);
                                    return `Total: ${context.raw}`;
                                }
                            }
                        }
                    }
                }
            });
             const pieData = dept.map(d => ({
                type: d,
                leave: fData.reduce((acc, t) => acc + (t.leave[d] || 0), 0)
            }));
            const pieCtx = document.getElementById('leave_doughnutChart').getContext('2d');
            const pieChart = new Chart(pieCtx, {
                type: 'doughnut',
                data: {
                    labels: pieData.map(d => d.type),
                    datasets: [{
                        data: pieData.map(d => d.leave),
                        backgroundColor: colors,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const percentage = (value / d3.sum(pieData.map(d => d.leave)) * 100).toFixed(2);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
            function updatePieChart(newData) {
                pieChart.data.datasets[0].data = newData.map(d => d.leave);
                pieChart.data.labels = newData.map(d => d.type);
                pieChart.update();
            }
        }
    }
    async update_join_resign_trends() {
        const colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        const data = await this.orm.call('hr.employee', 'join_resign_trends', []);
        if (data) {
            const labels = data[0].values.map(d => d.l_month);
            const datasets = data.map((dataset, index) => ({
                label: dataset.name,
                data: dataset.values.map(d => d.count),
                borderColor: colors[index % colors.length],
                fill: false,
                tension: 0.1,
                borderWidth: 2
            }));
            const ctx = document.getElementById('lineChart').getContext('2d');
            const lineChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            labels: {
                                color: 'black'
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'category',
                            title: {
                                display: true,
                                text: 'Month'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Count'
                            }
                        }
                    }
                }
            });
        }
    }
    async update_monthly_attrition() {
        const colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_attrition_rate', []);
        if (data) {
            const labels = data.map(d => d.month);
            const attritionData = data.map(d => d.attrition_rate);
            const ctx = document.getElementById('attritionRateChart').getContext('2d');
            const attritionRateChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Attrition Rate',
                        data: attritionData,
                        backgroundColor: colors[0],
                        borderColor: colors[0],
                        fill: false,
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    }]
                },
                options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `Attrition Rate: ${context.raw}`;
                                }
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: 'black'
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Month'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Attrition Rate'
                            }
                        }
                    }
                }
            });
        }
    }
    async update_leave_trend() {
        const data = await this.orm.call('hr.employee', 'employee_leave_trend', []);
        if (data) {
            const labels = data.map(d => d.l_month);
            const leaveData = data.map(d => d.leave);
            const ctx = document.getElementById('leaveTrendChart').getContext('2d');
            const leaveTrendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Leaves Taken',
                        data: leaveData,
                        backgroundColor: 'rgba(70, 140, 193, 0.4)',
                        borderColor: 'rgba(70, 140, 193, 1)',
                        fill: true,
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `Leaves: ${context.raw}`;
                                }
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: 'black'
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Month'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Leaves'
                            }
                        }
                    }
                }
            });
        }
    }
    async render_employee_skill() {
        const colors = ['#ff6384','#4bc0c0','#ffcd56','#c9cbcf','#36a2eb', '#659d4e', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_employee_skill', []);
        if (data) {
            const labels = data.map(d => d.skills);
            const skillData = data.map(d => d.progress);
            const ctx = document.getElementById('skillChart').getContext('2d');
            const skillChart = new Chart(ctx, {
                type: 'polarArea',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Skill ',
                        data: skillData,
                        backgroundColor: colors,
                        borderColor: ['white'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `Skill: ${context.raw}`;
                                }
                            }
                        },
                        legend: {
                            display: true,
                            position: 'right',
                            labels: {
                                color: 'black'
                            }
                        }
                    },
                   scales: {
                    r: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
            });
        }
    }
    // EVENT METHODS
    add_attendance() {
        this.action.doAction({
            name: _t("Attendances"),
            type: 'ir.actions.act_window',
            res_model: 'hr.attendance',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new'
        });
    }
    add_leave() {
        this.action.doAction({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new'
        });
    }
    add_leave() {
        this.action.doAction({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new'
        });
    }
    add_expense() {
        this.action.doAction({
            name: _t("Expense"),
            type: 'ir.actions.act_window',
            res_model: 'hr.expense',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new'
        });
    }
    leaves_to_approve() {
        this.action.doAction({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['confirm','validate1']]],
            target: 'current'
        });
    }
    leave_allocations_to_approve() {
        this.action.doAction({
            name: _t("Leave Allocation Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave.allocation',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['confirm', 'validate1']]],
            target: 'current'
        })
    }
    job_applications_to_approve(){
        this.action.doAction({
            name: _t("Applications"),
            type: 'ir.actions.act_window',
            res_model: 'hr.applicant',
            view_mode: 'tree,kanban,form,pivot,graph,calendar',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form'],
                    [false, 'pivot'],[false, 'graph'],[false, 'calendar']],
            context: {},
            target: 'current'
        })
    }
    leaves_request_today() {
        var date = new Date();
        this.action.doAction({
            name: _t("Leaves Today"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['date_from','<=', date], ['date_to', '>=', date], ['state','=','validate']],
            target: 'current'
        })
    }
    leaves_request_month() {
        var date = new Date();
        var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        var fday = firstDay.toJSON().slice(0,10).replace(/-/g,'-');
        var lday = lastDay.toJSON().slice(0,10).replace(/-/g,'-');
        this.action.doAction({
            name: _t("This Month Leaves"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['date_from','>', fday],['state','=','validate'],['date_from','<', lday]],
            target: 'current'
        })
    }
    hr_payslip() {
        this.action.doAction({
            name: _t("Employee Payslips"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['employee_id','=', this.state.login_employee.id]],
            target: 'current'
        });
    }
   async hr_contract() {
        console.log("this:", this)
        if (this.isHrManager) {

            // Call the Python function to get the view ID
            const view_id = await this.orm.call(
                'hr.version',
                'get_hr_version_list_view_id',
                []
            );
            this.action.doAction({
                name: _t("Contracts"),
                type: 'ir.actions.act_window',
                res_model: 'hr.version',
                view_mode: 'tree,form,graph,pivot',
                views: [
                    [view_id, 'list'],
                    [false, 'graph'],
                    [false, 'pivot'],
                ],
                context: {
                    'search_default_employee_id': this.state.login_employee.id,
                },
                target: 'current'
            });
        }
   }

    hr_timesheets() {
        this.action.doAction({
            name: _t("Timesheets"),
            type: 'ir.actions.act_window',
            res_model: 'account.analytic.line',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            context: {
                'search_default_month': true,
            },
            domain: [['employee_id','=', this.state.login_employee.id]],
            target: 'current'
        })
    }
    employee_broad_factor() {
        var today = new Date();
        var dd = String(today.getDate()).padStart(2, '0');
        var mm = String(today.getMonth() + 1).padStart(2, '0');
        var yyyy = today.getFullYear();
        this.action.doAction({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['validate']],['employee_id','=', this.state.login_employee.id],['date_to','<=',today]],
            target: 'current',
            context:{'order':'duration_display'}
        })
    }
     attendance_sign_in_out() {
        if (this.state.login_employee['attendance_state'] == 'checked_out') {
            this.state.login_employee['attendance_state'] = 'checked_in'
        }
        else{
            if (this.state.login_employee['attendance_state'] == 'checked_in') {
                this.state.login_employee['attendance_state'] = 'checked_out'
            }
        }
        this.update_attendance()
    }
    async update_attendance() {
        var self = this;
        var result = await this.orm.call('hr.employee', 'attendance_manual',[[this.state.login_employee.id]])
        if (result) {
            var attendance_state = this.state.login_employee.attendance_state;
            var message = ''
            if (attendance_state == 'checked_in'){
                message = 'Checked In'
                this.env.bus.trigger('signin_signout', {
                    mode: "checked_in",
                });
            }
            else if (attendance_state == 'checked_out'){
                message = 'Checked Out'
                this.env.bus.trigger('signin_signout', {
                    mode: false,
                });
            }
            this.effect.add({
                message: _t("Successfully " + message),
                type: 'rainbow_man',
                fadeout: "fast",
            })
        }
    }
}
registry.category("actions").add("hr_dashboard", HrDashboard)

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        var self = this
        onMounted(() => {
            this.env.bus.addEventListener('signin_signout', ({
                detail
            }) => {
                if (detail.mode == 'checked_in') {
                    self.state.checkedIn = detail.mode
                } else {
                    self.state.checkedIn = false
                }
            })
        })
    },
})
