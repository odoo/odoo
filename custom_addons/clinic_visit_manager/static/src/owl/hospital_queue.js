/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const QUEUE_CHANNEL = "hospital_queue";
const QUEUE_NOTIFICATION = "hospital_queue_update";

class ServingCard extends Component {
    static template = "clinic_visit_manager.ServingCard";
    static props = ["current"];
}

class WaitingList extends Component {
    static template = "clinic_visit_manager.WaitingList";
    static props = ["waiting", "skipped", "showSkipped", "recall"];
}

class QueueControls extends Component {
    static template = "clinic_visit_manager.QueueControls";
    static props = ["current", "hasWaiting", "hasRecall", "callNext", "complete", "skip", "recall"];
}

export class QueueDashboard extends Component {
    static template = "clinic_visit_manager.QueueDashboard";
    static components = { ControlPanel, ServingCard, WaitingList, QueueControls };
    static props = { ...standardActionServiceProps };

    setup() {
        this.busService = useService("bus_service");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
            data: this.emptyQueueData(),
            loading: true,
            doctorId: false,
            adding: false,
            newPatientName: "",
        });
        this.onQueueUpdate = (payload) => this.handleQueueUpdate(payload);

        onWillStart(async () => {
            this.busService.subscribe(QUEUE_NOTIFICATION, this.onQueueUpdate);
            await this.busService.addChannel(QUEUE_CHANNEL);
            await this.loadQueue();
        });
        onWillUnmount(() => {
            this.busService.unsubscribe(QUEUE_NOTIFICATION, this.onQueueUpdate);
            this.busService.deleteChannel(QUEUE_CHANNEL);
        });
    }

    emptyQueueData() {
        return {
            doctor: false,
            doctors: [],
            current: false,
            waiting: [],
            skipped: [],
            can_add_queue: false,
            updated_at: false,
        };
    }

    async loadQueue(options = {}) {
        if (!options.silent) {
            this.state.loading = true;
        }
        try {
            const data = await this.orm.call("hospital.queue", "get_queue_data", [
                this.state.doctorId || false,
            ]);
            this.state.data = data;
            this.state.doctorId = data.doctor?.id || false;
        } catch (error) {
            this.notification.add(error.message || _t("The queue could not be loaded."), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    handleQueueUpdate(payload) {
        const doctorIds = payload.doctor_ids || [];
        if (!doctorIds.length || !this.state.doctorId || doctorIds.includes(this.state.doctorId)) {
            this.loadQueue({ silent: true });
        }
    }

    async setDoctor(ev) {
        this.state.doctorId = parseInt(ev.target.value, 10);
        await this.loadQueue();
    }

    updateNewPatientName(ev) {
        this.state.newPatientName = ev.target.value;
    }

    async addPatient() {
        const patientName = this.state.newPatientName.trim();
        if (!patientName || this.state.adding) {
            return;
        }
        this.state.adding = true;
        try {
            this.state.data = await this.orm.call("hospital.queue", "action_add_patient", [
                patientName,
                this.state.doctorId,
            ]);
            this.state.newPatientName = "";
            this.notification.add(_t("Patient added to queue."), { type: "success" });
        } catch (error) {
            this.notification.add(error.message || _t("The patient could not be added."), {
                type: "danger",
            });
        } finally {
            this.state.adding = false;
        }
    }

    async runQueueAction(callback, successMessage) {
        try {
            const data = await callback();
            if (data) {
                this.state.data = data;
            } else {
                await this.loadQueue({ silent: true });
            }
            this.notification.add(successMessage, { type: "success" });
        } catch (error) {
            this.notification.add(error.message || _t("The queue action could not be completed."), {
                type: "danger",
            });
        }
    }

    async callNext() {
        await this.runQueueAction(
            () => this.orm.call("hospital.queue", "action_call_next", [this.state.doctorId]),
            _t("Next patient called.")
        );
    }

    async complete() {
        if (!this.current) {
            return;
        }
        await this.runQueueAction(
            () => this.orm.call("hospital.queue", "action_complete", [[this.current.id]]),
            _t("Patient completed.")
        );
    }

    async skip() {
        if (!this.current) {
            return;
        }
        await this.runQueueAction(
            () => this.orm.call("hospital.queue", "action_skip", [[this.current.id]]),
            _t("Patient skipped.")
        );
    }

    async recall(queue = false) {
        const target = queue || this.current || this.skipped[0];
        if (!target) {
            return;
        }
        await this.runQueueAction(
            () => this.orm.call("hospital.queue", "action_recall", [[target.id]]),
            _t("Patient recalled.")
        );
    }

    get data() {
        return this.state.data || this.emptyQueueData();
    }

    get current() {
        return this.data.current;
    }

    get waiting() {
        return this.data.waiting || [];
    }

    get skipped() {
        return this.data.skipped || [];
    }

    get hasWaiting() {
        return Boolean(this.waiting.length);
    }

    get hasRecall() {
        return Boolean(this.current || this.skipped.length);
    }

    get canAddQueue() {
        return Boolean(this.data.can_add_queue);
    }
}

export class TVDisplayScreen extends Component {
    static template = "clinic_visit_manager.TVDisplayScreen";
    static components = { ServingCard, WaitingList };
    static props = { ...standardActionServiceProps };

    setup() {
        this.busService = useService("bus_service");
        this.orm = useService("orm");
        this.state = useState({
            data: {
                current: false,
                waiting: [],
                skipped: [],
                doctor: false,
            },
            loading: true,
        });
        this.onQueueUpdate = () => this.loadQueue({ silent: true });

        onWillStart(async () => {
            this.busService.subscribe(QUEUE_NOTIFICATION, this.onQueueUpdate);
            await this.busService.addChannel(QUEUE_CHANNEL);
            await this.loadQueue();
        });
        onWillUnmount(() => {
            this.busService.unsubscribe(QUEUE_NOTIFICATION, this.onQueueUpdate);
            this.busService.deleteChannel(QUEUE_CHANNEL);
        });
    }

    async loadQueue(options = {}) {
        if (!options.silent) {
            this.state.loading = true;
        }
        this.state.data = await this.orm.call("hospital.queue", "get_queue_data", [false]);
        this.state.loading = false;
    }

    get data() {
        return this.state.data;
    }
}

registry.category("actions").add("clinic_visit_manager.hospital_queue_dashboard", QueueDashboard);
registry.category("actions").add("clinic_visit_manager.hospital_queue_tv", TVDisplayScreen);
