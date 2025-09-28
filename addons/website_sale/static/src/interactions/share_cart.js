import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ShareCart extends Interaction {
    static selector = ".o_wsale_share_cart";
    dynamicContent = {
        "#share_cart_button": {
            "t-on-click": (ev) => this.onShareClick(ev)
        }
    };

    /**
     * Handles the "Share Cart" button click using the native Web Share API if available,
     * or falling back to copying the share link to the clipboard.
     *
     * :param Event ev: The click event on the share cart button.
     * :rtype: Promise<void>
     */
    async onShareClick(ev) {
        ev.preventDefault();

        const shareCartEl = ev.currentTarget;
        if (!shareCartEl) {
            return;
        }

        // Read all share data from the backend via data-share-vals
        const shareVals = JSON.parse(shareCartEl.dataset.shareVals || "{}");
        const shareLink = shareVals.share_link;
        const shareTitle = shareVals.share_title || _t("My cart");
        const shareText = shareVals.share_description || "";

        if (!shareLink) {
            return;
        }

        try {
            if (navigator.share) {
                await navigator.share({
                    title: shareTitle,
                    text: shareText,
                    url: shareLink
                });
            } else {
                await navigator.clipboard.writeText(shareLink);
            }
        } catch (err) {
            console.warn("Error sharing or copying the cart link:", err);
        }
    }

}

registry.category("public.interactions").add("website_sale.share_cart", ShareCart);
