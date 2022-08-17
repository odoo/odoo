odoo.define('sale.tour', function(require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

const { markup } = owl;

tour.register("sale_tour", {
    url: "/web",
    rainbowMan: false,
    sequence: 20,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
    content: _t("Open Sales app to send your first quotation in a few clicks."),
    position: "right",
    edition: "community"
}, {
    trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
    content: _t("Open Sales app to send your first quotation in a few clicks."),
    position: "bottom",
    edition: "enterprise"
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_base_onboarding_company]',
    extra_trigger: ".o_sale_order",
    content: _t("Start by checking your company's data."),
    position: "bottom",
}, {
    trigger: ".modal-content button[name='action_save_onboarding_company_step']",
    content: _t("Looks good. Let's continue."),
    position: "left",
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_base_document_layout]',
    extra_trigger: ".o_sale_order",
    content: _t("Customize your quotes and orders."),
    position: "bottom",
}, {
    trigger: "button[name='document_layout_save']",
    extra_trigger: ".o_sale_order",
    content: _t("Good job, let's continue."),
    position: "top", // dot NOT move to bottom, it would cause a resize flicker
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_sale_onboarding_payment_provider]',
    extra_trigger: ".o_sale_order",
    content: _t("To speed up order confirmation, we can activate electronic signatures or payments."),
    position: "bottom",
}, {
    trigger: "button[name='add_payment_methods']",
    extra_trigger: ".o_sale_order",
    content: _t("Lets keep electronic signature for now."),
    position: "bottom",
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_sale_onboarding_sample_quotation]',
    extra_trigger: ".o_sale_order",
    content: _t("Now, we'll create a sample quote."),
    position: "bottom",
}]);

tour.register("sale_quote_tour", {
        url: "/web#action=sale.action_quotations_with_onboarding&view_type=form",
        rainbowMan: true,
        rainbowManMessage: markup(_t("<b>Congratulations</b>, your first quotation is sent!<br>Check your email to validate the quote.")),
        sequence: 30,
    }, [{
        trigger: ".o_form_editable .o_field_many2one[name='partner_id']",
        extra_trigger: ".o_sale_order",
        content: _t("Write a company name to create one, or see suggestions."),
        position: "right",
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
        content: _t("Click here to add some products or services to your quotation."),
        position: "bottom",
    }, {
        trigger: ".o_field_widget[name='product_id'], .o_field_widget[name='product_template_id']",
        extra_trigger: ".o_sale_order",
        content: _t("Select a product, or create a new one on the fly."),
        position: "right",
        run: function (actions) {
            var $input = this.$anchor.find("input");
            actions.text("DESK0001", $input.length === 0 ? this.$anchor : $input);
            // fake keydown to trigger search
            var keyDownEvent = jQuery.Event("keydown");
            keyDownEvent.which = 42;
            this.$anchor.trigger(keyDownEvent);
            var $descriptionElement = $(".o_form_editable textarea[name='name']");
            // when description changes, we know the product has been created
            $descriptionElement.change(function () {
                $descriptionElement.addClass("product_creation_success");
            });
        },
        id: "product_selection_step"
    }, {
        trigger: ".ui-menu.ui-widget .ui-menu-item a:contains('DESK0001')",
        auto: true,
    }, {
        trigger: ".o_form_editable textarea[name='name'].product_creation_success",
        auto: true,
        run: function () {
        } // wait for product creation
    }, {
        trigger: ".o_field_widget[name='price_unit'] ",
        extra_trigger: ".o_sale_order",
        content: Markup(_t("<b>Set a price</b>.")),
        position: "right",
        run: "text 10.0"
    },
    ...tour.stepUtils.statusbarButtonsSteps("Send by Email", Markup(_t("<b>Send the quote</b> to yourself and check what the customer will receive.")), ".o_statusbar_buttons button[name='action_quotation_send']"),
    {
        trigger: ".modal-footer button.btn-primary",
        auto: true,
    }, {
        trigger: ".modal-footer button[name='action_send_mail']",
        extra_trigger: ".modal-footer button[name='action_send_mail']",
        content: _t("Let's send the quote."),
        position: "bottom",
    }]);

});
