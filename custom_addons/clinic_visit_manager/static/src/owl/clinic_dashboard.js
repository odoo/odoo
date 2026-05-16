/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";
import { formatDateTime, formatFloat } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import {
    DashboardSummary,
    PatientTable,
    QuickPatientForm,
    QuickVisitForm,
    VisitTable,
} from "@clinic_visit_manager/owl/clinic_dashboard_components";

const VISIT_FIELDS = [
    "token_number",
    "name",
    "patient_name",
    "doctor_name",
    "visit_date",
    "queue_wait_minutes",
    "fee",
    "state",
];

const PATIENT_FIELDS = [
    "name",
    "phone",
    "email",
    "age",
    "gender",
    "blood_group",
    "visit_count",
];

const STATE_LABELS = {
    draft: _t("Draft"),
    waiting: _t("Waiting"),
    in_consultation: _t("In Consultation"),
    done: _t("Done"),
    cancelled: _t("Cancelled"),
};

const GENDER_LABELS = {
    male: _t("Male"),
    female: _t("Female"),
    other: _t("Other"),
};

const BLOOD_GROUP_LABELS = {
    a_positive: "A+",
    a_negative: "A-",
    b_positive: "B+",
    b_negative: "B-",
    ab_positive: "AB+",
    ab_negative: "AB-",
    o_positive: "O+",
    o_negative: "O-",
};

const VISIT_FILTERS = [
    ["active", _t("Active")],
    ["draft", _t("Draft")],
    ["waiting", _t("Waiting")],
    ["in_consultation", _t("In Consultation")],
    ["done", _t("Done")],
    ["all", _t("All")],
];

const FLOAT_VISIT_FIELDS = ["fee"];

const SEARCH_DELAY = 250;
const VISIT_PAGE_SIZE = 3;
const PATIENT_PAGE_SIZE = 5;

export class ClinicDashboard extends Component {
    static template = "clinic_visit_manager.ClinicDashboard";
    static components = {
        ControlPanel,
        DashboardSummary,
        PatientTable,
        QuickPatientForm,
        QuickVisitForm,
        VisitTable,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.searchTimers = {};
        this.state = useState({
            activeTab: this.props.action.context?.clinic_tab || "dashboard",
            dashboard: null,
            visits: [],
            visitCount: 0,
            visitPage: 1,
            patients: [],
            patientPage: 1,
            visitFilter: "active",
            visitSearch: "",
            patientSearch: "",
            error: null,
            loading: true,
            showVisitForm: false,
            showPatientForm: false,
            newVisit: this.emptyVisit(),
            newPatient: this.emptyPatient(),
        });

        onWillStart(() => this.loadWorkspace());
        onMounted(() => {
            this.refreshInterval = setInterval(() => this.loadWorkspace({ silent: true }), 60000);
        });
        onWillUnmount(() => {
            clearInterval(this.refreshInterval);
            for (const timer of Object.values(this.searchTimers)) {
                clearTimeout(timer);
            }
        });
    }

    emptyVisit() {
        return {
            patient_name: "",
            patient_phone: "",
            patient_email: "",
            patient_age: "",
            patient_gender: "",
            doctor_name: "",
            fee: "",
            symptoms: "",
        };
    }

    emptyPatient() {
        return {
            name: "",
            phone: "",
            email: "",
            age: "",
            gender: "",
            blood_group: "",
            notes: "",
        };
    }

    async loadWorkspace(options = {}) {
        if (!options.silent) {
            this.state.loading = true;
        }
        try {
            await Promise.all([this.loadDashboard(), this.loadVisits(), this.loadPatients()]);
            this.state.error = null;
        } catch (error) {
            this.state.error = error.message || _t("The clinic workspace could not be loaded.");
        } finally {
            this.state.loading = false;
        }
    }

    async loadDashboard() {
        this.state.dashboard = await this.orm.call(
            "clinic.visit.dashboard",
            "get_owl_dashboard_data",
            []
        );
    }

