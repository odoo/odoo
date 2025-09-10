import { patch } from "@web/core/utils/patch";
import FinalSteps from "@website_event_booth_exhibitor/../tests/tours/website_event_booth_exhibitor_steps";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

patch(FinalSteps.prototype, {

    _getSteps: function () {
        return [
            {
                content: "Click on confirm button",
                trigger: "button.o_wbooth_registration_confirm",
                run: "click",
                expectUnloadPage: true,
            },
            wsTourUtils.goToCheckout(),
            ...wsTourUtils.payWithTransfer({ expectUnloadPage: true }),
        ];
    }

});
