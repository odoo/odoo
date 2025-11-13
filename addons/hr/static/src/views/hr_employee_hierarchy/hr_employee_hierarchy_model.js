import { HierarchyModel } from "@web_hierarchy/hierarchy_model";
import { KeepLast } from "@web/core/utils/concurrency";

export class HrEmployeeHierarchyModel extends HierarchyModel {
    /**@override */
    setup(params, { notification }) {
        super.setup(params, { notification });
        this.KeepLastInCycle = new KeepLast();
    }

    /** @override */
    async load(params = {}) {
        await super.load(params);
        this.nodesInCycle = await this.KeepLastInCycle.add(this._loadNodesInCycle());
    }

    async _loadNodesInCycle() {
        const domain = [["company_id", "in", this.context.allowed_company_ids || []]];
        return await this.orm.call("hr.employee", "cycles_in_hierarchy_read", [
            domain,
        ]);
    }
}
