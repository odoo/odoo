/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, useRef } from "@odoo/owl";

class VerificationCodeWidget extends Component {
    static props = {
        ...standardFieldProps,
    };
    static template = "account_peppol.VerificationCodeWidget";

    setup() {
        super.setup();
        this.inputs = [];
        for (let i = 0; i < 6; i++) {
            this.inputs.push(useRef(`input_${i}`));
        }
    }

    /*
    overrides the default paste behaviour, so that if a value is pasted
    into one of the verification code fields, it's split between the input fields,
    so they can easily copy and paste the code they received via SMS.
    */
    onPaste(ev) {
        if (!ev.clipboardData?.items) {
            return;
        }
        ev.preventDefault();

        let pastedData = ev.clipboardData.getData('text').split('');
        let target = ev.target;
        for (let i = target.id; i < this.inputs.length; i++) {
            this.inputs[i].el.value = pastedData.shift() || null;
        }
    }

    // switch focus to the next input box once they enter
    // one digit and switch focus to the previous input box
    // if they press backspace
    onKeyUp(ev) {
        if (ev.target.value.length === 1 && ev.target.id < 5) {
            ev.target.nextElementSibling.focus();
        } else if (ev.key == 'Backspace' && ev.target.value === "" && ev.target.id > 0) {
            ev.target.previousElementSibling.focus();
        }
    }

    _save() {
        let verificationCode = [...this.inputs.map((i) => i.el.value)].join('');
        if (verificationCode.length === 6) {
            this.props.record.update({ verification_code: verificationCode });
        }
    }
}

registry.category("fields").add("verification_code", {
    component: VerificationCodeWidget,
    supportedTypes: ["char"],
});
