import { patch } from "@web/core/utils/patch";
import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { TABS } from "@html_editor/main/media/media_dialog/media_dialog_utils";

patch(MediaDialog.prototype, {
    extraClassesToAdd() {
        const classes = super.extraClassesToAdd();
        const closestDivEl = this.props.node?.parentElement?.closest("div");
        if (
            this.state.activeTab == TABS.IMAGES.id &&
            closestDivEl?.matches(".s_social_media, .s_share")
        ) {
            classes.push("social_media_img");
            for (const element of this.props.node.classList) {
                if (element.match(/fa-\d{1}x/) || element == "small_social_icon") {
                    classes.push(element);
                }
            }
        }
        return classes;
    },
});
