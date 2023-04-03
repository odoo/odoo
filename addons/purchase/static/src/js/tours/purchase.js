/** @odoo-module **/

import core from "web.core";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

var _t = core._t;
import PurchaseAdditionalTourSteps from "purchase.purchase_steps";

registry.category("web_tour.tours").add('purchase_tour' , {
    url: "/web",
    sequence: 40,
    steps: [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="purchase.menu_purchase_root"]',
    content: _t("Let's try the Purchase app to manage the flow from purchase to reception and invoice control."),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="purchase.menu_purchase_root"]',
    content: _t("Let's try the Purchase app to manage the flow from purchase to reception and invoice control."),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_purchase_order",
    content: _t("Let's create your first request for quotation."),
    position: "bottom",
}, {
    trigger: ".o_form_editable .o_field_many2one[name='partner_id']",
    extra_trigger: ".o_purchase_order",
    content: _t("Search a vendor name, or create one on the fly."),
    position: "bottom",
    run: function (actions) {
        actions.text("Agrolait", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".o_field_many2one[name='partner_id'] .o_external_button",
    content: _t("Add some products or services to your quotation."),
    position: "bottom",
}, {
    trigger: ".o_field_widget[name=product_id], .o_field_widget[name=product_template_id]",
    extra_trigger: ".o_purchase_order",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: function (actions) {
        var $input = this.$anchor.find('input');
        actions.text("DESK0001", $input.length === 0 ? this.$anchor : $input);
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        this.$anchor.trigger(keyDownEvent);
        var $descriptionElement = $('.o_form_editable textarea[name="name"]');
        // when description changes, we know the product has been created
        $descriptionElement.change(function () {
            $descriptionElement.addClass('product_creation_success');
        });
    },
}, {
    trigger: '.ui-menu.ui-widget .ui-menu-item a:contains("DESK0001")',
    auto: true,
}, {
    trigger: '.o_form_editable textarea[name="name"].product_creation_success',
    auto: true,
    run: function () {} // wait for product creation
}, {
    trigger: ".o_form_editable input[name='product_qty'] ",
    extra_trigger: ".o_purchase_order",
    content: _t("Indicate the product quantity you want to order."),
    position: "right",
    run: 'text 12.0'
},
...stepUtils.statusbarButtonsSteps('Send by Email', _t("Send the request for quotation to your vendor."), ".o_statusbar_buttons button[name='action_rfq_send']"),
{
    trigger: ".modal-content",
    auto: true,
    run: function(actions){
        // Check in case user must add email to vendor
        var $input = $(".modal-content input[name='email']");
        if ($input.length) {
            actions.text("agrolait@example.com", $input);
            actions.click($(".modal-footer button"));
        }
    }
}, {
    trigger: ".modal-footer button[name='action_send_mail']",
    extra_trigger: ".modal-footer button[name='action_send_mail']",
    content: _t("Send the request for quotation to your vendor."),
    position: "left",
    run: 'click',
}, {
    trigger: ".o_field_widget [name=price_unit]",
    extra_trigger: ".o_purchase_order",
    content: _t("Once you get the price from the vendor, you can complete the purchase order with the right price."),
    position: "right",
    run: 'text 200.00'
}, {
    auto: true,
    trigger: ".o_purchase_order",
    run: 'click',
}, ...stepUtils.statusbarButtonsSteps('Confirm Order', _t("Confirm your purchase.")),
...new PurchaseAdditionalTourSteps()._get_purchase_stock_steps(),
]});
