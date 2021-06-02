/** @odoo-module alias=point_of_sale.TextAreaPopup **/

import PosComponent from 'point_of_sale.PosComponent';
import Draggable from 'point_of_sale.Draggable';
import { _t } from 'web.core';
const { useState, useRef } = owl.hooks;

class TextAreaPopup extends PosComponent {
    /**
     * @param {Object} props
     * @param {string} props.startingValue
     */
    constructor() {
        super(...arguments);
        this.state = useState({ inputValue: this.props.startingValue });
        this.inputRef = useRef('input');
    }
    mounted() {
        this.inputRef.el.focus();
    }
}
TextAreaPopup.components = { Draggable };
TextAreaPopup.template = 'point_of_sale.TextAreaPopup';
TextAreaPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: '',
    body: '',
    startingValue: '',
};

export default TextAreaPopup;
