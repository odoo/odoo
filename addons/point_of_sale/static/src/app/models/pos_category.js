import { registry } from "@web/core/registry";
import { Base } from "./related_models";

const { DateTime } = luxon;

export class PosCategory extends Base {
    static pythonModel = "pos.category";

    getAllChildren() {
        const children = [this];
        if (this.child_ids.length === 0) {
            return children;
        }
        for (const child of this.child_ids) {
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

    get isAvailable() {
        const now = DateTime.now();
        const nowDecimal = now.hour + now.minute / 60;
        return nowDecimal > this.hour_after && nowDecimal < this.hour_until;
    }
}

registry.category("pos_available_models").add(PosCategory.pythonModel, PosCategory);
