import { registry } from "@web/core/registry";
import { ProfilingItem } from "./profiling_item";
import { session } from "@web/session";
import { profilingSystrayItem } from "./profiling_systray_item";

import { EventBus, reactive } from "@odoo/owl";

const systrayRegistry = registry.category("systray");

export const profilingService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        // Only set up profiling when in debug mode
        if (!env.debug) {
            return;
        }

        function notify() {
            if (systrayRegistry.contains("web.profiling") && state.isEnabled === false) {
                systrayRegistry.remove("web.profiling");
            }
            if (!systrayRegistry.contains("web.profiling") && state.isEnabled === true) {
                systrayRegistry.add("web.profiling", profilingSystrayItem, { sequence: 99 });
            }
            bus.trigger("UPDATE");
        }

        const state = reactive(
            {
                session: session.profile_session || false,
                collectors: session.profile_collectors || ["sql", "traces_async"],
                params: session.profile_params || {},
                get isEnabled() {
                    return Boolean(state.session);
                },
            },
            notify
        );

        const bus = new EventBus();
        notify();

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
            if (resp.type) {
                // most likely an "ir.actions.act_window"
                env.services.action.doAction(resp);
            } else {
                state.session = resp.session;
                state.collectors = resp.collectors;
                state.params = resp.params;
            }
        }

        function profilingItem() {
            return {
                type: "component",
                Component: ProfilingItem,
                props: { bus },
                sequence: 570,
                section: "tools",
            };
        }

        registry.category("debug").category("default").add("profilingItem", profilingItem);

        return {
            state,
            async toggleProfiling() {
                await setProfiling({ profile: !state.isEnabled });
            },
            async toggleCollector(collector) {
                const nextCollectors = state.collectors.slice();
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
