/** @odoo-module native */
import { Component, onWillDestroy, useState } from "@odoo/owl";
import { SelectMenu } from "@web/components/select_menu";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useBus } from "@web/core/utils/hooks";

const log = makeLogger("portal.select_menu");

export class SelectMenuWrapper extends Component {
    static template = "l10n_latam_base.SelectMenuWrapper";
    static components = { SelectMenu };
    static props = {
        el: { type: Object },
    };

    setup() {
        const select = this.props.el;
        this.state = useState({
            choices: [...select.options]
                .filter((option) => option.value)
                .map(({ value, label }) => ({ value, label })),
            multiSelect: select.multiple,
            value: select.multiple
                ? [...select.selectedOptions].map((option) => option.value)
                : select.value,
        });
        const wasHidden = select.classList.contains("d-none");
        select.classList.add("d-none");
        onWillDestroy(() => {
            if (!wasHidden) {
                select.classList.remove("d-none");
            }
        });
        useBus(select, "select", (ev) => this.onSelect(ev.detail.value));
    }

    onSelect(value) {
        const select = this.props.el;
        if (this.state.multiSelect) {
            const selected = new Set(value ?? []);
            for (const option of select.options) {
                option.selected = selected.has(option.value);
            }
            this.state.value = [...select.selectedOptions].map(
                (option) => option.value,
            );
        } else {
            select.value = value ?? "";
            this.state.value = select.value;
        }
        log.logic("synchronize selection", {
            multiple: this.state.multiSelect,
            selectedCount: select.selectedOptions.length,
        });
        // Manually trigger the change event
        const event = new Event("change", { bubbles: true });
        select.dispatchEvent(event);
    }
}
