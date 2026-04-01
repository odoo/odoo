import { LivechatChannel } from "@im_livechat/core/common/livechat_channel_model";

import { useSequential } from "@mail/utils/common/hooks";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const sequential = useSequential();

const livechatChannelPatch = {
    async join({ notify = true } = {}) {
        this.are_you_inside = true;
        if (notify) {
            this.store.env.services.notification.add(_t("You joined %s.", this.name), {
                type: "info",
            });
        }
        await sequential(() =>
            this.store.env.services.orm.call("im_livechat.channel", "action_join", [this.id])
        );
    },
    get joinTitle() {
        return _t("Join %s", this.name);
    },
    async leave({ notify = true } = {}) {
        this.are_you_inside = false;
        if (notify) {
            this.store.env.services.notification.add(_t("You left %s.", this.name), {
                type: "info",
            });
        }
        await sequential(() =>
            this.store.env.services.orm.call("im_livechat.channel", "action_quit", [this.id])
        );
    },
    get leaveTitle() {
        return _t("Leave %s", this.name);
    },
};
patch(LivechatChannel.prototype, livechatChannelPatch);
