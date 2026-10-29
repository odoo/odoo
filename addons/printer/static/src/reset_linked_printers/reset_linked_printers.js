import { Component, proxy, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { forgetLinkedPrinters, getAllLinkedPrinters } from "../linked_printers";

/**
 * Lists the reports whose printers are remembered in this browser, to forget
 * them: the printer dialog then opens again the next time they are printed.
 */
export class ResetLinkedPrinters extends Component {
    static template = "printer.ResetLinkedPrinters";
    static components = { Layout };
    props = useProps(standardActionServiceProps);

    setup() {
        this.state = proxy({ linkedPrinters: getAllLinkedPrinters() });
    }

    forget(reportName) {
        forgetLinkedPrinters(reportName);
        this.state.linkedPrinters = getAllLinkedPrinters();
    }
}

registry.category("actions").add("printer.reset_linked_printers", ResetLinkedPrinters);
