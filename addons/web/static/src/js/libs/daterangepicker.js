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

});
