odoo.define('website_sale.payment', function (require) {
"use strict";

$(document).ready(function () {
    // If option is enable
    if ($("#checkbox_cgv").length) {
      $("#checkbox_cgv").click(function() {
        $("div.oe_sale_acquirer_button").find('input, button').prop("disabled", !this.checked);
      });
    }
});

});
