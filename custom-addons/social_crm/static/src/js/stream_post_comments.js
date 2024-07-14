/** @odoo-module **/

import { StreamPostComments } from '@social/js/stream_post_comments';

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(StreamPostComments.prototype, {
    setup() {
        super.setup(...arguments);

        this.actionService = useService("action");
    },

    isConvertibleToLead() {
        return !this.isAuthor;
    },

    /**
     * Method called when generating a social.lead from a social.stream.post.
     * It opens the social.post.to.lead wizard and pass it the social_post reference as.
     * The various information (author, date, ...) will be deduced by the wizard using
     * the social_post reference.
     *
     * We also give the wizard the content formatted with "_formatPost", which will add support for
     * @mentions, #references, and links.
     */
     generateLeadFromPost() {
        this.actionService.doAction("social_crm.social_post_to_lead_action", {
            additionalContext: {
                default_conversion_source: 'stream_post',
                default_social_stream_post_id: this.originalPost.id.raw_value,
                default_social_account_id: this.originalPost.account_id.raw_value,
                default_post_content: this._formatPost(this.originalPost.message.raw_value),
            }
        });

        this.env.closeCommentsModal();
    }
});
