/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
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
    extractProps({ options }) {
        const props = this._super(...arguments);
        props.enableButton = options.enable_sms;
        return props;
    },
    supportedOptions: [{
        label: _lt("Enable SMS"),
        name: "enable_sms",
        type: "boolean",
        default: true,
    }],
};

patch(phoneField, "sms.PhoneField", patchDescr);
patch(formPhoneField, "sms.PhoneField", patchDescr);
