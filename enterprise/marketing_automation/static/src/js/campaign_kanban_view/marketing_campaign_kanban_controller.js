/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { CampaignTemplatePickerDialog } from "@marketing_automation/components/campaign_template_picker_dialog/campaign_template_picker_dialog";

export class CampaignKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }
    /**
     * @override
     */
    async createRecord() {
        this.dialog.add(CampaignTemplatePickerDialog, {});
    }
}
