/** @odoo-module **/
import * as hoot from "@odoo/hoot-dom";
import { _t } from "@web/core/l10n/translation";

/**
 * Calls the given `func` then returns/resolves to `true`
 * if it will result to unloading of the page.
 * @param {(...args: any[]) => void} func
 * @param  {any[]} args
 * @returns {boolean | Promise<boolean>}
 */
export function callWithUnloadCheck(func, ...args) {
    let willUnload = false;
    const beforeunload = () => (willUnload = true);
    window.addEventListener("beforeunload", beforeunload);
    const result = func(...args);
    if (result instanceof Promise) {
        return result.then(() => {
            window.removeEventListener("beforeunload", beforeunload);
            return willUnload;
        });
    } else {
        window.removeEventListener("beforeunload", beforeunload);
        return willUnload;
    }
}

/**
 * @returns The css selector of the node or its text when node is a text node.
 */
function serializeNode(node, accept_text_node = false) {
    if (accept_text_node && node.nodeType === Node.TEXT_NODE) {
        return `${node.nodeValue.trim()}`;
    }
    if (!(node instanceof Element)) {
        return "";
    }
    let selector = node.tagName.toLowerCase();
    if (node.id) {
        selector += `#${node.id}`;
    }
    if (node.classList.length > 0) {
        selector += `.${[...node.classList].join(".")}`;
    }
    for (const attr of node.attributes) {
        if (!["id", "class"].includes(attr.name)) {
            selector += `[${attr.name}="${attr.value}"]`;
        }
    }
    return selector;
}

/**
 * @returns List of modifications
 */
function extractChanges(nodes, parentPath = []) {
    let sentences = [];

    nodes.forEach((node) => {
        const currentPath = [...parentPath, node.node].filter(Boolean);
        const path =
            currentPath.length > 2
                ? `${currentPath.at(0)} ${currentPath.at(-1)}`
                : currentPath.at(0);

        if (node.text) {
            sentences.push(
                `${path} : Text has changed : ${node.text.before} => ${node.text.after}`
            );
        }

        if (node.attributes) {
            node.attributes.forEach((attr) => {
                sentences.push(
                    `${path} : Attribute ${attr.name} has changed : ${attr.before} => ${attr.after}`
                );
            });
        }

        if (node.addedNodes) {
            node.addedNodes.forEach((added) => {
                sentences.push(`${path} : The node {${added}} has been added.`);
            });
        }

        if (node.removedNodes) {
            node.removedNodes.forEach((removed) => {
                sentences.push(`${path} : The node {${removed}} has been removed.`);
            });
        }

        if (node.children) {
            sentences = sentences.concat(extractChanges(node.children, currentPath));
        }
    });

    return sentences;
}

/**
 * Popularizes the modifications that have been made for a node between two states.
 */
export function serializeChanges(beforeElement, afterElement, changes = [], deep = 0) {
    if (!beforeElement || !afterElement) {
        return;
    }
    const node = serializeNode(afterElement, true);
    const beforeNodes = [...beforeElement.childNodes];
    const afterNodes = [...afterElement.childNodes];
    const maxLength = Math.max(beforeNodes.length, afterNodes.length);
    const hasChanged = {};
    if (maxLength) {
        hasChanged.children = [];
    }

    if (
        afterElement.nodeType === Node.TEXT_NODE &&
        beforeElement.textContent !== afterElement.textContent &&
        !beforeElement.children?.length &&
        !afterElement.children?.length
    ) {
        hasChanged.text = {
            before: beforeElement.textContent,
            after: afterElement.textContent,
        };
    } else {
        hasChanged.node = node;
    }

    const beforeAttrNames = new Set([...(beforeElement.attributes || [])].map((attr) => attr.name));
    const afterAttrNames = new Set([...(afterElement.attributes || [])].map((attr) => attr.name));
    new Set([...beforeAttrNames, ...afterAttrNames]).forEach((name) => {
        const oldValue =
            beforeElement?.nodeType === Node.ELEMENT_NODE ? beforeElement.getAttribute(name) : null;
        const newValue =
            afterElement?.nodeType === Node.ELEMENT_NODE ? afterElement.getAttribute(name) : null;
        const before = oldValue !== newValue || !afterAttrNames.has(name) ? oldValue : null;
        const after = oldValue !== newValue || !beforeAttrNames.has(name) ? newValue : null;
        if (before || after) {
            hasChanged.attributes = hasChanged.attributes || [];
            hasChanged.attributes.push({ name, before, after });
        }
    });

    function compareNodes(afterNodes, beforeNodes) {
        return afterNodes.filter((node, index) => {
            const correspondingNode = beforeNodes[index];
            if (!correspondingNode) {
                return true;
            }
            if (
                correspondingNode.nodeName === node.nodeName &&
                correspondingNode.id === node.id &&
                correspondingNode.className === node.className
            ) {
                return false;
            }
            return (
                correspondingNode.nodeName !== node.nodeName ||
                (correspondingNode.nodeType !== Node.TEXT_NODE &&
                    correspondingNode.textContent !== node.textContent)
            );
        });
    }
    const addedNodes = compareNodes(afterNodes, beforeNodes);
    if (addedNodes.length) {
        hasChanged.addedNodes = addedNodes.map(serializeNode);
    }
    const removedNodes = compareNodes(beforeNodes, afterNodes);
    if (removedNodes.length) {
        hasChanged.removedNodes = removedNodes.map(serializeNode);
    }
    changes.push(hasChanged);
    for (let i = 0; i < maxLength; i++) {
        serializeChanges(beforeNodes[i], afterNodes[i], hasChanged.children, deep++);
    }

    return extractChanges(changes);
}

export function serializeMutation(mutation) {
    const { type, attributeName } = mutation;
    if (type === "attributes" && attributeName) {
        return `attribute: ${attributeName}`;
    } else {
        return type;
    }
}

