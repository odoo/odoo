/* eslint { "no-restricted-syntax": [ "error", {
    "selector": "MemberExpression[object.type=ThisExpression][property.name=pos]",
    "message": "Using this.pos in models is deprecated and about to be removed, for any question ask PoS team." }]}*/

import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosCategory extends Base {
    static pythonModel = "pos.category";

    getAllChildren() {
        const children = [this];
        if (this.child_id.length === 0) {
            return children;
        }
        for (const child of this.child_id) {
            children.push(...child.getAllChildren());
        }
        return children;
    }

    get allParents() {
        const parents = [];
        let parent = this.parent_id;

        if (!parent) {
            return parents;
        }

        while (parent) {
            parents.unshift(parent);
            parent = parent.parent_id;
        }

        return parents.reverse();
    }
}

registry.category("pos_available_models").add(PosCategory.pythonModel, PosCategory);
