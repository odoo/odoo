/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";

// ── helpers ──────────────────────────────────────────────────────────────────

function formatElapsed(totalSeconds) {
    const abs = Math.abs(totalSeconds);
    const h = Math.floor(abs / 3600);
    const m = Math.floor((abs % 3600) / 60);
    const s = abs % 60;
    return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

function timerStartToDate(value) {
    if (!value) return null;
    // Odoo datetime fields come as JS Date objects or ISO strings
    return value instanceof Date ? value : new Date(value.replace(" ", "T") + "Z");
}

// ── Stop dialog ───────────────────────────────────────────────────────────────

class TimerStopDialog extends Component {
    static template = "project_maestro_timer.TimerStopDialog";
    static components = { Dialog };
    static props = {
        elapsed: { type: String },
        onConfirm: { type: Function },
        onDiscard: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.state = useState({ description: "" });
    }

    onConfirm() {
        this.props.onConfirm(this.state.description);
        this.props.close();
    }

    onDiscard() {
        this.props.onDiscard();
        this.props.close();
    }
}

// ── Main widget component ─────────────────────────────────────────────────────

export class TaskTimerWidget extends Component {
    static template = "project_maestro_timer.TaskTimerWidget";
    static components = { TimerStopDialog };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.state = useState({ elapsed: 0, ticking: false });
        this._intervalId = null;

        onMounted(() => this._sync());

        onWillUpdateProps(() => {
            this._clearInterval();
            this._sync();
        });

        onWillDestroy(() => this._clearInterval());
    }

    // ── internals ─────────────────────────────────────────────────────────────

    get timerStart() {
        return this.props.record.data[this.props.name];
    }

    get isRunning() {
        return !!this.timerStart;
    }

    get elapsedFormatted() {
        return formatElapsed(this.state.elapsed);
    }

    _sync() {
        const start = timerStartToDate(this.timerStart);
        if (start) {
            this.state.elapsed = Math.floor((Date.now() - start.getTime()) / 1000);
            this.state.ticking = true;
            this._startInterval();
        } else {
            this.state.elapsed = 0;
            this.state.ticking = false;
        }
    }

    _startInterval() {
        this._clearInterval();
        this._intervalId = setInterval(() => {
            if (this.state.ticking) {
                this.state.elapsed += 1;
            }
        }, 1000);
    }

    _clearInterval() {
        if (this._intervalId) {
            clearInterval(this._intervalId);
            this._intervalId = null;
        }
    }

    // ── actions ───────────────────────────────────────────────────────────────

    async onStart() {
        const resId = this.props.record.resId;
        if (!resId) {
            this.notification.add("Salve a tarefa antes de iniciar o cronômetro.", { type: "warning" });
            return;
        }
        await this.orm.call("project.task", "action_timer_start", [resId]);
        await this.props.record.load();
    }

    onStop() {
        this.dialog.add(TimerStopDialog, {
            elapsed: this.elapsedFormatted,
            onConfirm: async (description) => {
                const resId = this.props.record.resId;
                await this.orm.call("project.task", "action_timer_stop", [resId, description]);
                await this.props.record.load();
                this.notification.add("Tempo registrado com sucesso!", { type: "success" });
            },
            onDiscard: async () => {
                const resId = this.props.record.resId;
                await this.orm.call("project.task", "action_timer_discard", [resId]);
                await this.props.record.load();
            },
        });
    }
}

registry.category("fields").add("task_timer", { component: TaskTimerWidget });
