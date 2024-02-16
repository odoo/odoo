import { Component } from "@odoo/owl";

export class CardLayout extends Component {
    static template = "hr_attendance.CardLayout";
    static props = {
        kioskModeClasses: { type: String, optional: true },
        slots: Object,
    };
    static defaultProps = {
        kioskModeClasses: "",
    };
}
