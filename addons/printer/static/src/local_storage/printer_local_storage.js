import { useState } from "@web/owl2/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart } from "@odoo/owl";

export const PRINTER_LINKED_TO_REPORT = `odoo-${odoo.info?.db}-report_printer_mapping`;

export function removePrinterReportIdFromBrowserLocalStorage(report_id) {
    const linkedPrinters = JSON.parse(browser.localStorage.getItem(PRINTER_LINKED_TO_REPORT));
    delete linkedPrinters[report_id];
    if (Object.keys(linkedPrinters).length === 0) {
        browser.localStorage.removeItem(PRINTER_LINKED_TO_REPORT);
    } else {
        browser.localStorage.setItem(PRINTER_LINKED_TO_REPORT, JSON.stringify(linkedPrinters));
    }
}

export function setReportIdInLocalStorage(report_id, value) {
    let linkedPrinters = JSON.parse(browser.localStorage.getItem(PRINTER_LINKED_TO_REPORT));
    if (linkedPrinters === null || typeof linkedPrinters !== "object") {
        linkedPrinters = {};
    }
    linkedPrinters[report_id] = value;
    browser.localStorage.setItem(PRINTER_LINKED_TO_REPORT, JSON.stringify(linkedPrinters));
}

class PrinterReportLocalStorage extends Component {
    static template = "printer.delete_printer";
    static props = { ...standardActionServiceProps };

    setup() {
        const linkedPrinters = JSON.parse(browser.localStorage.getItem(PRINTER_LINKED_TO_REPORT));
        this.state = useState({ reportList: linkedPrinters ? Object.keys(linkedPrinters) : [] });
        this.orm = useService("orm");
        onWillStart(async () => {
            this.state.reportList = await this.orm.searchRead("ir.actions.report", [
                ["id", "in", this.state.reportList],
            ]);
        });
    }
    removePrinterFromLocal(event, id) {
        removePrinterReportIdFromBrowserLocalStorage(id);
        this.state.reportList = this.state.reportList.filter((report) => report.id !== id);
    }
}

registry.category("actions").add("printer_delete_linked_devices_action", PrinterReportLocalStorage);
