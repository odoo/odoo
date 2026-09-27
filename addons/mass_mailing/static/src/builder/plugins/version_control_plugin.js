import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class VersionControlPlugin extends Plugin {
    static id = "versionControl";
    static dependencies = ["builderOptions"];
    accessPerOutdatedEl = new WeakMap();
    static shared = ["hasAccessToOutdatedEl", "giveAccessToOutdatedEl", "replaceWithNewVersion"];

    hasAccessToOutdatedEl(el) {
        if (!el.dataset.snippet) {
            return true;
        }
        if (this.accessPerOutdatedEl.has(el)) {
            return this.accessPerOutdatedEl.get(el);
        }
        const snippetKey = el.dataset.snippet;
        const snippet = this.config.snippetModel.getOriginalSnippet(snippetKey);
        let isUpToDate = true;
        if (snippet) {
            const { vxml: originalVxml } = snippet.content.dataset;
            const { vxml: elVxml } = el.dataset;
            isUpToDate = originalVxml === elVxml;
        }
        this.accessPerOutdatedEl.set(el, isUpToDate);
        return isUpToDate;
    }
    giveAccessToOutdatedEl(el) {
        this.accessPerOutdatedEl.set(el, true);
    }
    replaceWithNewVersion(el) {
        const snippetKey = el.dataset.snippet;
        const snippet = this.config.snippetModel.getOriginalSnippet(snippetKey);
        const cloneEl = snippet.content.cloneNode(true);
        el.after(cloneEl);
        el.remove();
        this.dependencies.builderOptions.setNextTarget(cloneEl);
    }
}

registry.category("mass_mailing-plugins").add(VersionControlPlugin.id, VersionControlPlugin);
