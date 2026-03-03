import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { CallContextMenu } from "./call_context_menu";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

Object.assign(DiscussAvatar.components, { Dropdown, CallContextMenu });

patch(DiscussAvatar.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtcSessionContextMenuDropdownState = useDropdownState();
    },
    get attClass() {
        return {
            ...super.attClass,
            "o-rtcSessionContextMenuOpen": this.rtcSessionContextMenuDropdownState.isOpen,
        };
    },
});
