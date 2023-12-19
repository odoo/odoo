import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { onWillStart } from "@odoo/owl";
import { getActionRecords, getPresenceActionItems } from "../../views/hooks";

/**
 * @extends CogMenu
 */
export class HrPresenceCogMenu extends CogMenu {
    static template = "hr_presence.cogmenu";
    
    setup() {
        super.setup();
        
        onWillStart(async () => {
            await super.onWillStart;
            this.records = await getActionRecords(this.actionItems, this.orm);
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
