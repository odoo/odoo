import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('order_lunch_tour', {
    url: "/odoo",
    steps: () => [
    stepUtils.showAppsMenuItem(),
{
    trigger: '.o_app[data-menu-xmlid="lunch.menu_lunch"]',
    content: _t("Start by accessing the lunch app."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    content:"click on location",
    trigger: ".lunch_location .o_input_dropdown input",
    run: 'click'
},
{
    content: "Pick 'Farm 1' option",
    trigger: '.dropdown-item:contains("Farm 1")',
    run: "click",
},
{
    trigger: '.lunch_location input:value("Farm 1")',
},
{
    trigger: ".o_kanban_record",
    content: _t("Click on a product you want to order and is available."),
    run: 'click'
},
{
    trigger: 'textarea[id="note_0"]',
    content: _t("Add additionnal information about your order."),
    tooltipPosition: 'bottom',
    run: "edit allergy to peanuts",
},
{
    trigger: 'button[name="add_to_cart"]',
    content: _t("Add your order to the cart."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: 'button:contains("Order Now")',
    content: _t("Validate your order"),
    tooltipPosition: 'left',
    run: 'click',
}, {
    trigger: ".o_lunch_widget_line li[name='o_lunch_order_line'] .badge:contains('Ordered')",
    content: 'Check that order is ordered',
}]});
