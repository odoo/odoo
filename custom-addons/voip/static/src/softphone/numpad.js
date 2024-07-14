/* @odoo-module */

import { useSelection } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Numpad extends Component {
    static props = { extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };
    static template = "voip.Numpad";

    setup() {
        this.softphone = useState(useService("voip").softphone);
        this.callService = useService("voip.call");
        this.userAgentService = useService("voip.user_agent");
        this.input = useRef("input");
        this.selection = useSelection({
            refName: "input",
            model: this.softphone.numpad.selection,
        });
        useEffect(
            (shouldFocus) => {
                if (shouldFocus) {
                    this.input.el.focus();
                    this.selection.restore();
                    this.softphone.shouldFocus = false;
                }
            },
            () => [this.softphone.shouldFocus]
        );
    }

    /** @param {MouseEvent} ev */
    onClickBackspace(ev) {
        const { value } = this.softphone.numpad;
        const { selectionStart, selectionEnd } = this.input.el;
        const cursorPosition = selectionStart === selectionEnd && selectionStart !== 0 ? selectionStart - 1 : selectionStart;
        if (selectionStart !== 0) {
            this.softphone.numpad.value = value.slice(0, cursorPosition) + value.slice(selectionEnd);
        }
        this.selection.moveCursor(cursorPosition);
        this.softphone.shouldFocus = true;
    }

    /** @param {MouseEvent} ev */
    onClickKeypad(ev) {
        const key = ev.target.textContent;
        this.userAgentService.session?.sipSession?.sessionDescriptionHandler.sendDtmf(key);
        const { value } = this.softphone.numpad;
        const { selectionStart, selectionEnd } = this.input.el;
        this.softphone.numpad.value = value.slice(0, selectionStart) + key + value.slice(selectionEnd);
        this.selection.moveCursor(selectionStart + 1);
        this.softphone.shouldFocus = true;
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        const inputValue = this.softphone.numpad.value.trim();
        if (!inputValue) {
            return;
        }
        this.userAgentService.makeCall({ phone_number: inputValue });
    }
}
