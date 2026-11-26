import { computed } from "@odoo/owl";

import { Pager } from "@web/core/pager/pager";


export class HierarchyPager extends Pager {
    static template = "web_hierarchy.HierarchyPager";

    canLoadLess = computed(() => this.props.limit > 80);

    canLoadMore = computed(() => Boolean(this.props.updateTotal) || this.props.limit < this.props.total);

    get value() {
        return String(this.maximum);
    }

    async setValue(value) {
        let limit = parseInt(value, 10);
        if (isNaN(limit) || limit < 1) {
            return;
        }
        if (!this.props.updateTotal) {
            limit = Math.min(limit, this.props.total);
        }
        await this.update(0, limit);
    }

    async navigate(direction) {
        const limit = Math.max(80, this.props.limit + direction * 80);
        this.update(0, limit, true);
    }
}
