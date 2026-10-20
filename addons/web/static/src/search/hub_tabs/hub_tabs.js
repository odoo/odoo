import { Component, signal, t, useProps } from '@odoo/owl'
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { Transition } from '@web/core/transition';
import { useService } from '@web/core/utils/hooks';
import { useSortable } from '@web/core/utils/sortable_owl';
import { openHubItem, saveHubSetting, useHubItems } from './hub_utils';


export class HubTabs extends Component {
    static template = 'web.HubTabs';
    static components = { Dropdown, DropdownItem, Transition };
    props = useProps({
        hub: t.any()
    });
    actionPlugin = useService("action");
    orm = useService("orm");
    ui = useService("ui");
    root = signal.ref();

    setup() {
        this.items = useHubItems(this.props.hub);
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
        const items = this.items();
        return this.props.hub.pinnedItemIds()
            .map((id) => items.find((item) => item.id === id))
            .filter(Boolean);
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
        saveHubSetting(this.orm, this.props.hub, { pinned_item_ids: pinnedItemIds });
    }

    isPinned(item) {
        return this.props.hub.pinnedItemIds().includes(item.id);
    }

    /**
     * Pin ``item`` as the last tab, or unpin it if it is pinned.
     */
    togglePin(item) {
        const pinnedItemIds = this.props.hub.pinnedItemIds().filter((id) => id !== item.id);
        if (!this.isPinned(item)) {
            pinnedItemIds.push(item.id);
        }
        saveHubSetting(this.orm, this.props.hub, { pinned_item_ids: pinnedItemIds });
    }

    openHubItem(item, newWindow) {
        const { resModel, resId } = this.props.hub;
        openHubItem(this.actionPlugin, item, { resModel, resId }, {
            stackPosition: "replaceCurrentAction",
            newWindow
        })
    }
}
