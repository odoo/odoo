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
        for (const [id, value] of this.dependencies) {
            this.dependenciesMap[id] = value;
        }
        this.dirty = false;
    }

    add(id, value) {
        // In case the dependency is added after a dependent try to get it
        // an event is scheduled to notify the dependent about it.
        this.triggerDependencyUpdated();
        this.dependencies.push([id, value]);
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
