import { FormCogMenu } from "@web/views/form/form_cog_menu/form_cog_menu";
import { onWillStart } from "@odoo/owl";
import { getActionRecords, getPresenceActionItems } from "../../views/hooks";

/**
 * @extends CogMenu
 */
export class HrPresenceCogMenu extends FormCogMenu {
    static template = "hr_presence.cogmenu";

    setup() {
        super.setup();

        onWillStart(async () => {
            await super.onWillStart;
            this.records = await getActionRecords(this.orm);
        });
    }

    /**
     * @override
     */
    get cogItems() {
        var result = super.cogItems;
        result = getPresenceActionItems(result, this.records);
        this.presenceActionItems = result[1];
        return result[0];
    }

    get PresenceActionItems() {
        return this.presenceActionItems;
    }
}
