import { Component } from "@odoo/owl";
import { OnboardingIconCard } from "./onboarding_icon_card";

export class OnboardingHelperBlocks extends Component {
    static template = "hr.OnboardingHelperBlocks";
    static components = { OnboardingIconCard };
    static props = {};
}
