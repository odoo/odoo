import {
    compareVersions,
    VERSION_SELECTOR,
    htmlEditorVersions,
} from "@html_editor/html_migrations/manifest";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";

export class HtmlUpgradeManager {
    constructor(env = {}) {
        this.upgradeRegistry = registry.category("html_editor_upgrade");
        this.parser = new DOMParser();
        this.originalValue = undefined;
        this.upgradedValue = undefined;
        this.element = undefined;
        this.env = env;
    }

    get value() {
        if (this.originalValue?.constructor?.name === "Markup") {
            return markup(this.upgradedValue);
        }
        return this.upgradedValue;
    }

    processForUpgrade(value, containsComplexHtml) {
        this.containsComplexHtml = containsComplexHtml;
        const strValue = value.toString();
        if (
            strValue === this.originalValue?.toString() ||
            strValue === this.upgradedValue?.toString()
        ) {
            return this.value;
        }
        this.originalValue = value;
        this.upgradedValue = value;
        this.element = this.parser.parseFromString(fixInvalidHTML(value.toString()), "text/html")[
            this.containsComplexHtml ? "documentElement" : "body"
        ];
        const versionNode = this.element.querySelector(VERSION_SELECTOR);
        const version = versionNode?.dataset.oeVersion || "0.0";
        const VERSIONS = htmlEditorVersions();
        const currentVersion = VERSIONS.at(-1);
        if (!currentVersion || version === currentVersion) {
            return this.value;
        }
        try {
            const upgradeSequence = VERSIONS.filter((subVersion) => {
                // skip already applied versions
                return compareVersions(subVersion, version) > 0;
            });
            this.upgradedValue = this.upgrade(upgradeSequence);
        } catch {
            // If an upgrade fails, silently continue to use the raw value.
        }
        return this.value;
    }

    upgrade(upgradeSequence) {
        for (const version of upgradeSequence) {
            const modules = this.upgradeRegistry.category(version);
            for (const [key, module] of modules.getEntries()) {
                const upgrade = odoo.loader.modules.get(module).upgrade;
                if (!upgrade) {
                    console.error(
                        `An "${key}" upgrade function could not be found at "${module}" or it did not load.`
                    );
                }
                upgrade(this.element, this.env);
            }
        }
        return this.element[this.containsComplexHtml ? "outerHTML" : "innerHTML"];
    }
}
