/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { TextField, textField } from "@web/views/fields/text/text_field";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { usePopover } from "@web/core/popover/popover_hook";

import { useRef } from "@odoo/owl";


export class WhatsappVariablesTextField extends TextField {
    static template = "whatsapp.WhatsappVariablesTextField";
    static components = { ...TextField.components };
    setup() {
        super.setup();
        this.textareaRef = useRef('textarea');
        this.variablesButton = useRef('variablesButton');
        this.popover = usePopover(Tooltip, { animation: false, position: "left" });
    }

    _onClickAddVariables() {
        const originalContent = this.textareaRef.el.value;
        const start = this.textareaRef.el.selectionStart;
        const end = this.textareaRef.el.selectionEnd;

        const matches = Array.from(originalContent.matchAll(/{{(\d+)}}/g));
        const integerList = matches.map(match => parseInt(match[1]));
        const nextVariable = Math.max(...integerList, 0) + 1;

        if (nextVariable > 10){
            // Show tooltip
            this.popover.open(this.variablesButton.el, { tooltip: _t("You can set a maximum of 10 variables.") });
            browser.setTimeout(this.popover.close, 2600);
            return;
        }

        const separator = originalContent.slice(0, start) ? ' ' : '';
        this.textareaRef.el.value = originalContent.slice(0, start) + separator + '{{' + nextVariable + '}}' + originalContent.slice(end, originalContent.length);
        // Trigger onInput from input_field hook to set field as dirty
        this.textareaRef.el.dispatchEvent(new InputEvent("input"));
        // Keydown on "enter" serves to both commit the changes in input_field and trigger onchange for some fields
        this.textareaRef.el.dispatchEvent(new KeyboardEvent("keydown", {key: 'Enter'}));
        this.textareaRef.el.focus();
        const newCursorPos = start + separator.length + nextVariable.toString().length + 4; // 4 is the number of brackets {{ }}
        this.textareaRef.el.setSelectionRange(newCursorPos, newCursorPos);
    }
}

export const whatsappVariablesTextField = {
    ...textField,
    component: WhatsappVariablesTextField,
    additionalClasses: [...(textField.additionalClasses || []), "o_field_text"],
};

registry.category("fields").add("whatsapp_text_variables", whatsappVariablesTextField);
