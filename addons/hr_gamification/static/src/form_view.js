import { patch } from "@web/core/utils/patch";
import { EmployeeFormRenderer } from "@hr/views/form_view";
import { onMounted } from "@odoo/owl";

patch(EmployeeFormRenderer.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const record = this.props.record
            const context = record.context?.params || record.context;
            if (context?.open_badges_tab && record.resModel === "hr.employee.public") {
                const tab = document.querySelector('[name="received_badges"]');
                if (tab) {
                    tab.click();
                    setTimeout(() => {
                        const badges = record.data.badge_ids?.records || [];
                        const badgeToHighlight = badges.find(badge => badge.resId === context.user_badge_id);
                        if (!badgeToHighlight) return;

                        const userBadge = document.querySelector(`[data-id="${badgeToHighlight.id}"]`);
                        if (!userBadge) return;

                        userBadge.classList.add('user-badge', 'user-badge-lift');
                        setTimeout(() => {
                            userBadge.classList.remove('user-badge-lift');
                        }, 2000);
                    },100);
                }
            }
        });
    }
});
