import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "discuss-rtc",
    {
        condition: ({ persona }) => Boolean(persona?.is_in_call),
        icon: "videocam",
        iconClass: "oi-filled",
        title: _t("User is on a call"),
    },
    { sequence: 60 }
);
