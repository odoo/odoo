/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class TechnicianDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            technicians: [],
            activeTab: 'overview',
            newTech: { name: '', job_title: 'Extrusion Technician', work_email: '', work_phone: '' }
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        // Fetch ONLY employees flagged as Technicians
        const employees = await this.orm.searchRead(
            "hr.employee",
            [["is_drs_technician", "=", true]],
            ["id", "name"]
        );

        let techMap = {};
        for (let emp of employees) {
            techMap[emp.id] = {
                id: emp.id,
                name: emp.name,
                m311: { weight: 0, rolls: 0 },
                m312: { weight: 0, rolls: 0 },
                totalWeight: 0,
                totalRolls: 0
            };
        }

        // Fetch all production records to calculate many2many relations
        const records = await this.orm.searchRead(
            "mrp.drs.production",
            [],
            ["technician_ids", "machine_number", "final_weight"]
        );

        for (let r of records) {
            let weight = r.final_weight || 0;
            let techIds = r.technician_ids || [];

            for (let tId of techIds) {
                if (techMap[tId]) {
                    techMap[tId].totalWeight += weight;
                    techMap[tId].totalRolls += 1;

                    if (r.machine_number === '311') {
                        techMap[tId].m311.weight += weight;
                        techMap[tId].m311.rolls += 1;
                    } else if (r.machine_number === '312') {
                        techMap[tId].m312.weight += weight;
                        techMap[tId].m312.rolls += 1;
                    }
                }
            }
        }

        this.state.technicians = Object.values(techMap).sort((a, b) => {
            if (b.totalWeight !== a.totalWeight) return b.totalWeight - a.totalWeight;
            return a.name.localeCompare(b.name);
        });
    }

    setTab(tabName) {
        this.state.activeTab = tabName;
    }

    async createTechnician(ev) {
        ev.preventDefault();

        if (!this.state.newTech.name) {
            this.notification.add("Technician Name is required.", { type: "danger" });
            return;
        }

        try {
            // Apply the 'is_drs_technician: true' flag automatically
            await this.orm.create("hr.employee", [{
                name: this.state.newTech.name,
                job_title: this.state.newTech.job_title,
                work_email: this.state.newTech.work_email,
                work_phone: this.state.newTech.work_phone,
                is_drs_technician: true
            }]);

            this.notification.add("New Technician added successfully!", { type: "success" });
            this.state.newTech = { name: '', job_title: 'Extrusion Technician', work_email: '', work_phone: '' };

            await this.fetchData();
            this.state.activeTab = 'overview';

        } catch (error) {
            this.notification.add("An error occurred while creating the technician.", { type: "danger" });
        }
    }

    openEmployeeDirectory() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Manage Technicians',
            res_model: 'hr.employee',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['is_drs_technician', '=', true]],
            context: { default_is_drs_technician: true }
        });
    }

    openTechnicianWork(technicianId) {
        // Domain for Many2many is 'in'
        let domain = technicianId ? [['technician_ids', 'in', [technicianId]]] : [['technician_ids', '=', false]];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Technician Production Reports',
            res_model: 'mrp.drs.production',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }
}

TechnicianDashboard.template = "mrp_drs_production.TechnicianDashboardTemplate";
registry.category("actions").add("drs_technician_dashboard_action", TechnicianDashboard);