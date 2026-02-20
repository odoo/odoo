import { useLayoutEffect } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};

    setup() {
        this.offlineService = useService("offline");
        useLayoutEffect(this.env.redrawNavbar, () => [this.offlineService.offline]);
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });
