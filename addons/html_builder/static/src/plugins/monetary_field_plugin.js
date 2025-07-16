import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class MonetaryFieldPlugin extends Plugin {
    static id = "monetaryField";
    static dependencies = ["selection"];
    resources = {
        force_editable_selector: "[data-oe-field][data-oe-type=monetary] .oe_currency_value",
        force_not_editable_selector: "[data-oe-field][data-oe-type=monetary]",
    };

    setup() {
        this.addDomListener(this.editable, "focusin", (ev) => {
            const fieldEl = ev.target.closest("[data-oe-field][data-oe-type=monetary]");
            if (!fieldEl) {
                return;
            }
            const amountEl = fieldEl.querySelector(".oe_currency_value");
            if (!amountEl.isContentEditable) {
                return;
            }
            if (fieldEl !== ev.relatedTarget?.closest("[data-oe-field][data-oe-type=monetary]")) {
                this.dependencies.selection.setSelection({
                    anchorNode: amountEl,
                    anchorOffset: 0,
                    focusNode: amountEl,
                    focusOffset: amountEl.childNodes.length,
                });
            }
        });
        this.addDomListener(this.editable, "click", (ev) => {
            const fieldEl = ev.target.closest("[data-oe-field][data-oe-type=monetary]");
            if (!fieldEl) {
                return;
            }
            const amountEl = fieldEl.querySelector(".oe_currency_value");
            if (!amountEl.isContentEditable) {
                return;
            }
            if (
                !this.dependencies.selection
                    .getTargetedNodes()
                    .some((node) => amountEl.contains(node))
            ) {
                this.dependencies.selection.setSelection({
                    anchorNode: amountEl,
                    anchorOffset: 0,
                    focusNode: amountEl,
                    focusOffset: amountEl.childNodes.length,
                });
            }
        });
    }
}

registry.category("website-plugins").add(MonetaryFieldPlugin.id, MonetaryFieldPlugin);
