import { Component, signal, t, useProps, computed } from "@odoo/owl";

import { Pager } from "@web/core/pager/pager";
import { HierarchyCard } from "./hierarchy_card";

export class HierarchyRenderer extends Component {
    static template = "web_hierarchy.HierarchyRenderer";
    static components = { HierarchyCard, Pager };

    props = useProps({
        model: t.object(),
        list: t.any(),
        openRecord: t.function(),
        archInfo: t.object(),
    });

    rendererRef = signal.ref();

    rows = computed(() => {
        return this.props.list.isGrouped
            ? this.props.list.groups
            : [{ id: this.props.list.id, list: this.props.list }];
    });

    getGroupPagerProps(group) {
        const list = group.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                await list.load({ limit, offset });
            },
            withAccessKey: false,
        };
    }
}
