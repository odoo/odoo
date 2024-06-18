/** @odoo-module */

import { Component, useState } from  "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { FilesList } from "@sale_pdf_quote_builder/js/files_list/files_list";

export class UpdateIncludedPdfDialog extends Component {
    static components = { Dialog, FilesList };
    static template = "salePdfQuoteBuilder.updateIncludedPdfDialog";
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
     * Confirm the current setup.
     *
     * @return {undefined}
     */
    async onConfirm() {
        let selected_lines_pdf = {}
        for (const line of this.props.lines) {
            selected_lines_pdf[line.id] = line.files.filter(
                files => files.is_selected
            ).map(files => files.id)
        }
        let selected_pdf = {
            'header': this.props.headers.files.filter(
                files => files.is_selected
            ).map(files => files.id),
            'lines': selected_lines_pdf,
            'footer': this.props.footers.files.filter(
                files => files.is_selected
            ).map(files => files.id),
        }
        await this.orm.call(
            'sale.order', 'save_included_pdf', [this.props.sale_order_id, selected_pdf]
        )
        this.props.close();
    }
}
