import { Failure } from "@mail/core/common/failure_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Failure.prototype, {
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
<<<<<<< master
                    record_name: this.lastMessage.thread.display_name,
||||||| d3470834837b1b4738677900b87ef59b7e069b42
=======
                    record_name: this.lastMessage.thread.name,
>>>>>>> 67b53beed50ff293bc7c52eb908d8f972671bca8
                });
            }
            return _t("An error occurred when sending an SMS");
        }
        return super.body;
    },
});
