import { Component, t, useProps } from '@odoo/owl'
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { useService } from '@web/core/utils/hooks';
import { openHubItem } from '../hub_menu/hub_utils';


export class HubTabs extends Component {
    static template = 'web.HubTabs';
    static components = { Dropdown, DropdownItem };
    props = useProps({
        hub: t.any()
    });
    actionPlugin = useService("action");

    setup() {
        this.items = this.props.hub.action.item_ids;
        this.itemsById = Object.fromEntries(this.props.hub.action.item_ids.map((item) => [item.id, item]));
    }

    getPinnedItems(){
        return this.props.hub.pinnedItemIds().map(id => this.itemsById[id]).filter(Boolean);
    }

    openHubItem(item) {
        openHubItem(this.actionPlugin, item, {
            resModel: this.props.hub.action.res_model,
            resId: this.props.hub.resId
        }, {
            stackPosition: "replaceCurrentAction",
        })
    }
}
