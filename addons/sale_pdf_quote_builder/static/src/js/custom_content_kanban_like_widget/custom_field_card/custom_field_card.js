import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useAutoresize } from "@web/core/utils/autoresize";

export class CustomFieldCard extends Component {
    static template = "sale_pdf_quote_builder.customFieldCard";
    static props = {
        name: String,
        value: String,
        onChange: Function,
    };

    setup() {
        this.customFormFieldTextAreaRef = useRef('customFieldCardTextArea');
        this.placeholder = _t("Click to write content for the PDF quote...");
        useAutoresize(this.customFormFieldTextAreaRef);
    }

    expandTextArea(ev) {
        const textarea = ev.target;
        textarea.style.height = textarea.scrollHeight+'px';
    }
}
