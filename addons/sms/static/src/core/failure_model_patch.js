import { Failure } from "@mail/core/common/failure_model";
import { patchModel } from "@mail/model/export";
import { _t } from "@web/core/l10n/translation";

export const failurePatch = patchModel(Failure, {
    get iconSrc() {
        if (this.type === "sms") {
            return "/sms/static/img/sms_failure.svg";
        }
        return super.iconSrc;
    },
    get body() {
        if (this.type === "sms") {
            if (this.notifications.length === 1 && this.lastMessage?.thread) {
                return _t("An error occurred when sending an SMS on “%(record_name)s”", {
                    record_name: this.lastMessage.thread.display_name,
                });
            }
            return _t("An error occurred when sending an SMS");
        }
        return super.body;
    },
});
