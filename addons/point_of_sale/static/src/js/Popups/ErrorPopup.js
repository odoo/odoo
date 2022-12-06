/** @odoo-module alias=point_of_sale.ErrorPopup */
import AbstractAwaitablePopup from "point_of_sale.AbstractAwaitablePopup";
import Registries from "point_of_sale.Registries";
import { _lt } from "@web/core/l10n/translation";

import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ErrorPopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();
        this.sound = useService("sound");
        onMounted(this.onMounted);
    }
    onMounted() {
        this.sound.play("error");
    }
}
ErrorPopup.template = "ErrorPopup";
ErrorPopup.defaultProps = {
    confirmText: _lt("Ok"),
    title: _lt("Error"),
    body: "",
    cancelKey: false,
};

Registries.Component.add(ErrorPopup);

// FIXME remove default export
export default ErrorPopup;
