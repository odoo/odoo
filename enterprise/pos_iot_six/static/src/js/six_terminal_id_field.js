import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useState } from "@odoo/owl";

const DEBOUNCE_DELAY_MS = 500;

export class SixTerminalIdField extends CharField {
    static template = "pos_iot_six.SixTerminalIdField";

    setup() {
        super.setup(...arguments);
        this.state = useState({ isTerminalIdValid: true, terminalIdSentSuccessfully: null });

        this.sendTerminalIdToIotBox = useDebounced(async (terminalId) => {
            try {
                const iotBoxUrl = this.props.record.data.iot_box_url;
                if (terminalId) {
                    const body = { params: { terminal_id: terminalId } };
                    const headers = new Headers({ "Content-Type": "application/json" });
                    const response = await browser.fetch(
                        `${iotBoxUrl}/hw_posbox_homepage/six_payment_terminal_add`,
                        {
                            method: "POST",
                            headers,
                            body: JSON.stringify(body),
                        }
                    );
                    this.state.terminalIdSentSuccessfully = response.ok;
                } else {
                    const response = await browser.fetch(
                        `${iotBoxUrl}/hw_posbox_homepage/six_payment_terminal_clear`
                    );
                    this.state.terminalIdSentSuccessfully = response.ok;
                }
            } catch {
                this.state.terminalIdSentSuccessfully = false;
            }
        }, DEBOUNCE_DELAY_MS);
    }

    onTerminalIdChanged(event) {
        this.state.terminalIdSentSuccessfully = null;
        const value = event.target.value.trim();
        if (!value) {
            this.state.isTerminalIdValid = true;
        } else {
            this.state.isTerminalIdValid = /^[0-9]+$/.test(value);
        }
        if (this.state.isTerminalIdValid) {
            this.sendTerminalIdToIotBox(value);
        }
    }
}

export const sixTerminalIdField = {
    ...charField,
    component: SixTerminalIdField,
};

registry.category("fields").add("six_terminal_id_field", sixTerminalIdField);
