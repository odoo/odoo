import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;
export class OutdatedPageWatcherService {
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    setup(env, { bus_service, multi_tab, notification }) {
        this.notification = notification;
        const vacuumInfo = multi_tab.getSharedValue("bus.autovacuum_info");
        this.lastAutovacuumDt = vacuumInfo ? deserializeDateTime(vacuumInfo.lastcall) : null;
        this.nextAutovacuumDt = vacuumInfo ? deserializeDateTime(vacuumInfo.nextcall) : null;
        this.lastDisconnectDt = null;
        this.closeNotificationFn;
        bus_service.addEventListener("disconnect", () => (this.lastDisconnectDt = DateTime.now()));
        bus_service.addEventListener("reconnect", async () => {
            if (!multi_tab.isOnMainTab() || !this.lastDisconnectDt) {
                return;
            }
            if (!this.lastAutovacuumDt || DateTime.now() >= this.nextAutovacuumDt) {
                const { lastcall, nextcall } = await rpc(
                    "/bus/get_autovacuum_info",
                    {},
                    { silent: true }
                );
                this.lastAutovacuumDt = deserializeDateTime(lastcall);
                this.nextAutovacuumDt = deserializeDateTime(nextcall);
                multi_tab.setSharedValue("bus.autovacuum_info", { lastcall, nextcall });
            }
            if (this.lastDisconnectDt <= this.lastAutovacuumDt) {
                this.showOutdatedPageNotification();
            }
        });
        multi_tab.bus.addEventListener("shared_value_updated", ({ detail: { key, newValue } }) => {
            if (key !== "bus.autovacuum_info") {
                return;
            }
            const infos = JSON.parse(newValue);
            this.lastAutovacuumDt = deserializeDateTime(infos.lastcall);
            this.nextAutovacuumDt = deserializeDateTime(infos.nextcall);
            if (this.lastDisconnectDt <= this.lastAutovacuumDt) {
                this.showOutdatedPageNotification();
            }
        });
    }

    showOutdatedPageNotification() {
        this.closeNotificationFn?.();
        this.closeNotificationFn = this.notification.add(
            _t("Save your work and refresh to get the latest updates and avoid potential issues."),
            {
                title: _t("The page is out of date"),
                type: "warning",
                sticky: true,
                buttons: [
                    {
                        name: _t("Refresh"),
                        primary: true,
                        onClick: () => browser.location.reload(),
                    },
                ],
            }
        );
    }
}

export const outdatedPageWatcherService = {
    dependencies: ["bus_service", "multi_tab", "notification"],
    start(env, services) {
        return new OutdatedPageWatcherService(env, services);
    },
};

registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
