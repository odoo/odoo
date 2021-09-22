/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ProfilingItem } from "./profiling_item";
import { session } from "@web/session";

const { core } = owl;

const profilingService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const state = {
            session: session.profile_session || false,
            collectors: session.profile_collectors || ["sql", "traces_async"],
            params: session.profile_params || {},
            get isEnabled() {
                return Boolean(state.session);
            },
        };
        const bus = new core.EventBus();

        let recordingIcon = null;
        function updateDebugIcon() {
            const debugItem = document.querySelector(".o_main_navbar .o_debug_manager .fa-bug");
            if (state.isEnabled) {
                recordingIcon = document.createElement("span");
                recordingIcon.classList.add("o_recording", "text-danger", "fa", "fa-circle");
                debugItem.appendChild(recordingIcon);
            } else if (recordingIcon) {
                debugItem.removeChild(recordingIcon);
                recordingIcon = null;
            }
        }

        if (env.debug) {
            env.bus.on("WEB_CLIENT_READY", null, updateDebugIcon);
        }

        async function setProfiling(params) {
            const kwargs = Object.assign(
                {
                    collectors: state.collectors,
                    params: state.params,
                    profile: state.isEnabled,
                },
                params
            );
            const resp = await orm.call("ir.profile", "set_profiling", [], kwargs);
            if (resp.type) {  // most likely an "ir.actions.act_window"
                env.services.action.doAction(resp);
            } else {
                state.session = resp.session;
                state.collectors = resp.collectors;
                state.params = resp.params;
                bus.trigger("UPDATE");
                updateDebugIcon();
            }
        }

        function profilingSeparator() {
            return {
                type: "separator",
                sequence: 500,
            };
        }

        function profilingItem() {
            return {
                type: "component",
                Component: ProfilingItem,
                props: { bus },
                sequence: 510,
            };
        }

        registry
            .category("debug")
            .category("default")
            .add("profilingSeparator", profilingSeparator)
            .add("profilingItem", profilingItem);

        return {
            state,
            async toggleProfiling() {
                await setProfiling({ profile: !state.isEnabled });
            },
            async toggleCollector(collector) {
                let nextCollectors = state.collectors.slice();
                const index = nextCollectors.indexOf(collector);
                if (index >= 0) {
                    nextCollectors.splice(index, 1);
                } else {
                    nextCollectors.push(collector);
                }
                await setProfiling({ collectors: nextCollectors });
            },
            async setParam(key, value) {
                const nextParams = Object.assign({}, state.params);
                nextParams[key] = value;
                await setProfiling({ params: nextParams });
            },
            isCollectorEnabled(collector) {
                return state.collectors.includes(collector);
            },
        };
    },
};

registry.category("services").add("profiling", profilingService);
