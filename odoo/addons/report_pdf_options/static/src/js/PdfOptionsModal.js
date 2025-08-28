/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class PdfOptionsModal extends Component {
    setup() {
        this.title = _t("What do you want to do?");
    }
    executePdfAction(option) {
        this.props.onSelectOption(option);
    }
}

PdfOptionsModal.template = "report_pdf_options.ButtonOptions";
PdfOptionsModal.components = { Dialog };