/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

export class AlertPopup extends AbstractAwaitablePopup {}

AlertPopup.template = "AlertPopup";
AlertPopup.defaultProps = {
    confirmText: _lt("Ok"),
    title: "",
    body: "",
    cancelKey: false,
};

Registries.Component.add(AlertPopup);
