import { useRef } from "@web/owl2/utils";
import { Component, props, signal, t, useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useAutoresize } from "@web/core/utils/autoresize";

export class CustomFieldCard extends Component {
    static template = "sale_pdf_quote_builder.customFieldCard";
    props = props({
        name: t.string(),
        value: t.string(),
        onChange: t.function(),
        readonly: t.boolean().optional(),
    });

    setup() {
        this.value = signal(this.props.value || "");
        useEffect(() => this.value.set(this.props.value || ""));
        this.customFormFieldTextAreaRef = useRef('customFieldCardTextArea');
        this.placeholder = _t("Click to write content for the PDF quote...");
        useAutoresize(this.customFormFieldTextAreaRef);
    }

    expandTextArea(ev) {
        const textarea = ev.target;
        textarea.style.height = textarea.scrollHeight+'px';
    }
}
