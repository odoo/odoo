odoo.define('web.daterangepicker.extensions', function () {
'use strict';

/**
 * Update date in input field when user change the date
 */
var clickDateFunction = daterangepicker.prototype.clickDate;
daterangepicker.prototype.clickDate = function (ev) {
    clickDateFunction.apply(this, arguments);
    this.element.trigger('clickDate.daterangepicker', this);
};

/**
 * Update time in input field when user change the time
 */
var timeChangedFunction = daterangepicker.prototype.timeChanged;
daterangepicker.prototype.timeChanged = function(ev) {
    timeChangedFunction.apply(this, arguments);
    this.element.trigger('timeChanged.daterangepicker', this);
};

});
