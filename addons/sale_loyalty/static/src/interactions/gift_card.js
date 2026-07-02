import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { rpc, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";


export class GiftCardCopy extends Interaction {
    static selector = ".o_purchased_gift_card .copy-to-clipboard";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
    };

    onClick(ev) {
        const clipboardButtonEl = ev.currentTarget;
        const textValue = clipboardButtonEl.dataset.clipboardText;
        const iconEl = clipboardButtonEl.querySelector("i");
        browser.navigator.clipboard.writeText(textValue);
        iconEl.classList.replace("fa-clone", "fa-check");
        iconEl.classList.add("text-success");
        this.waitForTimeout(() => {
            iconEl.classList.replace("fa-check", "fa-clone");
            iconEl.classList.remove("text-success");
        }, 1800);
    }
}

export class GiftCardSend extends Interaction {
    static selector = ".o_gift_card_send_form";
    dynamicContent = {
        "button[type='submit']": { "t-on-click.prevent": this.locked(this.onSubmit, true) },
    };

    async onSubmit() {
        if (!this.el.reportValidity()) {
            return;                       // shows native "required"/invalid-email bubble, then aborts
        }
        const code = this.el.querySelector("input[name='code']").value;
        const email = this.el.querySelector("input[name='email']").value;
        try {
            await this.waitFor(rpc("/gift_card/send", { code, email }));
        } catch (error) {
            if (error instanceof RPCError) {
                this.services.notification.add(
                    _t("Could not send the gift card. Please try again."),
                    { type: "danger" },
                );
                return;
            }
            throw error;
        }
        this.protectSyncAfterAsync(() => this.el.reset())();
        this.services.notification.add(_t("Gift card sent to %s", email), {
            type: "success",
        });
    }
}

registry.category("public.interactions").add("sale_loyalty.gift_card_copy", GiftCardCopy);
registry.category("public.interactions").add("sale_loyalty.gift_card_send", GiftCardSend);
