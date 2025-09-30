import { Component } from "@odoo/owl";
import { registry } from "../registry";
import { useService } from "../utils/hooks";

class OfflineSystray extends Component {
    static template = "web.offlineSystray";
    static props = {};

    setup() {
        this.offlineService = useService("offline");
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("OfflineSystrayItem", offlineSystrayItem, { sequence: 1000 });
