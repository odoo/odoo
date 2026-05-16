/** @odoo-module **/

import { Component } from "@odoo/owl";

export class QuickVisitForm extends Component {
    static template = "clinic_visit_manager.QuickVisitForm";
    static props = ["visit", "update", "create", "close"];
}

export class QuickPatientForm extends Component {
    static template = "clinic_visit_manager.QuickPatientForm";
    static props = ["patient", "update", "create", "close"];
}

export class DashboardSummary extends Component {
    static template = "clinic_visit_manager.DashboardSummary";
    static props = [
        "data",
        "metricCards",
        "updatedAt",
        "canCompleteVisits",
        "canStartVisits",
        "openDashboardAction",
        "openVisit",
        "completeVisit",
        "startVisit",
        "statusClass",
    ];
}

export class VisitTable extends Component {
    static template = "clinic_visit_manager.VisitTable";
    static props = [
        "visits",
        "visitCount",
        "pageNumbers",
        "currentPage",
        "canQueueVisits",
        "canStartVisits",
        "canCompleteVisits",
        "canCancelVisits",
        "formatDate",
        "formatNumber",
        "statusClass",
        "statusLabel",
        "openVisit",
        "sendToQueue",
        "startVisit",
        "completeVisit",
        "cancelVisit",
        "setPage",
        "previousPage",
        "nextPage",
    ];
}

export class PatientTable extends Component {
    static template = "clinic_visit_manager.PatientTable";
    static props = [
        "patients",
        "patientCount",
        "pageNumbers",
        "currentPage",
        "genderLabel",
        "bloodGroupLabel",
        "openPatient",
        "setPage",
        "previousPage",
        "nextPage",
    ];
}
