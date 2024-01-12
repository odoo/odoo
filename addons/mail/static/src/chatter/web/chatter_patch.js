import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Activity } from "@mail/core/web/activity";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { RecipientList } from "@mail/core/web/recipient_list";
import { FollowerList } from "@mail/core/web/follower_list";

import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

Chatter.components = {
    ...Chatter.components,
    Activity,
    SuggestedRecipientsList,
    FollowerList,
};

Chatter.props = [...Chatter.props, "has_activities?"];

Chatter.defaultProps = { ...Chatter.defaultProps, has_activities: true };

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.activityService = useState(useService("mail.activity"));
        this.recipientsPopover = usePopover(RecipientList);
    },

    get afterPostRequestList() {
        return [...super.afterPostRequestList, "followers", "suggestedRecipients"];
    },

    get requestList() {
        return [...super.requestList, "followers", "attachments", "suggestedRecipients"];
    },
});
