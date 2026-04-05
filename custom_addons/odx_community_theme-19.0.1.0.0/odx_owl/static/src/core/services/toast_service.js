/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ToastViewport } from "@odx_owl/components/toast/toast";

const TOAST_LIMIT = 1;
const REMOVE_DELAY = 220;
const DEFAULT_DURATION = 4500;

export const odxToastService = {
    start() {
        let toastId = 0;
        const state = reactive({ toasts: [] });
        const timers = new Map();
        const remainingTimes = new Map();
        const timerDeadlines = new Map();

        registry.category("main_components").add(
            "odx_owl.toast_viewport",
            {
                Component: ToastViewport,
                props: { state },
            },
            { sequence: 140 }
        );

        function remove(id) {
            state.toasts = state.toasts.filter((toast) => toast.id !== id);
            clearTimeout(timers.get(id));
            timers.delete(id);
            remainingTimes.delete(id);
            timerDeadlines.delete(id);
        }

        function startDismissTimer(id, delay) {
            clearTimeout(timers.get(id));
            if (!delay || delay <= 0) {
                timers.delete(id);
                remainingTimes.delete(id);
                timerDeadlines.delete(id);
                return;
            }
            timerDeadlines.set(id, Date.now() + delay);
            timers.set(
                id,
                setTimeout(() => {
                    dismiss(id);
                }, delay)
            );
        }

        function scheduleRemove(id, delay = REMOVE_DELAY) {
            clearTimeout(timers.get(id));
            timers.set(
                id,
                setTimeout(() => {
                    remove(id);
                }, delay)
            );
        }

        function dismiss(id) {
            if (id) {
                clearTimeout(timers.get(id));
                timers.delete(id);
                remainingTimes.delete(id);
                timerDeadlines.delete(id);
                state.toasts = state.toasts.map((toast) =>
                    toast.id === id ? { ...toast, open: false } : toast
                );
                scheduleRemove(id);
                return;
            }
            for (const toast of state.toasts) {
                dismiss(toast.id);
            }
        }

        function update(id, patch) {
            state.toasts = state.toasts.map((toast) =>
                toast.id === id ? { ...toast, ...patch } : toast
            );
            if (patch.duration !== undefined) {
                const toast = state.toasts.find((entry) => entry.id === id);
                if (toast?.open && patch.duration > 0) {
                    remainingTimes.delete(id);
                    startDismissTimer(id, patch.duration);
                }
            }
        }

        function pause(id) {
            const deadline = timerDeadlines.get(id);
            if (!deadline) {
                return;
            }
            remainingTimes.set(id, Math.max(0, deadline - Date.now()));
            clearTimeout(timers.get(id));
            timers.delete(id);
            timerDeadlines.delete(id);
        }

        function resume(id) {
            const toast = state.toasts.find((entry) => entry.id === id);
            if (!toast || toast.open === false) {
                return;
            }
            if (timerDeadlines.has(id) || !remainingTimes.has(id)) {
                return;
            }
            const delay = remainingTimes.get(id) ?? toast.duration;
            remainingTimes.delete(id);
            if (delay > 0) {
                startDismissTimer(id, delay);
            }
        }

        function add(options = {}) {
            toastId += 1;
            const id = `toast-${toastId}`;
            const toast = {
                id,
                open: true,
                variant: options.variant || "default",
                title: options.title,
                description: options.description,
                action: options.action,
                actionLabel: options.actionLabel,
                actionAltText: options.actionAltText,
                className: options.className || "",
                closeLabel: options.closeLabel || "Dismiss notification",
                duration: options.duration ?? DEFAULT_DURATION,
                role: options.role,
            };
            const nextToasts = [toast, ...state.toasts].slice(0, TOAST_LIMIT);
            const retainedIds = new Set(nextToasts.map((entry) => entry.id));
            for (const existingToast of state.toasts) {
                if (!retainedIds.has(existingToast.id)) {
                    clearTimeout(timers.get(existingToast.id));
                    timers.delete(existingToast.id);
                    remainingTimes.delete(existingToast.id);
                    timerDeadlines.delete(existingToast.id);
                }
            }
            state.toasts = nextToasts;
            if (toast.duration > 0) {
                startDismissTimer(id, toast.duration);
            }
            return {
                id,
                dismiss: () => dismiss(id),
                pause: () => pause(id),
                resume: () => resume(id),
                update: (patch) => update(id, patch),
            };
        }

        return {
            state,
            add,
            dismiss,
            pause,
            resume,
            toast: add,
            update,
            clear: () => dismiss(),
        };
    },
};

registry.category("services").add("odx_toast", odxToastService);
