import { Component, useExternalListener, useRef } from "@odoo/owl";
import { isIOS, isIosApp, isMacOS } from "@web/core/browser/feature_detection";

export class CustomGroupByItem extends Component {
    static template = "web.CustomGroupByItem";
    static props = {
        fields: Array,
        onAddCustomGroup: Function,
    };

    setup() {
        this.selectRef = useRef("selectElement");
        this.isIOSOrMacOS = isIosApp() || isIOS() || isMacOS();
        if (!this.isIOSOrMacOS) {
            useExternalListener(window, "click", (ev) => {
                const select = this.selectRef.el;
                if (select && !select.contains(ev.target)) {
                    select.value = "";
                }
            });
        }
    }

    get choices() {
        return this.props.fields.map((f) => ({ label: f.string, value: f.name }));
    }

    onChange(ev) {
        if (!this.isIOSOrMacOS) {
            return;
        }
        this.addCustomGroup(ev.target);
    }

    onClick(ev) {
        if (this.isIOSOrMacOS) {
            return;
        }
        this.addCustomGroup(ev.target);
    }

    addCustomGroup(select) {
        if (select.value) {
            this.props.onAddCustomGroup(select.value);
            // reset the placeholder
            select.value = "";
        }
    }
}
