/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { CampaignTemplatePickerDialog } from "@marketing_automation/components/campaign_template_picker_dialog/campaign_template_picker_dialog";

export class CampaignListController extends ListController {
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
