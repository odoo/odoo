import { getImStatusText, imStatusDataRegistry } from "@mail/core/common/im_status_data";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add("hr-holidays", {
    condition(component) {
        return component.persona.leave_date_to;
    },
    icon: "fa-plane",
    title(component) {
        return component.persona.im_status === "offline"
            ? _t("On Leave")
            : _t("On Leave (%(status)s)", {
                  status: getImStatusText(component.persona.im_status),
              });
    },
    ariaLabel(component) {
        return component.persona.im_status === "offline"
            ? _t("User is on leave")
            : _t("User is on leave and %(status)s", {
                  status: getImStatusText(component.persona.im_status),
              });
    },
    sequence: 50,
});
