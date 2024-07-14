/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { onWillStart } from "@odoo/owl";

export class ReferralKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.company = useService("company");
        this.showGrass = true;

        onWillStart(async () => {
            const referralData = await this.orm.call('hr.applicant', 'retrieve_referral_data');
            this.showGrass = referralData.show_grass || true;
        });
    }

    get companyId() {
        return this.company.activeCompanyIds[0];
    }
}
ReferralKanbanRenderer.template = 'hr_referral.KanbanRenderer';

registry.category('views').add('referral_kanban', {
    ...kanbanView,
    Renderer: ReferralKanbanRenderer,
});
