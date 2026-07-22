import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

const { DateTime, Interval } = luxon;

imStatusDataRegistry.add(
    "hr-holidays",
    {
        condition: ({ user }) => {
            if (!user?.employee_id?.leave_date_from || !user?.employee_id?.leave_date_to) {
                return false;
            }
            const leaveInterval = Interval.fromDateTimes(
                user.employee_id.leave_date_from,
                user.employee_id.leave_date_to
            );
            return leaveInterval.contains(DateTime.now());
        },
        icon: "travel",
        iconClass: "",
        title: {
            online: _t("User is on leave and online"),
            away: _t("User is on leave and idle"),
            busy: _t("User is on leave and busy"),
            default: _t("User is on leave"),
        },
    },
    { sequence: 50 }
);
