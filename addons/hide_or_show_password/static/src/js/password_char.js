/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { archParseBoolean } from "@web/views/utils";
import { PasswordEyeButton } from "./password_eye_button";


CharField.template = 'hide_or_show_password.CharFieldPasswordEye';
CharField.components = {
    ...CharField.components,
    PasswordEyeButton,
}
CharField.props = {
    ...CharField.props,
    showOrHidePassword: { type: Boolean, optional: true },
};

const charExtractProps = CharField.extractProps;
CharField.extractProps = ({ attrs, field }) => {
    return Object.assign(charExtractProps({ attrs, field }), {
        showOrHidePassword: archParseBoolean(attrs.options.show_or_hide),
    });
};
