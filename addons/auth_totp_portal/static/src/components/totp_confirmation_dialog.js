import { useLayoutEffect } from "@web/owl2/utils";
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
<<<<<<< b9a088e60470abdb16cf21d7b14b9f771111fb06
        useLayoutEffect(
            (clipboardButtonEl) => {
                if (clipboardButtonEl) {
||||||| 64ceef175fc0dc014908bd4d79b8acf526a7a3c6
        useEffect(
            (clipboardButtonEl) => {
                if (clipboardButtonEl) {
=======
        useEffect(
            (...clipboardButtonEls) => {
                for (const clipboardButtonEl of clipboardButtonEls) {
>>>>>>> e6dcde6ebc9710b93e6d81e68e426937a042e82a
                    clipboardButtonEl.addEventListener("click", onClickClipboardButton);
                }
                return () => {
                    for (const clipboardButtonEl of clipboardButtonEls) {
                        clipboardButtonEl.removeEventListener("click", onClickClipboardButton);
                    }
                };
            },
            () => [...(this.modalRef.el?.querySelectorAll(".o_clipboard_button") ?? [])]
        );
    }
}
