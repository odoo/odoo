import { EventBus, Plugin, t, useConfig, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { useEnv } from "@web/owl2/utils";

export class GlobalBusPlugin extends Plugin {
    bus = useConfig(
        "bus",
        t.instanceOf(EventBus).optional(() => new EventBus())
    );
}
services.add(GlobalBusPlugin);

// TODO: temporary bridge for the services-to-plugins migration, remove once
// `env.bus` is no longer used anywhere in the codebase.
export class EnvBusBridgePlugin extends Plugin {
    static sequence = 1;

    env = useEnv();
    globalBus = usePlugin(GlobalBusPlugin);

    setup() {
        this.env.bus = this.globalBus.bus;
    }
}
services.add(EnvBusBridgePlugin);
