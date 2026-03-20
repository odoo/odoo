import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};

    setup() {
        this.offlineService = useService("offline");
        useEffect(this.env.redrawNavbar, () => [this.offlineService.offline]);
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });
