import { Component, useRef } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BusLogsMenuItem extends Component {
    static components = { DropdownItem };
    static template = "bus.BusLogsMenuItem";
    static props = {};

    setup() {
        this.busLogsService = useService("bus.logs_service");
        this.downloadButton = useRef("downloadButton");
    }

    onClickToggle() {
        this.busLogsService.toggleLogging();
    }

    onClickDownload() {
        this.env.services.bus_service.downloadLogs();
    }
}

registry
    .category("debug")
    .category("default")
    .add("bus.download_logs", () => ({
        Component: BusLogsMenuItem,
        sequence: 550,
        section: "tools",
        type: "component",
    }));
