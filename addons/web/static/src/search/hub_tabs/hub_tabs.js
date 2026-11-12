import { Component, signal, t, useProps } from '@odoo/owl'
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { useService } from '@web/core/utils/hooks';
import { useSortable } from '@web/core/utils/sortable_owl';
import { openHubItem, savePinnedItemIds } from '../hub_menu/hub_utils';


export class HubTabs extends Component {
    static template = 'web.HubTabs';
    static components = { Dropdown, DropdownItem };
    props = useProps({
        hub: t.any()
    });
    actionPlugin = useService("action");
    orm = useService("orm");
    root = signal.ref();

    setup() {
        this.items = this.props.hub.items;
        this.itemsById = Object.fromEntries(this.props.hub.items.map((item) => [item.id, item]));
        useSortable({
            ref: this.root,
            elements: ".o_hub_tab",
            cursor: "move",
            delay: 200,
            tolerance: 10,
            onWillStartDrag: ({ element, addClass }) => addClass(element, "o_hub_tab_dragged"),
            onDrop: (params) => this.onTabDrop(params),
        });
    }

    getPinnedItems(){
        return this.props.hub.pinnedItemIds().map(id => this.itemsById[id]).filter(Boolean);
    }

    /**
     * Move the dropped tab after ``previous`` (or first), and save that order.
     * Ids of deleted items are dropped from the pins along the way.
     */
    onTabDrop({ element, previous }) {
        const itemId = Number(element.dataset.id);
        const pinnedItemIds = this.getPinnedItems()
            .map((item) => item.id)
            .filter((id) => id !== itemId);
        const index = previous ? pinnedItemIds.indexOf(Number(previous.dataset.id)) + 1 : 0;
        pinnedItemIds.splice(index, 0, itemId);
        savePinnedItemIds(this.orm, this.props.hub, pinnedItemIds);
    }

    openHubItem(item) {
        const { resModel, resId } = this.props.hub;
        openHubItem(this.actionPlugin, item, { resModel, resId }, {
            stackPosition: "replaceCurrentAction",
        })
    }
}
