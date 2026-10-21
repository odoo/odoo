import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class TutorialItem extends Component {
    static components = { DropdownItem };
    static template = "web_tuto.TutorialItem";
    props = useProps({
        tutorialsEnabled: t.boolean(),
        toggleItem: t.function(),
    });
}
