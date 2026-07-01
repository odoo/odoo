/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

// ── formatadores ──────────────────────────────────────────────────────────────

function formatSeconds(totalSeconds) {
    const abs = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(abs / 3600);
    const m = Math.floor((abs % 3600) / 60);
    const s = abs % 60;
    return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

function odooDatetimeToMs(value) {
    if (!value) return null;
    if (value instanceof Date) return value.getTime();
    // Odoo retorna "YYYY-MM-DD HH:MM:SS" em UTC
    return new Date(String(value).replace(" ", "T") + "Z").getTime();
}

// ── Diálogo de confirmação de parada ─────────────────────────────────────────

class TimerSaveDialog extends Component {
    static template = "project_maestro_timer.TimerSaveDialog";
    static components = { Dialog };
    static props = {
        elapsed: String,
        onSave: Function,
        onDiscard: Function,
        close: Function,
    };
    setup() {
        this.state = useState({ description: "" });
    }
    onSave() {
        this.props.onSave(this.state.description);
        this.props.close();
    }
    onDiscard() {
        this.props.onDiscard();
        this.props.close();
    }
}

// ── Widget principal ──────────────────────────────────────────────────────────

export class TaskTimerWidget extends Component {
    static template = "project_maestro_timer.TaskTimerWidget";
    static components = { TimerSaveDialog };
    /**
     * Props recebidos do campo `user_timer_status` (Char).
     * Mas precisamos também do `user_timer_accumulated` e do timer_start do
     * registro de project.task.timer — buscamos via action_timer_state().
     */
    static props = {
        // standardFieldProps subset que precisamos
        record: Object,
        name: String,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        // status: 'idle' | 'running' | 'paused'
        this.state = useState({
            status: "idle",
            elapsed: 0,          // segundos totais (acumulado + sessão atual)
            accumulated: 0,      // segundos de sessões pausadas
            timerStartMs: null,  // timestamp UTC da sessão atual em andamento
        });

        this._intervalId = null;

        onMounted(() => this._refreshFromServer());
        onWillUpdateProps(() => {
            // O campo user_timer_status mudou no record → sincroniza
            this._refreshFromRecord();
        });
        onWillDestroy(() => this._clearInterval());
    }

    // ── sincronização ─────────────────────────────────────────────────────────

    async _refreshFromServer() {
        const resId = this.props.record.resId;
        if (!resId) return;
        try {
            const result = await this.orm.call(
                "project.task", "action_timer_state", [resId]);
            this._applyState(result);
        } catch (e) {
            // offline ou erro de rede — não travar a UI
        }
    }

    _refreshFromRecord() {
        // fallback rápido usando os campos computados já no record
        const status = this.props.record.data["user_timer_status"] || "idle";
        if (status !== this.state.status) {
            this._refreshFromServer();
        }
    }

    _applyState({ status, accumulated_seconds, timer_start }) {
        this._clearInterval();
        const acc = accumulated_seconds || 0;
        const startMs = timer_start ? odooDatetimeToMs(timer_start) : null;

        this.state.status = status;
        this.state.accumulated = acc;
        this.state.timerStartMs = startMs;

        if (status === "running" && startMs) {
            this._tickNow(acc, startMs);
            this._startInterval(acc, startMs);
        } else {
            this.state.elapsed = acc;
        }
    }

    _tickNow(acc, startMs) {
        this.state.elapsed = acc + Math.floor((Date.now() - startMs) / 1000);
    }

    _startInterval(acc, startMs) {
        this._intervalId = setInterval(() => {
            this.state.elapsed = acc + Math.floor((Date.now() - startMs) / 1000);
        }, 1000);
    }

    _clearInterval() {
        if (this._intervalId) {
            clearInterval(this._intervalId);
            this._intervalId = null;
        }
    }

    // ── getters para o template ───────────────────────────────────────────────

    get isIdle()    { return this.state.status === "idle"; }
    get isRunning() { return this.state.status === "running"; }
    get isPaused()  { return this.state.status === "paused"; }

    get elapsedFormatted() { return formatSeconds(this.state.elapsed); }

    // ── ações ─────────────────────────────────────────────────────────────────

    async onStart() {
        const resId = this.props.record.resId;
        if (!resId) {
            this.notification.add("Salve a tarefa antes de iniciar o cronômetro.", { type: "warning" });
            return;
        }
        await this.orm.call("project.task", "action_timer_start", [resId]);
        await this._refreshFromServer();
        await this.props.record.load();
    }

    async onPause() {
        const resId = this.props.record.resId;
        await this.orm.call("project.task", "action_timer_pause", [resId]);
        await this._refreshFromServer();
        await this.props.record.load();
    }

    onStop() {
        this.dialog.add(TimerSaveDialog, {
            elapsed: this.elapsedFormatted,
            onSave: async (description) => {
                const resId = this.props.record.resId;
                await this.orm.call("project.task", "action_timer_stop", [resId, description]);
                this._clearInterval();
                this.state.status = "idle";
                this.state.elapsed = 0;
                await this.props.record.load();
                this.notification.add("Tempo registrado com sucesso!", { type: "success" });
            },
            onDiscard: async () => {
                const resId = this.props.record.resId;
                await this.orm.call("project.task", "action_timer_discard", [resId]);
                this._clearInterval();
                this.state.status = "idle";
                this.state.elapsed = 0;
                await this.props.record.load();
            },
        });
    }
}

registry.category("fields").add("task_timer", { component: TaskTimerWidget });
