/** @odoo-module */

import {patch} from "@web/core/utils/patch";
import {ListController} from "@web/views/list/list_controller";

patch(ListController.prototype, "web_group_expand.ListController", {
    async expandAllGroups() {
        // We expand layer by layer. So first we need to find the highest
        // layer that's not already fully expanded.
        let layer = this.model.root.groups;
        while (layer.length) {
            const closed = layer.filter(function (group) {
                return group.isFolded;
            });
            if (closed.length) {
                // This layer is not completely expanded, expand it
                await layer.forEach((group) => {
                    group.isFolded = false;
                });
                break;
            }
            // This layer is completely expanded, move to the next
            layer = _.flatten(
                layer.map(function (group) {
                    return group.list.groups || [];
                }),
                true
            );
        }
        await this.model.root.load();
        this.model.notify();
    },

    async collapseAllGroups() {
        // We collapse layer by layer. So first we need to find the deepest
        // layer that's not already fully collapsed.
        let layer = this.model.root.groups;
        while (layer.length) {
            const next = _.flatten(
                layer.map(function (group) {
                    return group.list.groups || [];
                }),
                true
            ).filter(function (group) {
                return !group.isFolded;
            });
            if (!next.length) {
                // Next layer is fully collapsed, so collapse this one
                await layer.forEach((group) => {
                    group.isFolded = true;
                });
                break;
            }
            layer = next;
        }
        await this.model.root.load();
        this.model.notify();
    },
});
