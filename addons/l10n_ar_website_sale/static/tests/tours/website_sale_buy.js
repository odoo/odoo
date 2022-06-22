odoo.define('l10n_ar_website_sale.shop_buy_product', function (require) {
"use strict";

    let tour = require('web_tour.tour');

    var Session = require('web.session');

    let session = Session;

    console.log(session);
    console.log(session.user_context);
    console.log(session.user_context.allowed_company_ids);

    let shop_buy_product = tour.tours.shop_buy_product;
    // Remove the step related to other localisations
    shop_buy_product.steps = _.filter(shop_buy_product.steps, step => !step.l10n || step.l10n === "ar");

    let checkout_step_idx = _.findIndex(shop_buy_product.steps, step => step.trigger === 'a[href*="/shop/checkout"]');

    shop_buy_product.steps.splice(checkout_step_idx + 1, 0, {
        trigger: "#wizard-step20.active, #wizard-step40.active",
        auto: true,
        l10n: 'ar',
        run: function (actions) {
            let $wizard_step = $("div[id=wizard-step20]");
            if ($wizard_step.length && $wizard_step.hasClass("active")) {
                let $el = $('select[name="l10n_ar_afip_responsibility_type_id"]');
                if ($el.length) {
                    $("select[name='l10n_ar_afip_responsibility_type_id'] option[value='5']").prop('selected', true);
                    $("select[name='l10n_latam_identification_type_id'] option[value='1']").prop('selected', true);
                    $("input[name='vat']").val('123456789');
                    $("a[role='button'] span:contains('Next')").click();
                }
            }
        },
    }, {
        trigger: "span:contains('Confirm'), #wizard-step40.active",
        auto: true,
        l10n: 'ar',
        run: function (actions) {
            let $wizard_step = $("div[id=wizard-step20]");
            if ($wizard_step.length && $wizard_step.hasClass("active")) {
                $("a[role='button'] span:contains('Confirm')").click();
            }
        },
    });
});
