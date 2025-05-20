/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SynchronizeDialog extends Component {
    static template = "base_import.SynchronizeDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        confirm: Function,
    };

    setup() {
        this.state = useState({
            skip: 0,
            limit: 10,
        });
    }

    async onConfirm() {
        await this.props.confirm(this.state.skip, this.state.limit);
        this.props.close();
    }
}