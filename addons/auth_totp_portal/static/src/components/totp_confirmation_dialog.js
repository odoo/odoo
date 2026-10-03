/** @odoo-module **/

import { useEffect } from "@odoo/owl";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";

/**
 * This is a quick-and-dirty fix to enable the copy of the TOTP secret in the
 * portal.
 */
export class TotpConfirmationDialog extends InputConfirmationDialog {
    setup() {
        super.setup();
        this.tooltip = usePopover(Tooltip, { position: "bottom" });

        const onClickClipboardButton = async (ev) => {
            ev.preventDefault();
            const clipboardButtonEl = ev.currentTarget;
            const secretSpan = this.modalRef.el.querySelector("span[name='secret']");
            browser.navigator.clipboard.writeText(secretSpan.textContent).then(() => {
                this.tooltip.open(clipboardButtonEl, { tooltip: _t("Copied!") });
                setTimeout(this.tooltip.close, 800);
            });
        };
        useEffect(
            (...clipboardButtonEls) => {
                clipboardButtonEls.forEach((btn) => btn.addEventListener("click", onClickClipboardButton));
                return () => clipboardButtonEls.forEach((btn) => btn.removeEventListener("click", onClickClipboardButton));
            },
            () => [...(this.modalRef.el?.querySelectorAll(".o_clipboard_button") ?? [])]
        );
    }
}
