import { markup } from "@odoo/owl";
import {
    compareVersions,
    VERSION_SELECTOR,
    htmlEditorVersions,
} from "@html_editor/html_migrations/html_migrations_utils";
import { registry } from "@web/core/registry";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";

/**
 * Handle HTML transformations dependent on the current implementation of the
 * editor and its plugins for HtmlField values that were not upgraded through
 * conventional means (python upgrade script), i.e. modify obsolete
 * classes/style, convert deprecated Knowledge Behaviors to their
 * EmbeddedComponent counterparts, ...
 *
 * How to use:
 * - Create a file to export a `migrate(element, env)` function which applies
 *   the necessary modifications inside `element` related to a specific version:
 *    - HTMLElement `element`: a container for the HtmlField value
 *    - Object `env`: the typical `owl` environment (can be used to check
 *      the current record data, use a service, ...).
 * !!!  ALWAYS assume that the `env` may not have the resource used in your
 *      migrate function and adjust accordingly.
 * - Refer to that file in the `html_editor_upgrade` registry, in the version
 *   category related to your change: `major.minor` (bump major for a change in
 *   master, and minor for a change in stable), in a sub-category related to
 *   your module.
 *   Example for the version 1.1 in `html_editor`:
 *   `registry
 *        .category("html_editor_upgrade")
 *        .category("1.1")
 *        .add("html_editor", "@html_editor/html_migrations/migration-1.1")`
 */
export class HtmlUpgradeManager {
    constructor() {
        this.upgradeRegistry = registry.category("html_editor_upgrade");
        this.parser = new DOMParser();
        this.originalValue = undefined;
        this.upgradedValue = undefined;
        this.element = undefined;
        this.env = {};
    }

    get value() {
        return this.upgradedValue;
    }

    processForUpgrade(value, { containsComplexHTML, env } = {}) {
        this.env = env || {};
        this.containsComplexHTML = containsComplexHTML;
        const strValue = value.toString();
        if (
            strValue === this.originalValue?.toString() ||
            strValue === this.upgradedValue?.toString()
        ) {
            return this.value;
        }
        this.originalValue = value;
        this.upgradedValue = value;
        this.element = this.parser.parseFromString(fixInvalidHTML(value), "text/html")[
            this.containsComplexHTML ? "documentElement" : "body"
        ];
        const versionNode = this.element.querySelector(VERSION_SELECTOR);
        const version = versionNode?.dataset.oeVersion || "0.0";
        const VERSIONS = htmlEditorVersions();
        const currentVersion = VERSIONS.at(-1);
        if (!currentVersion || version === currentVersion) {
            return this.value;
        }
        try {
            const upgradeSequence = VERSIONS.filter(
                (subVersion) =>
                    // skip already applied versions
                    compareVersions(subVersion, version) > 0
            );
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
                const migrate = odoo.loader.modules.get(module).migrate;
                if (!migrate) {
                    console.error(
                        `A "${key}" migrate function could not be found at "${module}" or it did not load.`
                    );
                }
                migrate(this.element, this.env);
            }
        }
        return markup(this.element[this.containsComplexHTML ? "outerHTML" : "innerHTML"]);
    }
}
