/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useKEProxy } from "./ke_proxy_hook";
import { Component } from "@odoo/owl";


export class KEProxyDialog extends Component {
    setup() {
        // prevent the escape key from exiting the dialog
        useHotkey("escape", () => {});
        this.action = useService("action");
        this.sender = useKEProxy({ onAllSent: this.props.close });
        this.state = this.sender.state;
        this.sender.postInvoices(this.props.invoices);
    };
}

KEProxyDialog.template = "l10n_ke_edi_tremol.KEProxyDialog";
KEProxyDialog.components = { Dialog };
KEProxyDialog.props = {
    invoices: Object,
    close: Function,
};
