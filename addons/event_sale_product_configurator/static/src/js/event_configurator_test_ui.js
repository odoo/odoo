odoo.define("event_sale_product_configurator.event_configurator_tour", function (require) {
"use strict";
/**
 * We need to replace the trigger of the product selection step because the
 * "sale_product_configurator" module replaces the "product_id" field with
 * a "product_template_id" field.
 */
var tour = require('web_tour.tour');
require('event.event_configurator_tour');

var productSelectionStepIndex = _.findIndex(tour.tours.event_configurator_tour.steps, function (step) {
    return (step.id === 'product_selection_step');
});

var productSelectionStep = tour.tours.event_configurator_tour.steps[productSelectionStepIndex];
productSelectionStep.trigger = 'div[name="product_template_id"] input';
productSelectionStep.run = function (){
    var $input = $('div[name="product_template_id"] input');
    $input.click();
    $input.val('EVENT');
    // fake keydown to trigger search
    var keyDownEvent = jQuery.Event("keydown");
    keyDownEvent.which = 42;
    $input.trigger(keyDownEvent);
};

});
