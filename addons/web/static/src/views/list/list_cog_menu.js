import { props, t } from "@odoo/owl";
import { CogMenu, cogMenuProps } from "../../search/cog_menu/cog_menu";

export class ListCogMenu extends CogMenu {
    static template = "web.ListCogMenu";
    props = props({
        ...cogMenuProps,
        hasSelectedRecords: t.number().optional(),
    });
    _registryItems() {
        return this.props.hasSelectedRecords ? [] : super._registryItems();
    }
}
