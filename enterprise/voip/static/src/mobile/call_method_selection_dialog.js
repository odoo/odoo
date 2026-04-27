import { Component, useRef, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class CallMethodSelectionDialog extends Component {
    static components = { Dialog };
    static props = { close: Function, useVoip: Promise };
    static template = "voip.CallMethodSelectionDialog";

    setup() {
        this.fieldsetRef = useRef("fieldset");
        this.rememberCheckboxRef = useRef("rememberCheckbox");
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
    }

    get dialogProps() {
        return { title: _t("Select a call method") };
    }

    /** @param {MouseEvent} ev */
    onClickConfirm(ev) {
        const { value } = this.fieldsetRef.el.querySelector(
            "input[type='radio'][name='call-method']:checked"
        );
        if (this.rememberCheckboxRef.el.checked) {
            this.orm.call(
                "res.users.settings",
                "set_res_users_settings",
                [[this.store.settings.id]],
                {
                    new_settings: { how_to_call_on_mobile: value },
                }
            );
        }
        this.props.useVoip.resolve(value === "voip");
        this.props.close();
    }
}
