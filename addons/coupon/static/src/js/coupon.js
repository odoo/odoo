odoo.define("coupon.CouponGenerateWizard", function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');

    const CouponGenerateFormController = FormController.extend({

        /**
         * Display the domain selector popover outside the modal without scroll on modal.
         * @override
         */
        on_attach_callback() {
            this._super(...arguments);
            this.el.closest('.modal-body').style.overflow = 'visible';
        },
    });

    const couponGenerateWizard = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: CouponGenerateFormController,
        }),
    });

    viewRegistry.add('coupons_generate_form', couponGenerateWizard);

    return couponGenerateWizard;

});
