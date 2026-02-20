import { NotificationMessage } from "@mail/core/common/notification_message";
import { patch } from "@web/core/utils/patch";
import { router } from "@web/core/browser/router";
import { user } from "@web/core/user";

import { useEffect } from "@odoo/owl";

patch(NotificationMessage.prototype, {
    setup() {
        super.setup();
        useEffect(
            () => {
                this.prepareNotificationMessageBody(this.root.el);
            },
            () => [this.message.richBody]
        );
    },
    /**
     * @override
     * @param {HTMLElement} bodyEl
     */
    prepareNotificationMessageBody(bodyEl) {
        if (!bodyEl) {
            return;
        }
        this._updatePartnerMentionsHref(bodyEl);
    },

    /**
     * @param {HTMLElement} bodyEl
     */
    async _updatePartnerMentionsHref(bodyEl) {
        if (!user.isInternalUser) {
            return;
        }
        const mentionEls = Array.from(
            bodyEl.querySelectorAll("a[data-oe-model='res.partner'][data-oe-id]")
        );
        const partnerIds = [...new Set(mentionEls.map((el) => Number(el.dataset.oeId)).filter(Boolean))];
        if (!partnerIds.length) {
            return;
        }
        const partners = await this.env.services.orm.read("res.partner", partnerIds, ["employee_ids"]);
        const employeeByPartnerId = new Map(
            partners
                .map((partner) => [partner.id, partner.employee_ids[0]])
                .filter(([, employeeId]) => Boolean(employeeId))
        );
        for (const mentionEl of mentionEls) {
            const partnerId = Number(mentionEl.dataset.oeId);
            const employeeId = employeeByPartnerId.get(partnerId);
            if (employeeId) {
                mentionEl.dataset.oeModel = "hr.employee";
                mentionEl.dataset.oeId = employeeId;
                mentionEl.href = router.stateToUrl({ model: "hr.employee", resId: employeeId });
            }
        }
    },
});
