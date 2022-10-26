/** @odoo-module **/

import { _t } from 'web.core';
import tour from 'web_tour.tour';

tour.register('order_lunch_tour', {
    url: "/web",
    test: true,
}, [{
    trigger: 'a[data-menu-xmlid="lunch.menu_lunch"]',
    content: _t("Start by accessing the lunch app."),
    position: 'bottom',
},
{
    trigger: ".o_search_panel_filter_value .form-check-input",
    content: _t("Restrict your search using filters"),
    position: 'bottom',
},
{
    trigger: "div[role=article]",
    extra_trigger: '.o_search_panel_filter_value .form-check-input:checked',
    content: _t("Click on a product you want to order and is available."),
    position: 'bottom',
},
{
    trigger: 'textarea[name="note"]',
    extra_trigger: 'button[name="add_to_cart"]',
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
    trigger: '.o_lunch_widget_order_button',
    content: _t("Validate your order"),
    position: 'left',
    run: 'click',
}]);
