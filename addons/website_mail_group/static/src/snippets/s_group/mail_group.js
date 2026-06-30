import { MailGroup } from "@mail_group/interactions/mail_group";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";

import { rpc } from "@web/core/network/rpc";

patch(MailGroup.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            _root: {
                "t-att-class": () => ({
                    "d-none": false,
                }),
                "t-att-data-is-member": () => `${this.isMember}`,
            },
            ".o_mg_email_input_group": {
                "t-att-class": () => ({
                    "input-group": !this.hasMemberEmail,
                    "d-flex": !!this.hasMemberEmail,
                    "justify-content-end": !!this.hasMemberEmail,
                }),
            },
            ".o_mg_email_input_group .o_mg_subscribe_email": {
                "t-att-class": () => ({
                    "d-none": !!this.hasMemberEmail,
                }),
            },
        });
    },

    async willStart() {
        await super.willStart(...arguments);

        // Can not be done in the template of the snippets
        // Because it's rendered only once when the admin add the snippets
        // for the first time, we make a RPC call to setup the widget properly
        const email = (new URL(document.location.href)).searchParams.get('email');
        const response = await rpc('/group/is_member', {
            'group_id': this.mailGroupId,
            'email': email,
            'token': this.token,
        });

        if (!response) {
            // We do not access to the mail group, just remove the widget
            this.removeChildren(this.el);
            return;
        }

        const userEmail = response.email;
        this.isMember = response.is_member;

        if (userEmail && userEmail.length) {
            this.hasMemberEmail = true;
            this.el.querySelector(".o_mg_email_input_group .o_mg_subscribe_email").value = userEmail;
        }
    },
});
