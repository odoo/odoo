import { Message } from "@mail/core/common/message";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";

export class KnowledgeMessage extends Message {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            this.isPortalUser = await user.hasGroup("base.group_portal");
            this.isInternalUser = await user.hasGroup("base.group_user");
        });
    }

    get quickActionCount() {
        return 3;
    }

    get canToggleStar() {
        return super.canToggleStar && this.isInternalUser;
    }
    get showUnfollow() {
        return super.showUnfollow && this.isInternalUser;
    }
}
