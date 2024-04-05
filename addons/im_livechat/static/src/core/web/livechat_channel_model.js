import { Record } from "@mail/core/common/record";
import { useSequential } from "@mail/utils/common/hooks";

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

const sequential = useSequential();

export class LivechatChannel extends Record {
    static id = "id";

    appCategory = Record.one("DiscussAppCategory", {
        compute() {
            return {
                extraClass: "o-mail-DiscussSidebarCategory-livechat",
                id: `im_livechat.category_${this.id}`,
                livechatChannel: this,
                name: this.name,
                sequence: 22,
            };
        },
    });
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    hasSelfAsMember = false;
    threads = Record.many("Thread", { inverse: "livechatChannel" });

    async join({ notify = true } = {}) {
        this.hasSelfAsMember = true;
        if (notify) {
            this.store.env.services.notification.add(_t("You joined %s.", this.name), {
                type: "info",
            });
        }
        await sequential(() =>
            this.store.env.services.orm.call("im_livechat.channel", "action_join", [this.id])
        );
    }

    get joinTitle() {
        return sprintf(_t("Join %s"), this.name);
    }

    async leave({ notify = true } = {}) {
        this.hasSelfAsMember = false;
        if (notify) {
            this.store.env.services.notification.add(_t("You left %s.", this.name), {
                type: "info",
            });
        }
        await sequential(() =>
            this.store.env.services.orm.call("im_livechat.channel", "action_quit", [this.id])
        );
    }

    get leaveTitle() {
        return sprintf(_t("Leave %s"), this.name);
    }
}
LivechatChannel.register();
