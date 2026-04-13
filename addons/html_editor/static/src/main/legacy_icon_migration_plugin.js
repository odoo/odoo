import { mapCSSRules } from "@html_editor/utils/formatting";
import { Plugin } from "../plugin";

// Modifier suffixes that map directly from fa-X → oi-X
export const MODIFIER_SUFFIXES = new Set([
    "fw",
    "lg",
    "spin",
    "pulse",
    "1x",
    "2x",
    "3x",
    "4x",
    "5x",
    "6x",
    "7x",
    "8x",
    "9x",
    "10x",
]);

export class LegacyIconMigrationPlugin extends Plugin {
    static id = "legacyIconMigration";
    static shared = ["convertFaIcon"];

    /**
     * Runs at editor initialisation, before the user can interact and before
     * dirty-tracking is active (save_plugin.canObserve is still false), so
     * these DOM mutations are invisible to the history / dirty system.
     */
    setup() {
        for (const icon of this.editable.querySelectorAll(".fa")) {
            this.migrateElement(icon);
        }
    }

    convertFaIcon(faIcon) {
        this.faIconMap ??= Object.fromEntries(
            mapCSSRules((rule) => {
                const classMatch = rule.selectorText.match(/^\.(fa-[\w-]+)::before/);
                if (!classMatch) {
                    return;
                }

                const className = classMatch[1];
                let contentValue = rule.style.content;
                if (!contentValue) {
                    return;
                }

                contentValue = contentValue.replace(/^['"]|['"]$/g, "");

                if (contentValue.length > 1) {
                    return [className, contentValue];
                }
                if (contentValue.length === 1) {
                    // If the content is a single character,
                    // it's not a Material Symbol icon.
                    return [className, `oi_${className.replace(/^fa-/, "")}`];
                }
            })
        );
        return this.faIconMap[faIcon];
    }

    /**
     * Migrates a single icon element:
     * - Adds the `oi` class.
     * - Sets `data-icon` from the FA→oi mapping if not already set.
     * - Replaces FA modifier classes (fa-2x, fa-fw, …) with oi equivalents.
     * - Removes all remaining `fa` and `fa-*` classes.
     *
     * @param {HTMLElement} icon
     */
    migrateElement(icon) {
        let dataIcon = null;
        const classesToRemove = [];

        for (const cls of icon.classList) {
            if (cls === "fa") {
                classesToRemove.push(cls);
            } else if (cls.startsWith("fa-")) {
                const suffix = cls.slice(3);

                if (MODIFIER_SUFFIXES.has(suffix)) {
                    icon.classList.add(`oi-${suffix}`);
                } else if (!dataIcon) {
                    dataIcon = this.convertFaIcon(cls);
                }
                classesToRemove.push(cls);
            }
        }

        if (dataIcon) {
            icon.classList.add("oi");
            if (dataIcon.endsWith("_f")) {
                dataIcon = dataIcon.slice(0, -2);
                icon.classList.add("oi-filled");
            }
            icon.dataset.icon = dataIcon;
        }

        icon.classList.remove(...classesToRemove);
    }
}
