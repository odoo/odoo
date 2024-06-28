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
        let name = this.props.document_type == 'header_footer'
            ? _("Header or footer / %s", this.props.formField)
            : _t("Product / %s", this.props.formField)
        this.title = _t("Edit: %s", name);
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
        await this.orm.call(
            'sale.order', 'save_new_custom_content', [
                this.props.saleOrderId,
                this.props.documentType,
                this.props.formField,
                this.props.content,
            ]
        )

        this.props.close();
    }
}