/**
 * @param {HTMLElement} element
 * @returns {HTMLElement | null}
 */
export function getScrollParent(element) {
    if (!element) {
        return null;
    }
    // We cannot only rely on the fact that the element’s scrollHeight is
    // greater than its clientHeight. This might not be the case when a step
    // starts, and the scrollbar could appear later. For example, when clicking
    // on a "building block" in the "building block previews modal" during a
    // tour (in website edit mode). When the modal opens, not all "building
    // blocks" are loaded yet, and the scrollbar is not present initially.
    const overflowY = window.getComputedStyle(element).overflowY;
    const isScrollable =
        overflowY === "auto" ||
        overflowY === "scroll" ||
        (overflowY === "visible" && element === element.ownerDocument.scrollingElement);
    if (isScrollable) {
        return element;
    } else {
        return getScrollParent(element.parentNode);
    }
}

export const stepUtils = {
    _getHelpMessage(functionName, ...args) {
        return `Generated by function tour utils ${functionName}(${args.join(", ")})`;
    },

    addDebugHelp(helpMessage, step) {
        if (typeof step.debugHelp === "string") {
            step.debugHelp = step.debugHelp + "\n" + helpMessage;
        } else {
            step.debugHelp = helpMessage;
        }
        return step;
    },

    showAppsMenuItem() {
        return {
            isActive: ["auto", "community", "desktop"],
            trigger: ".o_navbar_apps_menu button:enabled",
            tooltipPosition: "bottom",
            run: "click",
        };
    },

    toggleHomeMenu() {
        return [
            {
                isActive: [".o_main_navbar .o_menu_toggle"],
                trigger: ".o_main_navbar .o_menu_toggle",
                content: _t("Click the top left corner to navigate across apps."),
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_sidebar_topbar a.btn-primary",
                tooltipPosition: "right",
                run: "click",
            },
        ];
    },

    autoExpandMoreButtons(isActiveMobile = false) {
        const isActive = ["auto"];
        if (isActiveMobile) {
            isActive.push("mobile");
        }
        return {
            isActive,
            content: `autoExpandMoreButtons`,
            trigger: ".o-form-buttonbox",
            run() {
                const more = hoot.queryFirst(".o-form-buttonbox .o_button_more");
                if (more) {
                    hoot.click(more);
                }
            },
        };
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            this.showAppsMenuItem(),
            {
                isActive: ["community"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "right",
                run: "click",
            },
            {
                isActive: ["enterprise"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "bottom",
                run: "click",
            },
        ].map((step) =>
            this.addDebugHelp(this._getHelpMessage("goToApp", dataMenuXmlid, description), step)
        );
    },

    statusbarButtonsSteps(innerTextButton, description, trigger) {
        const steps = [];
        if (trigger) {
            steps.push({
                isActive: ["auto", "mobile"],
                trigger,
            });
        }
        steps.push(
            {
                isActive: ["auto", "mobile"],
                trigger: ".o_cp_action_menus",
                run: (actions) => {
                    const node = hoot.queryFirst(".o_cp_action_menus .fa-cog");
                    if (node) {
                        hoot.click(node);
                    }
                },
            },
            {
                trigger: `.o_statusbar_buttons button:enabled:contains('${innerTextButton}'), .dropdown-item button:enabled:contains('${innerTextButton}')`,
                content: description,
                tooltipPosition: "bottom",
                run: "click",
            }
        );
        return steps.map((step) =>
            this.addDebugHelp(
                this._getHelpMessage("statusbarButtonsSteps", innerTextButton, description),
                step
            )
        );
    },

    mobileKanbanSearchMany2X(modalTitle, valueSearched) {
        return [
            {
                isActive: ["mobile"],
                trigger: `.modal:not(.o_inactive_modal) .o_control_panel_navigation .btn .fa-search`,
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                tooltipPosition: "bottom",
                run: `edit ${valueSearched}`,
            },
            {
                isActive: ["mobile"],
                trigger: ".dropdown-menu.o_searchview_autocomplete",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                tooltipPosition: "bottom",
                run: "press Enter",
            },
            {
                isActive: ["mobile"],
                trigger: `.o_kanban_record:contains('${valueSearched}')`,
                tooltipPosition: "bottom",
                run: "click",
            },
        ].map((step) =>
            this.addDebugHelp(
                this._getHelpMessage("mobileKanbanSearchMany2X", modalTitle, valueSearched),
                step
            )
        );
    },
    /**
     * Utility steps to save a form and wait for the save to complete
     */
    saveForm() {
        return [
            {
                isActive: ["auto"],
                content: "save form",
                trigger: ".o_form_button_save:enabled",
                run: "click",
            },
            {
                content: "wait for save completion",
                trigger: ".o_form_readonly, .o_form_saved",
            },
        ];
    },
    /**
     * Utility steps to cancel a form creation or edition.
     *
     * Supports creation/edition from either a form or a list view (so checks
     * for both states).
     */
    discardForm() {
        return [
            {
                isActive: ["auto"],
                content: "discard the form",
                trigger: ".o_form_button_cancel",
                run: "click",
            },
            {
                content: "wait for cancellation to complete",
                trigger:
                    ".o_view_controller.o_list_view, .o_form_view > div > div > .o_form_readonly, .o_form_view > div > div > .o_form_saved",
            },
        ];
    },

    waitIframeIsReady() {
        return {
            content: "Wait until the iframe is ready",
            trigger: `iframe[is-ready=true]:iframe html`,
        };
    },

    goToUrl(url) {
        return {
            isActive: ["auto"],
            content: `Navigate to ${url}`,
            trigger: "body",
            run: `goToUrl ${url}`,
        };
    },
};
