import { Plugin } from "@html_editor/plugin";
import { isEmpty, isProtected, isProtecting } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { selectElements } from "@html_editor/utils/dom_traversal";

function isMutationRecordSavable(record) {
    if (record.type === "attributes" && record.attributeName === "placeholder") {
        return false;
    }
    return true;
}

function target(selection, editable) {
    const el = editable.firstChild;
    if (!selection.inEditable && el && el.tagName === "P" && editable.textContent === "") {
        return el;
    }
}

export class HintPlugin extends Plugin {
    static name = "hint";
    static dependencies = ["history", "selection"];
    /** @type { (p: HintPlugin) => Record<string, any> } */
    static resources = (p) => {
        const resources = {
            mutation_filtered_classes: ["o-we-hint"],
            is_mutation_record_savable: isMutationRecordSavable,
            onSelectionChange: p.updateTempHint.bind(p),
            onExternalHistorySteps: p.updateHints.bind(p),
        };
        if (p.config.placeholder) {
            resources.temp_hints = {
                text: p.config.placeholder,
                target,
            };
        }

        return resources;
    };

    setup() {
        this.tempHint = null;
        this.updateHints(this.editable);
    }

    destroy() {
        super.destroy();
        this.clearHints();
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CONTENT_UPDATED": {
                this.updateHints(payload.root);
                break;
            }
            case "CLEAN":
            case "CLEAN_FOR_SAVE":
                this.clearHints(payload.root);
                break;
        }
    }

    /**
     * @param {HTMLElement} [root]
     */
    updateHints(root = this.editable) {
        this.clearHints(root);
        this.makeEmptyBlockHints(root);
        this.updateTempHint(this.shared.getEditableSelection());
    }

    makeEmptyBlockHints(root) {
        for (const { selector, hint } of this.resources.emptyBlockHints) {
            for (const el of selectElements(root, selector)) {
                // @todo: consider using isEmptyBlock instead.
                if (isEmpty(el) && !isProtected(el) && !isProtecting(el)) {
                    this.makeHint(el, hint);
                }
            }
        }
    }

    updateTempHint(selection) {
        if (this.tempHint) {
            this.removeHint(this.tempHint);
        }

        if (selection.isCollapsed) {
            for (const hint of this.resources["temp_hints"]) {
                const target = hint.target(selection, this.editable);
                // Do not replace an existing empty block hint by a temp hint.
                if (target && !target.classList.contains("o-we-hint")) {
                    this.makeHint(target, hint.text);
                    this.tempHint = target;
                    return;
                }
            }
        }
    }

    makeHint(el, text) {
        el.setAttribute("placeholder", text);
        el.classList.add("o-we-hint");
    }

    removeHint(el) {
        el.removeAttribute("placeholder");
        removeClass(el, "o-we-hint");
        if (this.tempHint === el) {
            this.tempHint = null;
        }
    }

    clearHints(root = this.editable) {
        for (const elem of selectElements(root, ".o-we-hint")) {
            this.removeHint(elem);
        }
    }
}
