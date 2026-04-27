/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, markup, onWillStart, onWillUnmount } from "@odoo/owl";
import { useInactivity } from "../use_inactivity";

export class RegisterPage extends Component {
    static template = "frontdesk.RegisterPage";
    static props = {
        createVisitor: Function,
        hostData: { optional: true },
        isDrinkVisible: Boolean,
        isMobile: Boolean,
        onClose: Function,
        plannedVisitorData: { optional: true },
        showScreen: Function,
        theme: String,
    };

    setup() {
        if (!this.props.isMobile) {
            useInactivity(() => this.props.onClose(), 15000);
        }

        onWillStart(async () => {
            if (!this.props.plannedVisitorData) {
                // Check if a visitor has already been created
                const visitorCreated = sessionStorage.getItem("visitorCreated");
                if (!visitorCreated) {
                    await this.props.createVisitor();
                    if (this.props.isMobile) {
                        // Set the flag in sessionStorage
                        sessionStorage.setItem("visitorCreated", "true");
                    }
                }
            }
        });

        onWillUnmount(() => {
            if (this.props.isMobile) {
                // Clear the visitorCreated flag
                sessionStorage.removeItem("visitorCreated");
            }
        });
    }

    get markupValue() {
        return markup(this.props.plannedVisitorData.plannedVisitorMessage);
    }
}

registry.category("frontdesk_screens").add("RegisterPage", RegisterPage);
