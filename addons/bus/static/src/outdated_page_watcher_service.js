import { registry } from "@web/core/registry";

export class OutdatedPageWatcherService {
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").ServiceFactories>} services
     */
    setup(env, { bus_service, multi_tab, notification }) {
        this.notification = notification;
        this.multi_tab = multi_tab;
    }

    async checkHasMissedNotifications() {
        return false;
    }

    showOutdatedPageNotification() {}
}

export const outdatedPageWatcherService = {
    dependencies: ["bus_service", "multi_tab", "notification"],
    start(env, services) {
        return new OutdatedPageWatcherService(env, services);
    },
};

registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
