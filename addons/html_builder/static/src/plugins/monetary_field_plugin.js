import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const monetarySel = "[data-oe-field][data-oe-type=monetary]";

export class MonetaryFieldPlugin extends Plugin {
    static id = "monetaryField";
    static dependencies = ["selection"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_editable_selectors: `${monetarySel} .oe_currency_value`,
        content_not_editable_selectors: monetarySel,
    };

    setup() {
        const handleEvent = (ev, condition) => {
            const fieldEl = ev.target.closest(monetarySel);
            const amountEl = fieldEl?.querySelector(".oe_currency_value");
            if (amountEl?.isContentEditable && condition({ fieldEl, amountEl })) {
                this.dependencies.selection.setSelection({
                    anchorNode: amountEl,
                    anchorOffset: 0,
                    focusNode: amountEl,
                    focusOffset: amountEl.childNodes.length,
                });
            }
        };
        this.addDomListener(this.editable, "focusin", (ev) =>
            handleEvent(ev, ({ fieldEl }) => fieldEl !== ev.relatedTarget?.closest(monetarySel))
        );
        this.addDomListener(this.editable, "click", (ev) =>
            handleEvent(
                ev,
                ({ amountEl }) =>
                    !this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => amountEl.contains(node))
            )
        );
    }
}

registry.category("builder-plugins").add(MonetaryFieldPlugin.id, MonetaryFieldPlugin);
