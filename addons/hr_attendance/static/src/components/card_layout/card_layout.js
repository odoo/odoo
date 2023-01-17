/** @odoo-module **/

import { Component } from "@odoo/owl";

export class CardLayout extends Component {}

CardLayout.template = "hr_attendance.CardLayout";
CardLayout.props = {
    kioskModeClasses: { type: String, optional: true },
    slots: Object,
};
CardLayout.defaultProps = {
    kioskModeClasses: "",
};
