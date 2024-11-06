import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// -----------------------------------------------------------------------------
// Example of attached component
// -----------------------------------------------------------------------------
class TogglableBackgroundSection extends Component {
    static selector = "section";
    static dynamicContent = {
        "root:t-att-style": "'background-color: ' + state.bgColor",
        "h1,h2:t-on-click": "toggleBackground",
    };
    
    setup() {
        this.state = useState({ bgColor: "white" });
        this.notification = useService("notification");
    }

    toggleBackground() {
        this.state.bgColor = this.state.bgColor === "white" ? "red" : "white";
        this.notification.add(`Example of a service: ${this.state.bgColor}`);
    }
}

registry.category("website.active_elements").add("website.togglebackground", TogglableBackgroundSection);

// -----------------------------------------------------------------------------
// Example of attached component, simple interaction
// -----------------------------------------------------------------------------
class FunNotificationThing extends Component {
    static selector = "#wrapwrap";
    static dynamicContent = {
        "b,strong:t-on-click": "onClick"
    };

    setup() {
        this.notification = useService("notification");
    }

    onClick(ev) {
        const text = ev.target.innerText;
        this.notification.add(`Look at this => ${text}`);
    }
}

registry.category("website.active_elements").add("funnotification", FunNotificationThing);


// -----------------------------------------------------------------------------
// Example of mounted component
// -----------------------------------------------------------------------------
class Counter extends Component {
    static selector = "#wrapwrap h1,h2";
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

registry.category("website.active_elements").add("website.Counter", Counter);
