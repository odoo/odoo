/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('order_lunch_tour', {
    url: "/web",
    test: true,
    steps: () => [
    stepUtils.showAppsMenuItem(),
{
    trigger: '.o_app[data-menu-xmlid="lunch.menu_lunch"]',
    content: _t("Start by accessing the lunch app."),
    position: 'bottom',
},
{
    content:"click on location",
    trigger: ".lunch_location .o_input_dropdown input",
    run: 'click'
},
{
    content: "Pick 'Farm 1' option",
    trigger: '.o_input_dropdown a:contains(Farm 1)',
},
{
    trigger: '.lunch_location input:propValueContains(Farm 1)',
    run: () => {},  // wait for article to be correctly loaded
},
{
    trigger: "div[role=article] .oe_kanban_global_click",
    content: _t("Click on a product you want to order and is available."),
    run:'click',
},
{
    trigger: 'textarea[id="note_0"]',
    content: _t("Add additionnal information about your order."),
    position: 'bottom',
    run: 'text allergy to peanuts',
},
{
    trigger: 'button[name="add_to_cart"]',
    content: _t("Add your order to the cart."),
    position: 'bottom',
},
{
    trigger: 'button:contains("Order Now")',
    content: _t("Validate your order"),
    position: 'left',
    run: 'click',
}]});
