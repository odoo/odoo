/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PhoneField, phoneField, formPhoneField } from "@web/views/fields/phone/phone_field";
import { SendSMSButton } from '@sms/components/sms_button/sms_button';

patch(PhoneField, "sms.PhoneField", {
    components: {
        ...PhoneField.components,
        SendSMSButton
    },
    defaultProps: {
        ...PhoneField.defaultProps,
        enableButton: true,
    },
    props: {
        ...PhoneField.props,
        enableButton: { type: Boolean, optional: true },
    },
});

const patchDescr = {
    extractProps({ attrs }) {
        return {
            ...this._super({ attrs }),
            enableButton: attrs.options.enable_sms,
        };
    },
};

patch(phoneField, "sms.PhoneField", patchDescr);
patch(formPhoneField, "sms.PhoneField", patchDescr);
