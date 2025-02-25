import { patch } from "@web/core/utils/patch";
import { DiscussSidebar } from "../public_web/discuss_sidebar";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(DiscussSidebar.prototype, {
    setup() {
        super.setup();
        this.ui = useService("ui");
    },
    get startMeetingText() {
        return _t("Start a meeting");
    },
});
