odoo.define("sale_stock.tour", function (require) {
    "use strict";

    var tour = require('web_tour.tour');
    require('sale.tour');

    var quotation_product_selected_step_index = _.findIndex(tour.tours.sale_product_configurator_tour.steps, function (step) {
        return (step.id === "quotation_product_selected");
    });

    tour.tours.sale_product_configurator_tour.steps[quotation_product_selected_step_index].run = function (actions) {
        actions.auto();
    };

    tour.tours.sale_product_configurator_tour.steps.splice(quotation_product_selected_step_index+1, 0, {
        trigger: ".o_dialog_warning + .modal-footer .btn-primary",
        auto: true,
        run: function (actions) {
            actions.auto('.o_dialog_warning + .modal-footer .btn-primary');
        }
    }, {
        trigger: ".o_dialog_warning + .modal-footer .btn-primary",
        auto: true,
        run: function (actions) {
            actions.auto('.o_dialog_warning + .modal-footer .btn-primary');
        }
    }, {
        trigger: "body:not(:has(.o_dialog_warning))",
        auto: true,
        in_modal: false,
        run: function (actions) {
            if ($('.modal-footer .btn-primary').length){
                actions.auto('.modal-footer .btn-primary');
            }
        },
    });

    // Check if sale_management is installed since sale_stock is adding an extra
    // step to add to SO (not enough inventory)
    if ('sale.product_configurator_pricelist_tour' in odoo.__DEBUG__.services) {
        var steps = tour.tours.sale_product_configurator_pricelist_tour.steps;
        for (var k=0; k<steps.length; k++) {
            if (steps[k].content === "add to SO") {
                steps.splice(k+1, 0, {
                    content: "click in modal on ok button",
                    trigger: '.modal-footer button:contains("Ok")',
                });
            }
        }
    }
});
