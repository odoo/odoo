import { useListener } from "@odoo/owl";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";

export class TotpConfirmationDialog extends InputConfirmationDialog {
    setup() {
        super.setup();
        this.tooltip = usePopover(Tooltip, { position: "bottom" });

        const onClickCopyButton = async (ev) => {
            ev.preventDefault();
            const copyButtonEl = ev.currentTarget;
            const secretEl = this.modalRef().querySelector(copyButtonEl.dataset.copyTarget);
            browser.navigator.clipboard.writeText(secretEl.textContent).then(() => {
                this.tooltip.open(copyButtonEl, { tooltip: _t("Copied!") });
                setTimeout(this.tooltip.close, 800);
            });
        };
        useListener(
            () => this.modalRef()?.querySelector("[data-copy-target]"),
            "click",
            onClickCopyButton
        );
    }
}
