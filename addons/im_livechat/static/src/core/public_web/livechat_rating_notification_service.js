import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { renderToMarkup } from "@web/core/utils/render";

export const livechatRatingNotificationService = {
    dependencies: ["bus_service", "notification", "mail.store"],

    start(env, { bus_service, notification, ["mail.store"]: store }) {
        bus_service.subscribe(
            "livechat_rating_notification",
            ({ guest_id, partner_id, rating_id, channel_id, store_data }) => {
                store.insert(store_data);
                const partner = store["res.partner"].get(partner_id);
                const guest = store["mail.guest"].get(guest_id);
                const rating = store["rating.rating"].get(rating_id);
                const title = _t("%(name)s left a rating:", { name: partner?.name ?? guest.name });
                const message = renderToMarkup("im_livechat.RatingNotificationMessage", {
                    title,
                    rating,
                    channel: store["discuss.channel"].get(channel_id),
                });
                notification.add(message, { type: "info", sticky: true });
            }
        );
        bus_service.start();
    },
};

registry.category("services").add("livechatRatingNotification", livechatRatingNotificationService);
