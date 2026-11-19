import { Plugin, signal } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { services } from "@web/core/services";

export class WebsiteFrontendOfflinePlugin extends Plugin {
    static id = OfflinePlugin.id;

    isOffline = signal(false);
    syncingORM = signal(false);

    setOffline() {}
    async checkConnection() {}
}

services.delete(OfflinePlugin);
services.add(WebsiteFrontendOfflinePlugin);
