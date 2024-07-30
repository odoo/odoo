import { patch } from "@web/core/utils/patch";
import { DiscussSidebar } from "../public_web/discuss_sidebar";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

patch(DiscussSidebar.prototype, {
    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
        this.meetingHover = useHover(["meeting-btn", "meeting-floating*"], () => {
            this.meetingFloating.isOpen = this.meetingHover.isHover;
        });
        this.meetingFloating = useDropdownState();
    },
    get startMeetingText() {
        return _t("Start a meeting");
    },
});
