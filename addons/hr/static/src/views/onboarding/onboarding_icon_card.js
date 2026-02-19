import { Component } from "@odoo/owl";

export class OnboardingIconCard extends Component {
    static template = "hr.OnboardingIconCard";
    static props = {
        label: { type: String },
        iconPath: { type: String },
    };
}
