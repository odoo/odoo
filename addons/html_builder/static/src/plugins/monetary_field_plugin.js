import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

const monetarySel = "[data-oe-field][data-oe-type=monetary]";

export class MonetaryFieldPlugin extends Plugin {
    static id = "monetaryField";
    static dependencies = ["selection"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_editable_selectors: `${monetarySel} .oe_currency_value`,
        content_not_editable_selectors: monetarySel,

        /** Handlers */
        beforeinput_handlers: this.onBeforeInput.bind(this),

        /** Processors */
        clipboard_paste_text_processors: this.processUnsupportedHtmlForPaste.bind(this),
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

    /**
     * INPUT VALIDATION FOR MONETARY FIELDS
     * Allowed characters:
     *  - digits: 0-9
     *  - "." and ","
     *
     * Why allow "." and "," any number of times?
     * Because each locale uses them differently:
     *  - US:     "." = decimal, "," = grouping separator
     *  - Europe: "," = decimal, "." = grouping separator
     *
     * Note: Any invalid numeric pattern (wrong decimal/grouping usage) is
     * validated later on the server when the value is parsed.
     */
    onBeforeInput(ev) {
        const monetaryField = closestElement(ev.target, `${monetarySel} .oe_currency_value`);
        if (!monetaryField || !ev.data) {
            return;
        }

        const isValidInput = /\d/.test(ev.data) || ev.data === "." || ev.data === ",";
        if (!isValidInput) {
            ev.preventDefault();
        }
    }

    processUnsupportedHtmlForPaste(selection, text) {
        const monetaryField = closestElement(
            selection.anchorNode,
            `${monetarySel} .oe_currency_value`
        );
        return monetaryField ? text.replace(/[^\d.,]/g, "") : text;
    }
}

registry.category("builder-plugins").add(MonetaryFieldPlugin.id, MonetaryFieldPlugin);
