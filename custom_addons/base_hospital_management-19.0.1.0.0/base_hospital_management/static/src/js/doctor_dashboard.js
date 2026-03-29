/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";
import { user } from "@web/core/user";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class DoctorDashboard extends Component {
    static template = "DoctorDashboard";

    setup() {
        super.setup();
        this.rootRef = useRef('root');
        this.patientDataRef = useRef('patientData');
        this.orm = useService('orm');
        this.user = user;
        this.actionService = useService("action");
        this.welcomeRef = useRef("welcome");
        this.state = useState({
            patients: [],
            search_button: false,
            patients_search: [],
            activeSection: '',
        });
    }

    //Function for feting patient data
    async list_patient_data() {
        const patients = await this.orm.call('res.partner', 'fetch_patient_data', []);
        this.state.patients = patients;
        this.state.activeSection = 'patient_data';
        if (this.patientDataRef.el) {
            const activeElements = this.rootRef.el.querySelectorAll('.n_active');
            activeElements.forEach(el => el.classList.remove('n_active'));
            this.patientDataRef.el.classList.add('n_active');
        }
        await this.actionService.doAction({
            name: _t('Patient details'),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [['patient_seq', 'not in', ['New', 'Employee', 'User']]],
        });
    }

    //  Method for generating list of inpatients
    async action_list_inpatient() {
        await this.actionService.doAction({
            name: _t('Inpatient details'),
            type: 'ir.actions.act_window',
            res_model: 'hospital.inpatient',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
        });
        this.state.activeSection = 'inpatient';
    }

    // Fetch surgery details
    async fetch_doctors_schedule() {
        await this.actionService.doAction({
            name: _t('Surgery details'),
            type: 'ir.actions.act_window',
            res_model: 'inpatient.surgery',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
        });
        this.state.activeSection = 'surgery';
    }

    // Fetch op details
    async fetch_consultation() {
        await this.actionService.doAction({
            name: _t('Outpatient Details'),
            type: 'ir.actions.act_window',
            res_model: 'hospital.outpatient',
            view_mode: 'list,form',
            views: [[false, 'list']],
        });
        this.state.activeSection = 'outpatient';
    }

    // Fetch allocation details
    async fetch_allocation_lines() {
        await this.actionService.doAction({
            name: _t('Doctor Allocation'),
            type: 'ir.actions.act_window',
            res_model: 'doctor.allocation',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
        });
        this.state.activeSection = 'allocation';
    }
}

registry.category("actions").add('doctor_dashboard_tags', DoctorDashboard);

