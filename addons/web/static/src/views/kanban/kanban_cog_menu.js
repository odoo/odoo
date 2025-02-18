import { CogMenu } from "../../search/cog_menu/cog_menu";

export class KanbanCogMenu extends CogMenu {
    static template = "web.KanbanCogMenu";
    static props = {
        ...CogMenu.props,
        hasSelectedRecords: { type: Number, optional: true },
    };
    _registryItems() {
        return this.props.hasSelectedRecords ? [] : super._registryItems();
    }
}
