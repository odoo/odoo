/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("sale_tour", {
    url: "/web",
    rainbowMan: false,
    sequence: 20,
    steps: () => [stepUtils.showAppsMenuItem(), {
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
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_step_company_data]',
    extra_trigger: ".o_sale_order",
    content: _t("Start by checking your company's data."),
    position: "bottom",
    skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
}, {
    trigger: 'input[id=street_0]',
    content: _t("Complete your company's data"),
    position: "bottom",
    skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
}, {
    trigger: ".modal-content button.o_form_button_save",
    content: _t("Looks good. Let's continue."),
    position: "left",
    skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
}, stepUtils.showAppsMenuItem(),
{
    trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
    skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
    edition: "community",
    auto: true,
}, {
    trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
    skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
    edition: "enterprise",
    auto: true,
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_step_base_document_layout]',
    extra_trigger: ".o_sale_order",
    content: _t("Customize your quotes and orders."),
    position: "bottom",
    skip_trigger: 'a[data-method=action_open_step_base_document_layout].o_onboarding_step_action__done',
}, {
    trigger: "button[name='document_layout_save']",
    extra_trigger: ".o_sale_order",
    content: _t("Good job, let's continue."),
    position: "top", // dot NOT move to bottom, it would cause a resize flicker
    skip_trigger: 'a[data-method=action_open_step_base_document_layout].o_onboarding_step_action__done',
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_step_sale_order_confirmation]',
    extra_trigger: ".o_sale_order",
    content: _t("To speed up order confirmation, we can activate electronic signatures or payments."),
    position: "bottom",
    skip_trigger: 'a[data-method=action_open_step_sale_order_confirmation].o_onboarding_step_action__done',
}, {
    trigger: "button[name='add_payment_methods']",
    extra_trigger: ".o_sale_order",
    content: _t("Lets keep electronic signature for now."),
    position: "bottom",
    skip_trigger: 'a[data-method=action_open_step_sale_order_confirmation].o_onboarding_step_action__done',
}, {
    trigger: 'a.o_onboarding_step_action.btn[data-method=action_open_step_sample_quotation]',
    extra_trigger: ".o_sale_order",
    content: _t("Now, we'll create a sample quote."),
    position: "bottom",
}]});

registry.category("web_tour.tours").add("sale_quote_tour", {
        url: "/web#action=sale.action_quotations_with_onboarding&view_type=form",
        rainbowMan: true,
        rainbowManMessage: () => markup(_t("<b>Congratulations</b>, your first quotation is sent!<br>Check your email to validate the quote.")),
        sequence: 30,
        steps: () => [{
        trigger: ".o_field_res_partner_many2one[name='partner_id']",
        extra_trigger: ".o_sale_order",
        content: _t("Write a company name to create one, or see suggestions."),
        position: "right",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    }, {
        trigger: ".ui-menu-item > a:contains('Agrolait')",
        auto: true,
        in_modal: false,
    }, {
        trigger: ".o_field_x2many_list_row_add > a",
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
            var $descriptionElement = $(".o_form_editable textarea[name='name']");
            // when description changes, we know the product has been created
            $descriptionElement.change(function () {
                $descriptionElement.addClass("product_creation_success");
            });
        },
        id: "product_selection_step"
    }, {
        trigger: "a:contains('DESK0001')",
        auto: true,
    }, {
        trigger: ".o_field_text[name='name'] textarea:propValueContains(DESK0001)",
        run: () => {},
        auto: true,
    }, {
        trigger: ".o_field_widget[name='price_unit'] input",
        extra_trigger: ".oi-arrow-right",  // Wait for product creation
        content: markup(_t("<b>Set a price</b>.")),
        position: "right",
        run: "text 10.0"
    }, {
        trigger: ".o_field_monetary[name='price_subtotal']:contains(10.00)",
        auto: true,
    },
    ...stepUtils.statusbarButtonsSteps("Send by Email", markup(_t("<b>Send the quote</b> to yourself and check what the customer will receive.")), ".o_statusbar_buttons button[name='action_quotation_send']"),
    {
        trigger: ".modal-footer button[name='action_send_mail']",
        extra_trigger: ".modal-footer button[name='action_send_mail']",
        content: _t("Let's send the quote."),
        position: "bottom",
    },
    {
        trigger: "body:not(.modal-open)",
        auto: true,
    }
]});
