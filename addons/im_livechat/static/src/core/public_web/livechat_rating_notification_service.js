import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { convertLineBreakToBr } from "@mail/utils/common/format";
import { renderToMarkup } from "@web/core/utils/render";

export const livechatRatingNotificationService = {
    dependencies: ["bus_service", "notification", "mail.store"],

    start(env, { bus_service, notification, ["mail.store"]: store }) {
        bus_service.subscribe(
            "livechat_rating_notification",
            ({ guest_id, user_id, feedback, rating_image_url, channel_id, store_data }) => {
                store.insert(store_data);
                const user = store["res.users"].get(user_id);
                const guest = store["mail.guest"].get(guest_id);
                const title = _t("%(name)s left a rating:", { name: user?.name ?? guest.name });
                const message = renderToMarkup("im_livechat.RatingNotificationMessage", {
                    title,
                    feedback: convertLineBreakToBr(feedback),
                    rating_image_url,
                    channel: store["discuss.channel"].get(channel_id),
                });
                notification.add(message, { type: "info" });
            }
        );
        bus_service.start();
    },
};

registry.category("services").add("livechatRatingNotification", livechatRatingNotificationService);
