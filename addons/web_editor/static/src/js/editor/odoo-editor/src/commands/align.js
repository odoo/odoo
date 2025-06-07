/** @odoo-module **/
import { childNodeIndex, isBlock } from '../utils/utils.js';

Text.prototype.oAlign = function (offset, mode) {
    this.parentElement.oAlign(childNodeIndex(this), mode);
};
/**
 * This does not check for command state
 * @param {*} offset
 * @param {*} mode 'left', 'right', 'center' or 'justify'
 */
HTMLElement.prototype.oAlign = function (offset, mode) {
    if (!isBlock(this)) {
        return this.parentElement.oAlign(childNodeIndex(this), mode);
    }
    const { textAlign } = getComputedStyle(this);
    const alreadyAlignedLeft = textAlign === 'start' || textAlign === 'left';
    const shouldApplyStyle = !(alreadyAlignedLeft && mode === 'left');
    if (shouldApplyStyle) {
        this.style.textAlign = mode;
    }
};
