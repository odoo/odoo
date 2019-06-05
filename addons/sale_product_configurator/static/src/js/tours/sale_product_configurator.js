odoo.define("sale_product_configurator.tour", function (require) {
"use strict";
/**
 * We need to replace the trigger of the product selection step because the
 * "sale_product_configurator" module replaces the "product_id" field with
 * a "product_template_id" field.
 */
var tour = require('web_tour.tour');
require('sale.tour');

var productSelectionStepIndex = _.findIndex(tour.tours.sale_tour.steps, function (step) {
    return (step.id === 'product_selection_step');
});

var productSelectionStep = tour.tours.sale_tour.steps[productSelectionStepIndex];
productSelectionStep.trigger = ".o_form_editable .o_field_many2one[name='product_template_id']";

});
