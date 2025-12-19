import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PhoneField, phoneField, FormPhoneField, formPhoneField } from "@web/views/fields/phone/phone_field";

patch(PhoneField, {
    defaultProps: {
        ...PhoneField.defaultProps,
        enableButton: true,
    },
    props: {
        ...PhoneField.props,
        enableButton: { type: Boolean, optional: true },
    },
});

const patchDescr = () => ({
    extractProps({ options }) {
        const props = super.extractProps(...arguments);
        props.enableButton = options.enable_sms;
        return props;
    },
    supportedOptions: [{
        label: _t("Enable SMS"),
        name: "enable_sms",
        type: "boolean",
        default: true,
    }],
});

patch(phoneField, patchDescr());
patch(formPhoneField, patchDescr());

patch(FormPhoneField.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },
    get overlayButtons() {
        if (!this.props.enableButton || this.props.record.data[this.props.name].length === 0) {
            return super.overlayButtons;
        }
        return [
            ...super.overlayButtons,
            {
                icon: "fa-mobile",
                onSelected: async () => {
                    await this.props.record.save();
                    this.action.doAction(
                        {
                            type: "ir.actions.act_window",
                            target: "new",
                            name: _t("Send SMS"),
                            res_model: "sms.composer",
                            views: [[false, "form"]],
                            context: {
                                ...user.context,
                                default_res_model: this.props.record.resModel,
                                default_res_id: this.props.record.resId,
                                default_number_field_name: this.props.name,
                                default_composition_mode: "comment",
                                dialog_size: "medium",
                            },
                        },
                        {
                            onClose: () => {
                                this.props.record.load();
                            },
                        }
                    );
                },
                name: _t("SMS"),
                showInReadonly: true,
            },
        ];
    },
});
