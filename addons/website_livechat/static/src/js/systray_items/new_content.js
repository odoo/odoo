import {
    NewContentSystrayItem,
    MODULE_STATUS,
} from "@website/client_actions/website_preview/new_content_systray_item";
import { patch } from "@web/core/utils/patch";

patch(NewContentSystrayItem.prototype, {
    setup() {
        super.setup();

        const newChannelElement = this.state.newContentElements.find(
            (element) => element.moduleXmlId === "base.module_website_livechat"
        );
        newChannelElement.createNewContent = () =>
            this.onAddContent("website_livechat.im_livechat_channel_action_add");
        newChannelElement.status = MODULE_STATUS.INSTALLED;
        newChannelElement.model = "im_livechat.channel";
    },
});
