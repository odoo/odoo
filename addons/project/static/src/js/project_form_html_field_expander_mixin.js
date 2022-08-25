/** @odoo-module **/

import { device } from 'web.config';

const FormHtmlFieldExpanderMixin = {
    bottomDistance: 0,
    fieldQuerySelector: '.o_xxl_form_view .oe_form_field.oe_form_field_html',
    on_attach_callback() {
        this._super(...arguments);
        this._fixDescriptionHeight();
    },
    _fixDescriptionHeight() {
        if (device.isMobile) return;

        const descriptionField = this.el.querySelector(this.fieldQuerySelector);
        if (descriptionField) {
            const editor = descriptionField.querySelector('.note-editable')
            const elementToResize = editor || descriptionField
            const minHeight = document.documentElement.clientHeight - elementToResize.getBoundingClientRect().top - this.bottomDistance;
            elementToResize.style.minHeight = `${minHeight}px`
        }
    },
    _updateView() {
        this._super(...arguments);
        this._fixDescriptionHeight();
    },
}

export default FormHtmlFieldExpanderMixin
