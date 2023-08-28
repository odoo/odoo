/** @odoo-module */

import { Component, useRef } from "@odoo/owl";

import { HierarchyCard } from "./hierarchy_card";

export class HierarchyRenderer extends Component {
    static components = {
        HierarchyCard,
    };
    static props = {
        model: Object,
        openRecord: Function,
        archInfo: Object,
        templates: Object,
    };
    static template = "hr_org_chart.HierarchyRenderer";

    setup() {
        this.rendererRef = useRef("renderer");
    }

    get rows() {
        const rootNodes = this.props.model.root.rootNodes;
        const rows = [{ nodes: rootNodes }];
        const processNode = (node) => {
            if (!node.isLeaf) {
                rows.push({ parentNode: node, nodes: node.nodes});
                for (const subNode of node.nodes) {
                    processNode(subNode);
                }
            }
        };

        for (const node of this.props.model.root.rootNodes) {
            processNode(node);
        }

        return rows;
    }
}