    async loadVisits() {
        const domain = this.visitDomain();
        this.state.visitCount = await this.orm.searchCount("clinic.visit", domain);
        this.clampVisitPage();
        this.state.visits = await this.orm.searchRead("clinic.visit", domain, VISIT_FIELDS, {
            order: "visit_date desc, id desc",
            limit: VISIT_PAGE_SIZE,
            offset: (this.state.visitPage - 1) * VISIT_PAGE_SIZE,
        });
    }

    async loadPatients() {
        const domain = this.patientDomain();
        this.state.patients = await this.orm.searchRead("clinic.patient", domain, PATIENT_FIELDS, {
            order: "name asc",
            limit: 80,
        });
        this.clampPatientPage();
    }

    visitDomain() {
        const domain = [];
        if (this.state.visitFilter === "active") {
            domain.push(["state", "in", ["waiting", "in_consultation"]]);
        } else if (this.state.visitFilter !== "all") {
            domain.push(["state", "=", this.state.visitFilter]);
        }
        const search = this.state.visitSearch.trim();
        if (search) {
            domain.push("|", "|", ["patient_name", "ilike", search], ["token_number", "ilike", search], [
                "doctor_name",
                "ilike",
                search,
            ]);
        }
        return domain;
    }

    patientDomain() {
        const search = this.state.patientSearch.trim();
        if (!search) {
            return [];
        }
        return ["|", "|", ["name", "ilike", search], ["phone", "ilike", search], ["email", "ilike", search]];
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    toggleForm(formName) {
        if (formName === "patient" && !this.canCreatePatient) {
            return;
        }
        if (formName !== "patient" && !this.canCreateVisit) {
            return;
        }
        const stateKey = formName === "patient" ? "showPatientForm" : "showVisitForm";
        this.state[stateKey] = !this.state[stateKey];
    }

    async setVisitFilter(filter) {
        this.state.visitFilter = filter;
        this.state.visitPage = 1;
        await this.loadVisits();
    }

    onVisitSearch(ev) {
        this.state.visitSearch = ev.target.value;
        this.state.visitPage = 1;
        this.debounce("visits", () => this.loadVisits());
    }

    onPatientSearch(ev) {
        this.state.patientSearch = ev.target.value;
        this.state.patientPage = 1;
        this.debounce("patients", () => this.loadPatients());
    }

    debounce(key, callback) {
        clearTimeout(this.searchTimers[key]);
        this.searchTimers[key] = setTimeout(callback, SEARCH_DELAY);
    }

    updateNewVisit(field, value) {
        this.state.newVisit[field] = value;
    }

    updateNewPatient(field, value) {
        this.state.newPatient[field] = value;
    }

    closeVisitForm() {
        this.state.showVisitForm = false;
    }

    closePatientForm() {
        this.state.showPatientForm = false;
    }

    async setVisitPage(page) {
        this.state.visitPage = page;
        this.clampVisitPage();
        await this.loadVisits();
    }

    async nextVisitPage() {
        this.state.visitPage =
            this.state.visitPage >= this.visitPageCount ? 1 : this.state.visitPage + 1;
        await this.loadVisits();
    }

    async previousVisitPage() {
        this.state.visitPage =
            this.state.visitPage <= 1 ? this.visitPageCount : this.state.visitPage - 1;
        await this.loadVisits();
    }

    clampVisitPage() {
        this.state.visitPage = Math.min(Math.max(this.state.visitPage, 1), this.visitPageCount);
    }

    setPatientPage(page) {
        this.state.patientPage = page;
        this.clampPatientPage();
    }

    nextPatientPage() {
        this.state.patientPage =
            this.state.patientPage >= this.patientPageCount ? 1 : this.state.patientPage + 1;
    }

    previousPatientPage() {
        this.state.patientPage =
            this.state.patientPage <= 1 ? this.patientPageCount : this.state.patientPage - 1;
    }

    clampPatientPage() {
        this.state.patientPage = Math.min(Math.max(this.state.patientPage, 1), this.patientPageCount);
    }

    async createVisit() {
        const intakeVals = this.cleanValues(this.state.newVisit, FLOAT_VISIT_FIELDS, ["patient_age"]);
        if (!intakeVals.patient_name) {
            this.notification.add(_t("Patient name is required."), { type: "warning" });
            return;
        }
        try {
            const patient = await this.findOrCreatePatient(this.patientValuesFromVisit(intakeVals));
            const visitVals = this.visitValuesFromIntake(intakeVals, patient);
            const ids = await this.orm.create("clinic.visit", [visitVals]);
            this.notification.add(_t("Visit created."), { type: "success" });
            this.state.newVisit = this.emptyVisit();
            this.state.showVisitForm = false;
            await this.loadWorkspace({ silent: true });
            await this.openVisit({ id: ids[0], name: visitVals.patient_name });
        } catch (error) {
            this.notification.add(error.message || _t("The visit could not be created."), {
                type: "danger",
            });
        }
    }

    patientValuesFromVisit(vals) {
        return this.cleanValues(
            {
                name: vals.patient_name,
                phone: vals.patient_phone,
                email: vals.patient_email,
                age: vals.patient_age,
                gender: vals.patient_gender,
            },
            [],
            ["age"]
        );
    }

    visitValuesFromIntake(vals, patient) {
        const visitVals = this.cleanValues(
            {
                patient_name: vals.patient_name,
                doctor_name: vals.doctor_name,
                fee: vals.fee,
                symptoms: vals.symptoms,
            },
            FLOAT_VISIT_FIELDS
        );
        if (patient?.id) {
            visitVals.patient_id = patient.id;
        }
        return visitVals;
    }

    async findOrCreatePatient(vals) {
        if (!vals.name) {
            return null;
        }
        const patients = await this.orm.searchRead(
            "clinic.patient",
            this.patientLookupDomain(vals),
            ["name", "phone", "email", "age", "gender"],
            { limit: 1 }
        );
        if (!patients.length) {
            const ids = await this.orm.create("clinic.patient", [vals]);
            return { id: ids[0], name: vals.name };
        }

        const patient = patients[0];
        const updateVals = {};
        for (const field of ["phone", "email", "age", "gender"]) {
            if (vals[field] && !patient[field]) {
                updateVals[field] = vals[field];
            }
        }
        if (Object.keys(updateVals).length) {
            await this.orm.write("clinic.patient", [patient.id], updateVals);
        }
        return patient;
    }

    patientLookupDomain(vals) {
        if (vals.email) {
            return [["email", "=ilike", vals.email]];
        }
        if (vals.phone) {
            return [["phone", "=", vals.phone]];
        }
        return [["name", "=ilike", vals.name]];
    }

    async createPatient() {
        const vals = this.cleanValues(this.state.newPatient, [], ["age"]);
        if (!vals.name) {
            this.notification.add(_t("Patient name is required."), { type: "warning" });
            return;
        }
        try {
            await this.orm.create("clinic.patient", [vals]);
            this.notification.add(_t("Patient card created."), { type: "success" });
            this.state.newPatient = this.emptyPatient();
            this.state.showPatientForm = false;
            await this.loadPatients();
            await this.loadDashboard();
        } catch (error) {
            this.notification.add(error.message || _t("The patient could not be created."), {
                type: "danger",
            });
        }
    }

    cleanValues(source, floatFields = [], integerFields = []) {
        const vals = {};
        const floats = new Set(floatFields);
        const integers = new Set(integerFields);
        for (const [field, value] of Object.entries(source)) {
            if (value === "" || value === null || value === undefined) {
                continue;
            }
            if (floats.has(field)) {
                vals[field] = Number(value);
            } else if (integers.has(field)) {
                vals[field] = parseInt(value, 10);
            } else {
                vals[field] = value;
            }
        }
        return vals;
    }

    async openDashboardAction(actionKey, state = false) {
        if (actionKey === "state" && state) {
            await this.openVisits(state);
            return;
        }
        if (actionKey === "patients") {
            this.setTab("patients");
            return;
        }
        const filter = actionKey === "active_queue" ? "active" : "all";
        await this.openVisits(filter);
    }

    async openVisits(filter) {
        this.state.visitFilter = filter;
        this.state.visitPage = 1;
        this.setTab("visits");
        await this.loadVisits();
    }

    openRecord(model, record, fallbackName) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: record.token_number || record.name || fallbackName,
            res_model: model,
            res_id: record.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openVisit(visit) {
        return this.openRecord("clinic.visit", visit, _t("Visit"));
    }

    openPatient(patient) {
        return this.openRecord("clinic.patient", patient, _t("Patient"));
    }

    async runVisitWorkflow(visit, method, message) {
        try {
            await this.orm.call("clinic.visit", method, [[visit.id]]);
            this.notification.add(message, { type: "success" });
            await this.loadWorkspace({ silent: true });
        } catch (error) {
            this.notification.add(error.message || _t("The clinic action could not be completed."), {
                type: "danger",
            });
        }
    }

    async sendToQueue(visit) {
        await this.runVisitWorkflow(visit, "action_confirm", _t("Visit sent to queue."));
    }

    async startVisit(visit) {
        await this.runVisitWorkflow(visit, "action_start_consultation", _t("Consultation started."));
    }

    async completeVisit(visit) {
        await this.runVisitWorkflow(visit, "action_done", _t("Visit completed."));
    }

    async cancelVisit(visit) {
        await this.runVisitWorkflow(visit, "action_cancel", _t("Visit cancelled."));
    }

    formatDate(value) {
        return value ? formatDateTime(deserializeDateTime(value), { showSeconds: false }) : "";
    }

    formatNumber(value, digits = 0) {
        return formatFloat(value || 0, { digits: [16, digits] });
    }

    statusLabel(state) {
        return STATE_LABELS[state] || state;
    }

    genderLabel(gender) {
        return GENDER_LABELS[gender] || gender || "-";
    }

    bloodGroupLabel(bloodGroup) {
        return BLOOD_GROUP_LABELS[bloodGroup] || bloodGroup || "-";
    }

    statusClass(state) {
        return `o_clinic_status o_clinic_status_${state}`;
    }

    tabClass(tab) {
        return this.state.activeTab === tab ? "active" : "";
    }

    filterClass(filter) {
        return this.state.visitFilter === filter ? "active" : "";
    }

    get data() {
        return this.state.dashboard || {};
    }

    get metrics() {
        return this.data.metrics || {};
    }

    get permissions() {
        return this.data.permissions || {};
    }

    get canCreateVisit() {
        return Boolean(this.permissions.can_create_visit);
    }

    get canCreatePatient() {
        return Boolean(this.permissions.can_create_patient);
    }

    get canQueueVisits() {
        return Boolean(this.permissions.can_queue);
    }

    get canStartVisits() {
        return Boolean(this.permissions.can_start);
    }

    get canCompleteVisits() {
        return Boolean(this.permissions.can_complete);
    }

    get canCancelVisits() {
        return Boolean(this.permissions.can_cancel);
    }

    get metricCards() {
        return [
            {
                key: "today",
                label: _t("Today's Visits"),
                value: this.metrics.today_visits || 0,
                action: "all_visits",
            },
            {
                key: "queue",
                label: _t("Active Queue"),
                value: this.metrics.active_queue || 0,
                action: "active_queue",
            },
            {
                key: "completed",
                label: _t("Completed Today"),
                value: this.metrics.completed_today || 0,
                state: "done",
            },
            {
                key: "patients",
                label: _t("Patients"),
                value: this.metrics.total_patients || 0,
                action: "patients",
            },
        ];
    }

    get visitFilters() {
        return VISIT_FILTERS.map(([key, label]) => ({ key, label }));
    }

    get visitPageCount() {
        return Math.max(1, Math.ceil(this.state.visitCount / VISIT_PAGE_SIZE));
    }

    get visitPageNumbers() {
        return Array.from({ length: this.visitPageCount }, (_, index) => index + 1);
    }

    get patientPageCount() {
        return Math.max(1, Math.ceil(this.state.patients.length / PATIENT_PAGE_SIZE));
    }

    get patientPageNumbers() {
        return Array.from({ length: this.patientPageCount }, (_, index) => index + 1);
    }

    get paginatedPatients() {
        const start = (this.state.patientPage - 1) * PATIENT_PAGE_SIZE;
        return this.state.patients.slice(start, start + PATIENT_PAGE_SIZE);
    }

    get updatedAt() {
        return this.formatDate(this.data.updated_at);
    }
}

registry.category("actions").add("clinic_visit_manager.dashboard", ClinicDashboard);
