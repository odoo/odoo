/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('order_lunch_tour', {
    url: "/web",
    test: true,
    steps: () => [{
    trigger: 'a[data-menu-xmlid="lunch.menu_lunch"]',
    content: _t("Start by accessing the lunch app."),
    position: 'bottom',
    run: "click",
},
{
    trigger: ".o_search_panel_filter_value .form-check-input",
    content: _t("Restrict your search using filters"),
    position: 'bottom',
    run: "click",
},
{
    trigger: ".o_search_panel_filter_value .form-check-input:checked",
},
{
    trigger: "div[role=article]",
    content: _t("Click on a product you want to order and is available."),
    position: 'bottom',
    run: "click",
},
{
    trigger: `button[name="add_to_cart"]`,
},
{
    trigger: 'textarea[name="note"]',
    content: _t("Add additionnal information about your order."),
    position: 'bottom',
    run: "edit allergy to peanuts",
},
{
    trigger: 'button[name="add_to_cart"]',
    content: _t("Add your order to the cart."),
    position: 'bottom',
    run: "click",
},
{
    trigger: '.o_lunch_widget_order_button',
    content: _t("Validate your order"),
    position: 'left',
    run: 'click',
}]});
