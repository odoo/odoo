/** @odoo-module **/

import {FormRenderer} from "@web/views/form/form_renderer";
import {ViewButton} from "@web/views/view_button/view_button";
import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";
import {isPasswordLeaked} from "./password_leak_check";
import {_t} from "web.core";
import Dialog from "web.Dialog";

class ChangePasswordViewButton extends ViewButton {
    async onClick(ev) {
        let password = this.props.record.data.new_password;
        let checkPasswordLeak = this.props.clickParams.name === "change_password" && password.length !== 0;

        async function leaked() {
            try {
                return await isPasswordLeaked(password);
            } catch (e) {
                // Allow password change if the API is not available.
                return false;
            }
        }

        if (checkPasswordLeak && await leaked()) {
            Dialog.alert(this, _t("This password has been exposed in data breaches. Please choose another one."));
        } else {
            super.onClick(ev);
        }
    }
}

export class PasswordLeakCheckFormRenderer extends FormRenderer {
    static components = {...super.components, ViewButton: ChangePasswordViewButton};
}

export const ChangePasswordFormRender = {
    ...formView,
    Renderer: PasswordLeakCheckFormRenderer,
};

registry.category("views").add("change_password_form", ChangePasswordFormRender);
