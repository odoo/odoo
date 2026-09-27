import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class OnboardingItem extends Component {
    static components = { DropdownItem };
    static template = "web_tour.OnboardingItem";
    props = useProps({
        toursEnabled: t.boolean(),
        toggleItem: t.function(),
    });
    setup() {}
}
