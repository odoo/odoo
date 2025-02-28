import { patch } from "@web/core/utils/patch";
import { Store } from "@mail/model/store";
import { Record } from "@mail/model/record";
import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";

export const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.guest_token = Record.attr(null, {
            compute() {
                return expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
            },
            onUpdate() {
                if (this.guest_token) {
                    expirableStorage.setItem(GUEST_TOKEN_STORAGE_KEY, this.guest_token);
                    this.store.env.services.bus_service.addChannel(
                        `mail.guest_${this.guest_token}`
                    );
                    return;
                }
                expirableStorage.removeItem(GUEST_TOKEN_STORAGE_KEY);
                this.store.env.services.bus_service.deleteChannel(`mail.guest_${this.guest_token}`);
            },
            eager: true,
        });
    },
});
