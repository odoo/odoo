import { Component, signal, t, useProps, computed } from "@odoo/owl";

import { HierarchyCard } from "./hierarchy_card";

export class HierarchyRenderer extends Component {
    static template = "web_hierarchy.HierarchyRenderer";
    static components = { HierarchyCard };

    props = useProps({
        model: t.object(),
        list: t.any(),
        openRecord: t.function(),
        archInfo: t.object(),
    });

    rendererRef = signal.ref();

    rows = computed(() => {
        const { parent, records } = this.props.list;
        return parent ? [[parent], records] : [records];
    });
}
