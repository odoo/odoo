/** @odoo-module */

import { Component, useState } from  "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ContentEditionDialog extends Component {
    static components = { Dialog };
    static template = "salePdfQuoteBuilder.contentEditionDialog";
    static props = {
        "*": true,  //TODO edm
        close: Function, // This is the close from the env of the Dialog Component
    };


    setup() {
        this.title = _t("Customize your Quote");
        this.state = useState({
            ...this.props
        })
        this.orm = useService("orm");

    }

    /**
     * Confirm the current content.
     *
     * @return {undefined}
     */
    async onConfirm() {
        this.props.close();
    }
}
