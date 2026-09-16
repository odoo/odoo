import { t, useProps } from "@odoo/owl";
import { CogMenu } from "../../search/cog_menu/cog_menu";

export class KanbanCogMenu extends CogMenu {
    printItemsSeparator = true;
    myProps = useProps({
        hasSelectedRecords: t.number().optional(),
    });

    _registryItems() {
        return this.myProps.hasSelectedRecords ? [] : super._registryItems();
    }
}
