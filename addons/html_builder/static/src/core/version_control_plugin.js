import { Plugin } from "@html_editor/plugin";

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
            const {
                vcss: originalVcss,
                vxml: originalVxml,
                vjs: originalVjs,
            } = snippet.content.dataset;
            const { vcss: elVcss, vxml: elVxml, vjs: elVjs } = el.dataset;
            isUpToDate =
                originalVcss === elVcss && originalVxml === elVxml && originalVjs === elVjs;
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
        el.replaceWith(cloneEl);
        this.dependencies.builderOptions.setNextTarget(cloneEl);
    }
}
