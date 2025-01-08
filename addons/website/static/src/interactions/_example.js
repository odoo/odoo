import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { Component, xml, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * This is just a few examples. This should be removed in the future, before
 * merging this to master
 */

// -----------------------------------------------------------------------------
// Example of interaction
// -----------------------------------------------------------------------------
class TogglableBackgroundSection extends Interaction {
    static selector = "section";
    dynamicContent = {
        _root: {
            "t-att-style": () => ({
                "background-color": this.bgColor
            }),
            "t-att-data-bg-color": () => this.bgColor,
        },
        h2: {
            "t-on-click": this.toggleBackground,
            "t-out": () => this.bgColor,
        },
    };

    setup() {
        this.bgColor = this.el.dataset.bgColor || "white";
    }

    toggleBackground() {
        this.bgColor = this.bgColor === "white" ? "red" : "white";
        this.services.notification.add(`Example of a service: ${this.bgColor}`);
    }
}

/*
registry
    .category("public.interactions")
    .add("website.toggle_background", TogglableBackgroundSection);
*/

// -----------------------------------------------------------------------------
// Example of interaction
// -----------------------------------------------------------------------------
class FunNotificationThing extends Interaction {
    static selector = "#wrapwrap";
    dynamicContent = {
        "b,strong:t-on-click": this.onClick,
    };

    onClick(ev) {
        const text = ev.target.innerText;
        this.services.notification.add(`Look at this => ${text}`);
    }
}

/*
registry
    .category("public.interactions")
    .add("website.fun_notification", FunNotificationThing);
*/

// -----------------------------------------------------------------------------
// Example of mounted component
// -----------------------------------------------------------------------------
class Counter extends Component {
    static selector = "#wrapwrap h1";
    static template = xml`
        <div class="btn btn-primary" t-on-click="increment">
            Counter. Value=<t t-esc="state.value"/>
        </div>`;

    setup() {
        this.state = useState({ value: 1 });
        this.notification = useService("notification");
    }

    increment(ev) {
        ev.stopPropagation();
        this.state.value++;
        this.notification.add(`Example of a service: ${this.state.value}`);
    }
}

/*
registry.category("public.interactions").add("website.counter", Counter);
*/
