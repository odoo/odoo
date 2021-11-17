/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PhoneField } from "@web/fields/phone_field";
import { SendSMSButton } from '@sms/components/sms_button/sms_button';

patch(PhoneField, "sms.PhoneField", {
    components: {
        ...PhoneField.components,
        SendSMSButton
    },
});
