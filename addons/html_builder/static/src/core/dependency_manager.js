import { EventBus } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

export class DependencyManager extends EventBus {
    constructor() {
        super();
        this.dependencies = [];
        this.dependenciesMap = {};
        this.count = 0;
        this.dirty = false;
        this.triggerDependencyUpdated = batched(() => {
            this.trigger("dependency-updated");
        });
    }
    update() {
        this.dependenciesMap = {};
        for (const [id, value, ignored] of this.dependencies.slice().reverse()) {
            if (ignored && id in this.dependenciesMap) {
                continue;
            }
            this.dependenciesMap[id] = value;
        }
        this.dirty = false;
    }

    add(id, value, ignored = false) {
        // In case the dependency is added after a dependent try to get it
        // an event is scheduled to notify the dependent about it.
        if (!ignored || !(id in this.dependenciesMap)) {
            this.triggerDependencyUpdated();
        }
        this.dependencies.push([id, value, ignored]);
        this.dirty = true;
    }

    get(id) {
        if (this.dirty) {
            this.update();
        }
        return this.dependenciesMap[id];
    }

    removeByValue(value) {
        this.dependencies = this.dependencies.filter(([, v]) => v !== value);
        this.dirty = true;
        this.triggerDependencyUpdated();
    }
}
