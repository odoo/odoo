import { Component, signal, t, useProps } from "@odoo/owl";

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

    getGroupPagerProps(group) {
        const list = group.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.isGrouped ? list.count : group.count,
            onUpdate: async ({ offset, limit }) => {
                await list.load({ limit, offset });
            },
            withAccessKey: false,
        };
    }
}
