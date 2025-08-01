import { patch } from "@web/core/utils/patch";
import { DiscussSidebar } from "../public_web/discuss_sidebar";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

patch(DiscussSidebar.prototype, {
    setup() {
        super.setup();
        this.ui = useService("ui");
        this.meetingHover = useHover(["meeting-btn", "meeting-floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = false;
                }
            },
        });
        this.meetingFloating = useDropdownState();
    },
    get newMeetingText() {
        return _t("New Meeting");
    },
});
