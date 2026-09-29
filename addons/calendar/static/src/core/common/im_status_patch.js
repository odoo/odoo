import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "calendar-meeting",
    {
        condition: ({ persona }) => Boolean(persona?.is_in_meeting),
        icon: "calendar_today",
        iconClass: "oi-filled",
        title: _t("User is in a meeting"),
    },
    { sequence: 65 }
);
