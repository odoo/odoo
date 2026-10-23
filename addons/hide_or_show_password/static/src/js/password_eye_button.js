/** @odoo-module **/

import { formatChar } from '@web/views/fields/formatters';
import { Component } from "@odoo/owl";

export class PasswordEyeButton extends Component {
    onClick(e) {
        e.stopPropagation();
        const { fieldName, fieldValue, fieldReadonly } = this.props;

        const parent = e.target.parentElement.parentElement
        var elementValue;
        if (fieldReadonly) {
            elementValue = parent.querySelector(`span[field-name='${fieldName}']`)
        } else {
            elementValue = parent.querySelector(`input[field-name='${fieldName}']`)
        }
        if (elementValue) {
            const elementType = elementValue.getAttribute('type')
            if (elementType === 'password') {
                this.toggleIconClass(e.target, true)
                elementValue.setAttribute('type', 'text')
                if (fieldReadonly) {
                    elementValue.innerHTML = fieldValue
                }
            } else {
                this.toggleIconClass(e.target, false)
                elementValue.setAttribute('type', 'password')
                if (fieldReadonly) {
                    elementValue.innerHTML = formatChar(fieldValue, { isPassword: true })
                }
            }
        }
    }
    
    toggleIconClass(element, active) {
        if (active) {
            element.classList.remove('fa-eye')
            element.classList.add('fa-eye-slash')
        } else {
            element.classList.remove('fa-eye-slash')
            element.classList.add('fa-eye')
        }
    }
}
PasswordEyeButton.template = "hide_or_show_password.PasswordEyeButton";
PasswordEyeButton.defaultProps = { isTranslatable: false };
PasswordEyeButton.props = {
    fieldName: { type: String },
    fieldReadonly: { type: Boolean },
    isTranslatable: { type: Boolean, optional: true },
    fieldValue: { type: String, optional: true },
};
