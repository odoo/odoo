/** @odoo-module */
const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
const Registries = require("point_of_sale.Registries");
const { _lt } = require("@web/core/l10n/translation");

// formerly ConfirmPopupWidget
export class ConfirmPopup extends AbstractAwaitablePopup {}
ConfirmPopup.template = "ConfirmPopup";
ConfirmPopup.defaultProps = {
    confirmText: _lt("Ok"),
    cancelText: _lt("Cancel"),
    title: _lt("Confirm ?"),
    body: "",
};

Registries.Component.add(ConfirmPopup);
