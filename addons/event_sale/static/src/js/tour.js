odoo.define("event_sale.tour", function (require) {
    "use strict";

    var tour = require('web_tour.tour');
    require('sale.tour');

    var step_index = _.findIndex(tour.tours.sale_tour.steps, function (step) {
        return (step.id === "form_button_save_clicked");
    });
    tour.tours.sale_tour.steps.splice(step_index, 0, {
        trigger: ".modal-dialog .modal-footer .btn-primary:contains('Save & Close')",
    });
});
