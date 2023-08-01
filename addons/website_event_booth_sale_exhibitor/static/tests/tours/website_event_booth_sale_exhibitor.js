/** @odoo-module **/

import FinalSteps from "@website_event_booth_exhibitor/../tests/tours/website_event_booth_exhibitor_steps";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

FinalSteps.include({

    _getSteps: function () {
        return [
            wsTourUtils.goToCheckout(),
            ...wsTourUtils.payWithTransfer(),
        ];
    }

});
