/** @odoo-module */

import {
    Component,
} from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class BehaviorToolbar extends Component {
    static props = {
        buttonsGroupClass: { type: String, optional: true },
        slots: Object,
    };
    static template = "knowledge.BehaviorToolbar";
}

export class BehaviorToolbarButton extends Component {
    static props = {
        buttonRef: { type: Function, optional: true },
        hidden: { type: Boolean, optional: true },
        icon: { type: String, optional: true },
        label: String,
        name: { type: String, optional: true },
        onClick: Function,
        title: { type: String, optional: true},
    };
    static template = "knowledge.BehaviorToolbarButton";

    setup() {
        useForwardRefToParent("buttonRef");
    }
}
