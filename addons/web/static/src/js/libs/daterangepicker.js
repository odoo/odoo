odoo.define('web.daterangepicker.extensions', function () {
'use strict';

/**
 * Don't allow user to select off days(Dates which are out of current calendar).
 */
var clickDateFunction = daterangepicker.prototype.clickDate;
daterangepicker.prototype.clickDate = function (ev) {
    if (!$(ev.target).hasClass('off')) {
        clickDateFunction.apply(this, arguments);
    }
};

/**
 * Override to open up or down based on top/bottom space in window.
 */
const moveFunction = daterangepicker.prototype.move;
daterangepicker.prototype.move = function () {
    const offset = this.element.offset();
    this.drops = this.container.height() < offset.top ? 'up' : 'down';
    moveFunction.apply(this, arguments);
};

});
