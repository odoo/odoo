import { Meter } from "@auth_password_policy/password_meter";
import { ConcretePolicy, recommendations } from "@auth_password_policy/password_policy";
import { Component, useExternalListener, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class PasswordMeter extends Component {
    static template = "auth_password_policy_signup.PasswordMeter";
    static components = { Meter };
    static props = {
        selector: String,
    };

    setup() {
        const inputEl = document.querySelector(this.props.selector);
        useExternalListener(inputEl, "input", (e) => {
            this.state.password = e.target.value || "";
        });

        const minlength = Number(inputEl.getAttribute("minlength"));
        this.hasMinlength = !isNaN(minlength);
        this.state = useState({
            password: inputEl.value || "",
        });
        this.required = new ConcretePolicy({ minlength });
        this.recommended = recommendations;
    }
}

registry.category("public_components").add("password_meter", PasswordMeter);
