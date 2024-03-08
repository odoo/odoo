/* @odoo-module */

import { Thread } from "@mail/core_ui/thread";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(Thread.prototype, "calendar", {
    setup() {
        this._super();
        this.orm = useService("orm");
        this.user = useService("user");
        onWillStart(async () => {
            if (this.props.thread.model === 'calendar.event' && this.props.thread.id) {
                const record = await this.orm.read(
                    'calendar.event',
                    [this.props.thread.id],
                    ['privacy', 'user_id', 'partner_ids']
                );
                this.isAccesible = record[0].privacy === 'private' && !(this.user.userId === record[0].user_id[0]) && !(record[0].partner_ids.includes(this.user.partnerId));
            }
        });
    },
});
