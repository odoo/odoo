import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { addLoadingEffect } from "@web/core/utils/ui";
import { Interaction } from "@web/public/interaction";

export class RegistrationWallet extends Interaction {
    dynamicContent = {
        _root: {
            "t-att-class": () => ({ "d-none": !this.isVisible() }),
        },
        ".o_website_event_wallet_badge": {
            "t-on-click.prevent": this.onAddToWallet,
        },
    };

    isVisible() {
        return true;
    }

    async onAddToWallet(ev) {
        if (!this.isVisible() || this.isDownloading) {
            return;
        }
        this.isDownloading = true;
        const button = ev.currentTarget;
        const removeLoadingEffect = addLoadingEffect(button);
        button.setAttribute("aria-busy", "true");
        const cleanup = () => {
            removeLoadingEffect();
            button.removeAttribute("aria-busy");
        };
        this.registerCleanup(cleanup);
        try {
            // Use Odoo's download handling while retaining the signed GET URL.
            const form = document.createElement("form");
            form.method = "get";
            form.action = button.href;
            await download({ form });
        } catch {
            this.services.notification.add(
                _t("Unable to download your wallet pass. Please try again."),
                { type: "danger" }
            );
        } finally {
            cleanup();
            this.isDownloading = false;
        }
    }
}
