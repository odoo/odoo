import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class DateTimeFieldPlugin extends Plugin {
    static id = "dateTimeField";
    static dependencies = ["history", "selection"];
    setup() {
        this.addDomListener(this.editable, "focusin", this.handleEvent.bind(this));
        this.addDomListener(this.editable, "click", this.handleEvent.bind(this));
    }

    handleEvent(ev) {
        const fieldEl = ev.target.closest("[data-oe-field]");
        if (!fieldEl || !["datetime", "date"].includes(fieldEl.dataset.oeType)) {
            return;
        }
        const linkedFieldsNodes = this.editable.querySelectorAll(
            `[data-oe-id="${fieldEl.dataset.oeId}"][data-oe-field="${fieldEl.dataset.oeField}"][data-oe-model="${fieldEl.dataset.oeModel}"]`
        );
        this.dependencies.history.ignoreDOMMutations(() => {
            for (const node of linkedFieldsNodes) {
                node.classList.add("o_editable_date_field_linked");
            }
            if (fieldEl.classList.contains("o_editable_date_field_format_changed")) {
                return;
            }
            for (const node of linkedFieldsNodes) {
                node.textContent = fieldEl.dataset.oeOriginalWithFormat;
                node.classList.add("o_editable_date_field_format_changed");
                if (node.classList.contains("oe_hide_on_date_edit")) {
                    node.classList.add("d-none");
                }
            }
            if (fieldEl.classList.contains("oe_hide_on_date_edit")) {
                for (const node of linkedFieldsNodes) {
                    if (!node.classList.contains("oe_hide_on_date_edit")) {
                        this.dependencies.selection.setSelection({
                            anchorNode: node,
                            anchorOffset: 0,
                            focusNode: node,
                            focusOffset: node.childNodes.length,
                        });
                        break;
                    }
                }
            }
        });
    }
}
registry.category("website-plugins").add(DateTimeFieldPlugin.id, DateTimeFieldPlugin);
