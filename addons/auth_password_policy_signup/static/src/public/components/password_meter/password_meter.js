/** @odoo-module */

import { Meter } from "@auth_password_policy/password_meter";
import { ConcretePolicy, recommendations } from "@auth_password_policy/password_policy";
import { Component, useExternalListener, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class PasswordMeter extends Component {
    static template = xml`
        <Meter t-if="hasMinlength"
            password="state.password"
            required="required"
            recommended="recommended"/>`;
    static components = { Meter };
    static props = {
        selector: String,
    };

    setup() {
        const inputEl = document.querySelector(this.props.selector);
        useExternalListener(inputEl, "input", (e) => {
            this.state.password = e.target.value || "";
        });

        const minlength = Number(inputEl.dataset?.minlength || inputEl.getAttribute("minlength"));
        this.hasMinlength = !isNaN(minlength);
        this.state = useState({
            password: inputEl.value || "",
        });
        this.required = new ConcretePolicy({ minlength });
        this.recommended = recommendations;
    }
}

registry.category("public_components").add("password_meter", PasswordMeter);
