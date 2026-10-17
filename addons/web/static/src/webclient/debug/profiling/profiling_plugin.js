import { computed, Plugin, signal, useEffect, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { profilingSystrayItem } from "@web/webclient/debug/profiling/profiling_systray_item";

const systrayRegistry = registry.category("systray");

export class ProfilingPlugin extends Plugin {
    /** @private */
    debugMode = usePlugin(DebugModePlugin);
    /** @private */
    action = usePlugin(ActionPlugin);
    /** @private */
    orm = usePlugin(ORM);

    session = signal(session.profile_session || false);
    collectors = signal.Array(session.profile_collectors || ["sql", "traces_async"]);
    params = signal.Object(session.profile_params || {});
    isEnabled = computed(() => Boolean(this.session()));

    setup() {
        // Only set up profiling when in debug mode
        if (!this.debugMode.isActive()) {
            return;
        }
        useEffect(() => {
            const isEnabled = this.isEnabled();
            if (systrayRegistry.contains("web.profiling") && !isEnabled) {
                systrayRegistry.remove("web.profiling");
            }
            if (!systrayRegistry.contains("web.profiling") && isEnabled) {
                systrayRegistry.add("web.profiling", profilingSystrayItem, { sequence: 99 });
            }
        });
    }

    async toggleProfiling() {
        await this.setProfiling({ profile: !this.isEnabled() });
    }

    async toggleCollector(collector) {
        const nextCollectors = this.collectors().slice();
        const index = nextCollectors.indexOf(collector);
        if (index >= 0) {
            nextCollectors.splice(index, 1);
        } else {
            nextCollectors.push(collector);
        }
        await this.setProfiling({ collectors: nextCollectors });
    }

    async setParam(key, value) {
        const nextParams = Object.assign({}, this.params());
        nextParams[key] = value;
        await this.setProfiling({ params: nextParams });
    }

    isCollectorEnabled(collector) {
        return this.collectors().includes(collector);
    }

    /** @private */
    async setProfiling(params) {
        const kwargs = Object.assign(
            {
                collectors: this.collectors(),
                params: this.params(),
                profile: this.isEnabled(),
            },
            params
        );
        const resp = await this.orm.call("ir.profile", "set_profiling", [], kwargs);
        if (resp.type) {
            // most likely an "ir.actions.act_window"
            this.action.doAction(resp);
        } else {
            this.session.set(resp.session);
            this.collectors.set(resp.collectors);
            this.params.set(resp.params);
        }
    }
}

services.add(ProfilingPlugin);
