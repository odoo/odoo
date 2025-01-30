import { CogMenu } from "../../search/cog_menu/cog_menu";

export class ListCogMenu extends CogMenu {
    static template = "web.ListCogMenu";
    static props = {
        ...CogMenu.props,
        hasSelectedRecords: { type: Number, optional: true },
        slots: { type: Object, optional: true },
    };
    _registryItems() {
        return this.props.hasSelectedRecords ? [] : super._registryItems();
    }
    get hasItems() {
        const { __render, __ctx } = this.props.slots?.default || {};
        const rendered =  __render?.(__ctx, __ctx.__owl__);
        return super.hasItems || rendered?.children.filter((c) => c !== undefined).length;
    }
}
