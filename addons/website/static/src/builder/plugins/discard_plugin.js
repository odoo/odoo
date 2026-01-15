import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } DiscardPluginShared
 * @property { DiscardPlugin['getRollback'] } getRollback
 * @property { DiscardPlugin['setRollback'] } setRollback
 * @property { DiscardPlugin['rollback'] } rollback
 */
export class DiscardPlugin extends Plugin {
    static id = "discard";
    static dependencies = ["history"];
    static shared = ["getRollback", "setRollback", "rollback", "isSafe"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        save_handlers: this.onSave.bind(this),
    };

    rollbacks = null;

    getRollback(key, defaultValue = null) {
        return this.rollbacks?.[key] ?? defaultValue;
    }

    setRollback(key, value) {
        this.rollbacks ??= {};
        this.rollbacks[key] = value;
    }

    isSafe() {
        return this.rollbacks === null && !this.dependencies.history.canUndo();
    }

    setup() {
        if (document.querySelector("body").classList.contains("o_builder_open")) {
            // Retrieve saved rollback only if the page is reloaded because of
            // a backend change made with the builder; so only if the builder is
            // already open.
            this.rollbacks = JSON.parse(localStorage.getItem("website.rollbacks"));
        }
        this.deleteSavedRollbacks();
    }

    async onSave() {
        if (this.rollbacks) {
            localStorage.setItem("website.rollbacks", JSON.stringify(this.rollbacks));
        }
    }

    async rollback() {
        if (this.rollbacks) {
            await rpc("/website/rollback", this.rollbacks);
        }
        this.deleteSavedRollbacks();
    }

    deleteSavedRollbacks() {
        localStorage.removeItem("website.rollbacks");
    }
}

registry.category("website-plugins").add(DiscardPlugin.id, DiscardPlugin);
registry.category("translation-plugins").add(DiscardPlugin.id, DiscardPlugin);
