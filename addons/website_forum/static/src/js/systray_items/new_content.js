import { NewContentModal } from '@website/client_actions/website_preview/new_content_modal';
import { MODULE_STATUS } from "@website/client_actions/website_preview/new_content_element";
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newForumElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_forum');
        newForumElement.createNewContent = () => this.onAddContent('website_forum.forum_forum_action_add');
        newForumElement.status = MODULE_STATUS.INSTALLED;
        newForumElement.model = 'forum.forum';
    },
});
