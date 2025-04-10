/** @odoo-module */

import {Field} from '@web/views/fields/field';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { onEmployeeSubRedirect } from './hooks';

const { Component, onWillStart, onWillUpdateProps, onPatched, useState, useRef, onMounted } = owl;

function useUniquePopover() {
    const popover = usePopover();
    let remove = null;
    return Object.assign(Object.create(popover), {
        add(target, component, props, options) {
            if (remove) {
                remove();
            }
            remove = popover.add(target, component, props, options);
            return () => {
                remove();
                remove = null;
            };
        },
    });
}

class HrOrgChartPopover extends Component {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();
    }

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }
}
HrOrgChartPopover.template = 'hr_org_chart.hr_orgchart_emp_popover';

export class HrOrgChart extends Field {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.popover = useUniquePopover();

        this.jsonStringify = JSON.stringify;

        this.state = useState({'employee_id': null});
        this.lastParent = null;
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();

        this.isScrollable = false;
        this.maxDisplayedEmployees = 7;
        this.orgChartRef = useRef("org_chart");
        this.scrollUpBtn = useRef("scroll_up_btn");
        this.scrollDownBtn = useRef("scroll_down_btn");

        onWillStart(async () => {
            this.employee = this.props.record.data;
            // the widget is either dispayed in the context of a hr.employee form or a res.users form
            this.state.employee_id = this.employee.employee_ids !== undefined ? this.employee.employee_ids.resIds[0] : this.employee.id;
            const parentId = (this.employee.parent_id && this.employee.parent_id[0]) ? this.employee.parent_id[0] : false;
            const forceReload = this.lastRecord !== this.props.record || this.lastParent != parentId;
            this.lastParent = parentId;
            this.lastRecord = this.props.record;
            await this.fetchEmployeeData(this.state.employee_id, parentId, forceReload);
        });

        onMounted(this.handleComponentUpdate.bind(this))

        onWillUpdateProps(async (nextProps) => {
            const newParentId = (nextProps.record.data.parent_id && nextProps.record.data.parent_id[0])
            ? nextProps.record.data.parent_id[0] : false;
            if(this.lastParent !== newParentId){
                await this.fetchEmployeeData(this.state.employee_id, newParentId, true);
            }
            this.lastParent = newParentId;
        })

        onPatched(this.handleComponentUpdate.bind(this))
    }

    handleComponentUpdate(){
        if(this.managers || this.children){
            const entries = document.querySelectorAll(".o_org_chart_entry");
            if(this.isScrollable){
                this.scrollUpBtn.el.style.visibility = "visible";
                this.scrollDownBtn.el.style.visibility = "visible";
                if(!this.managers_more){
                    this.scrollUpBtn.el.style.visibility = "hidden";
                }
                if(this.managers.length - this.excess_managers_count + 1 + this.children.length <= this.maxDisplayedEmployees){
                    this.scrollDownBtn.el.style.visibility = "hidden";
                }
            }
            if(entries.length === 0){
                this.orgChartRef.el.setAttribute("style",`max-height:none;`);
                return;
            }
            let maxAllowedEntriesHeight = 0;
            for(let i = this.excess_managers_count;i < Math.min(this.maxDisplayedEmployees + this.excess_managers_count, entries.length);i++){
                maxAllowedEntriesHeight += entries[i].getBoundingClientRect().height;
            }
            const entryHeight = entries[0].getBoundingClientRect().height;
            this.orgChartRef.el.setAttribute("style",`max-height:${maxAllowedEntriesHeight}px;`);
            this.orgChartRef.el.scrollTop = entryHeight * this.excess_managers_count;
        }
    }

    async fetchEmployeeData(employeeId, newParentId = null, force = false) {
        if (!employeeId) {
            this.managers = [];
            this.children = [];
            if (this.view_employee_id) {
                this.render(true);
            }
            this.view_employee_id = null;
        } else if (employeeId !== this.view_employee_id || force) {
            this.view_employee_id = employeeId;
            var orgData = await this.rpc(
                '/hr/get_org_chart',
                {
                    employee_id: employeeId,
                    new_parent_id: newParentId,
                    context: Component.env.session.user_context,
                }
            );
            if (Object.keys(orgData).length === 0) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            this.managers = orgData.managers;
            this.children = orgData.children;
            this.managers_more = orgData.managers_more;
            this.self = orgData.self;
            this.excess_managers_count = orgData.excess_managers_count;
            this.isScrollable = this.managers.length > 0 || this.children.length > 0;
        }
    }

    _onOpenPopover(event, employee) {
        this.popover.add(
            event.currentTarget,
            this.constructor.components.Popover,
            {employee},
            {closeOnClickAway: true}
        );
    }

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }

    _onScrollUp() {
        if(this.isScrollable){
            const orgCharEntry = document.querySelector(".o_org_chart_entry");
            const entryHeight = orgCharEntry.getBoundingClientRect().height;
            this.orgChartRef.el.scrollTop -= entryHeight;
            this.scrollDownBtn.el.style.visibility = "visible";
            if(this.orgChartRef.el.scrollTop <= entryHeight){
                this.scrollUpBtn.el.style.visibility = "hidden";
            }
        }
    }

    _onScrollDown() {
        if(this.isScrollable){
            const orgCharEntry = document.querySelector(".o_org_chart_entry");
            const entryHeight = orgCharEntry.getBoundingClientRect().height;
            this.orgChartRef.el.scrollTop += entryHeight;
            this.scrollUpBtn.el.style.visibility = "visible";
            if(this.orgChartRef.el.scrollTop + this.orgChartRef.el.clientHeight >= this.orgChartRef.el.scrollHeight - entryHeight){
                this.scrollDownBtn.el.style.visibility = "hidden";
            }
        }
    }
}

HrOrgChart.components = {
    Popover: HrOrgChartPopover,
};

HrOrgChart.template = 'hr_org_chart.hr_org_chart';

registry.category("fields").add("hr_org_chart", HrOrgChart);
