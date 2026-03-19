import { patch } from "@web/core/utils/patch";
import { MediaDialog, TABS } from "@html_editor/main/media/media_dialog/media_dialog";

patch(MediaDialog.prototype, {
    extraClassesToAdd() {
        const classes = super.extraClassesToAdd();
        const closestSnippetEl = this.props.closestSnippetEl;
        if (
            this.state.activeTab == TABS.IMAGES.id &&
            closestSnippetEl?.matches(".s_social_media, .s_share")
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
