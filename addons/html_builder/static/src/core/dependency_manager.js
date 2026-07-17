import { EventBus } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

/**
 * @typedef { Object } BuilderOptionDependency
 * @property { () => boolean } isActive
 * @property { Function } [getActions]
 * @property { Function } [getValue]
 * @property { Function } [cleanSelectedItem]
 * @property { string } [type]
 */

export class DependencyManager extends EventBus {
    constructor() {
        super();
        this.dependencies = [];
        this.dependenciesMap = {};
        this.count = 0;
        this.dirty = false;
        this.retired = new Set();
        this.sweepScheduled = false;
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
    /**
     * @param {string} id
     * @param {BuilderOptionDependency} value
     * @param {Boolean} ignored - should not add the dependency to the map
     */
    add(id, value, ignored = false) {
        // A new registration supersedes entries with the same id that were
        // retired by cancelled components: they were kept alive only until
        // their replacement (this one) showed up (see retireByValue).
        const superseded = this.dependencies.filter(
            ([entryId, entryValue]) => entryId === id && this.retired.has(entryValue)
        );
        if (superseded.length) {
            this.dependencies = this.dependencies.filter((entry) => !superseded.includes(entry));
            for (const [, entryValue] of superseded) {
                this.retired.delete(entryValue);
            }
        }
        // In case the dependency is added after a dependent try to get it
        // an event is scheduled to notify the dependent about it.
        if (!ignored || !(id in this.dependenciesMap)) {
            this.triggerDependencyUpdated();
        }
        this.dependencies.push([id, value, ignored]);
        this.dirty = true;
    }
    /**
     * @param {string} id
     * @returns {BuilderOptionDependency}
     */
    get(id) {
        if (this.dirty) {
            this.update();
        }
        return this.dependenciesMap[id];
    }
    /**
     * @param {BuilderOptionDependency} value
     */
    removeByValue(value) {
        this.dependencies = this.dependencies.filter(([, v]) => v !== value);
        this.retired.delete(value);
        this.dirty = true;
        this.triggerDependencyUpdated();
    }
    /**
     * Removes the entry at the next animation frame rather than immediately,
     * unless a new entry with the same id supersedes it first (see add()).
     *
     * This is used when the owning component is destroyed before being
     * mounted, i.e. when its render was cancelled by a new render of an
     * ancestor: that new render usually recreates a replacement component,
     * but asynchronously (willStart, slots). Removing the entry right away
     * would make dependents observe a transiently missing dependency and
     * flip their state back and forth on each recreation, up to an infinite
     * render loop. So keep serving the current entry in the meantime, and
     * only drop it if no replacement showed up by the next animation frame
     * (which is when cancelled components used to be destroyed).
     *
     * @param {BuilderOptionDependency} value
     */
    retireByValue(value) {
        if (!this.dependencies.some(([, v]) => v === value)) {
            return;
        }
        this.retired.add(value);
        if (!this.sweepScheduled) {
            this.sweepScheduled = true;
            requestAnimationFrame(() => {
                this.sweepScheduled = false;
                this.sweepRetired();
            });
        }
    }
    sweepRetired() {
        if (!this.retired.size) {
            return;
        }
        const retired = this.retired;
        this.retired = new Set();
        this.dependencies = this.dependencies.filter(([, v]) => !retired.has(v));
        this.dirty = true;
        this.triggerDependencyUpdated();
    }
}
