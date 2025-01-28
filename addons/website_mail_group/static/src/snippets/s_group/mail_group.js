import { MailGroup } from "@mail_group/interactions/mail_group";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

patch(MailGroup.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            _root: {
                "t-att-class": () => ({
                    "d-none": false,
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
            'group_id': this.mailgroupId,
            'email': email,
            'token': this.token,
        });

        if (!response) {
            // We do not access to the mail group, just remove the widget
            this.el.replaceChildren();
            return;
        }

        const userEmail = response.email;
        this.isMember = response.is_member;

        if (userEmail && userEmail.length) {
            const emailInputEl = this.el.querySelector(".o_mg_subscribe_email");
            emailInputEl.value = userEmail;
            emailInputEl.setAttribute("readonly", 1);
        }

        if (this.isMember) {
            const buttonEl = this.el.querySelector(".o_mg_subscribe_btn");
            buttonEl.innerText = _t('Unsubscribe');
            buttonEl.classList.remove("btn-primary");
            buttonEl.classList.add("btn-outline-primary");
        }

        this.el.dataset.isMember = this.isMember;
    },
});
