import { Component, useRef, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

export class CustomStatusEditor extends Component {
    // static props = ["close"];
    static template = "discuss.StatusSettings";

    setup() {
        this.store = useState(useService("mail.store"));
        this.emojiButton = useRef("emoji-button");
        this.emojiPicker = useEmojiPicker(this.emojiButton, {
            onSelect: (emoji) => {
                this.state.customStatus += emoji;
            },
        });
        this.state = useState({
            customStatus: this.store.self.custom_status || "",
            resetAfter: "today",
        });
    }

    async setStatus(to) {
        rpc("/mail/im_status", { action: to });
        rpc("/discuss/settings/mute", { minutes: to == "busy" ? -1 : false });
        this.store.self.im_status = to;
    }

    onConfirm() {
        rpc("/mail/custom_status", {
            custom_status: this.state.customStatus,
            reset_after: this.state.resetAfter,
        });
        this.store.self.custom_status = this.state.customStatus;
        // this.props.close();
    }

    onClear() {
        this.state.customStatus = "";
        rpc("/mail/custom_status", { custom_status: "", reset_after: "never" });
        this.store.self.custom_status = "";
    }
}
