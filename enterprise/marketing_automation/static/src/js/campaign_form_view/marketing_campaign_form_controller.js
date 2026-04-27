/** odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { CampaignTemplatePickerDialog } from "@marketing_automation/components/campaign_template_picker_dialog/campaign_template_picker_dialog";

export class CampaignFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }
    /**
     * @override
     */
    async create() {
        this.dialog.add(CampaignTemplatePickerDialog, {});
    }
}
