odoo.define('website_sale.payment', function (require) {
"use strict";

$(document).ready(function () {
    // If option is enable
    if ($("#checkbox_cgv").length) {
      $("#checkbox_cgv").change(function() {
        $("button#o_payment_form_pay").prop("disabled", !this.checked);
      });
      $('#checkbox_cgv').trigger('change');
    }
});

});
