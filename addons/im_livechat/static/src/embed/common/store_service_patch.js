import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { Store } from "@mail/core/common/store_service";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

export const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.activeVisitorLivechats = fields.Many("discuss.channel", {
            inverse: "storeAsActiveVisitorLivechats",
        });
        this.onChange(
            () => [], // one-shot (no dependencies): cleanup on delete
            function onChangeGuestTokenStorage() {
                const onGuestTokenChange = (value) => (this.guest_token = value);
                expirableStorage.onChange(GUEST_TOKEN_STORAGE_KEY, onGuestTokenChange);
                return () =>
                    expirableStorage.offChange(GUEST_TOKEN_STORAGE_KEY, onGuestTokenChange);
            }
        );
        this.guest_token = expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
        this.onChange(
            () => [this.guest_token],
            function onChangeGuestToken(guest_token) {
                if (guest_token) {
                    expirableStorage.setItem(GUEST_TOKEN_STORAGE_KEY, guest_token);
                    const busChannel = `mail.guest_${guest_token}`;
                    this.env.services.bus_service.addChannel(busChannel);
                    return () => this.env.services.bus_service.deleteChannel(busChannel);
                }
                expirableStorage.removeItem(GUEST_TOKEN_STORAGE_KEY);
            }
        );
        this.livechat_rule = fields.One("im_livechat.channel.rule");
        this.livechat_available = false;
    },
    onStarted() {
        super.onStarted(...arguments);
        if (this.guest_token) {
            this.ensureInitialized();
        }
    },
};
patch(Store.prototype, StorePatch);
