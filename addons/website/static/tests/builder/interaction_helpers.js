/**
 * Helpers for testing interactions within the Website Builder iframe.
 *
 * This module provides mechanisms to:
 * - Load interaction bundles in the iframe
 * - Load and start the edit service
 * - Initialize the interaction service
 * - Whitelist specific interactions
 * - Patch interaction logic before initialization
 * - Communicate with the iframe's interaction service
 */

import { registry } from "@web/core/registry";
import { clearRegistry } from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";

const interactionRegistry = registry.category("public.interactions");
const interactionEditRegistry = registry.category("public.interactions.edit");

let activeWhiteList = null;
const activePatches = new Map();

// Store original content so we can restore it
const originalInteractionContent = {};
const originalEditContent = {};

// Capture original content on first access
function captureOriginalContent() {
    if (Object.keys(originalInteractionContent).length === 0) {
        for (const [key, value] of Object.entries(interactionRegistry.content)) {
            originalInteractionContent[key] = value;
        }
    }
    if (Object.keys(originalEditContent).length === 0) {
        for (const [key, value] of Object.entries(interactionEditRegistry.content)) {
            originalEditContent[key] = value;
        }
    }
}

/**
 * Setup interaction whitelist for builder tests.
 * Only the specified interactions will be loaded in the iframe.
 *
 * @param {string|string[]} interactions - Interaction name(s) to whitelist
 */
export function setupBuilderInteractionWhiteList(interactions) {
    if (arguments.length > 1) {
        throw new Error("Multiple white-listed interactions should be listed in an array.");
    }
    if (typeof interactions === "string") {
        interactions = [interactions];
    }
    activeWhiteList = interactions;
    captureOriginalContent();
}

/**
 * Get the current interaction whitelist
 * @returns {string[]|null}
 */
setupBuilderInteractionWhiteList.getWhiteList = () => activeWhiteList;

/**
 * Clear the interaction whitelist
 */
export function clearBuilderInteractionWhiteList() {
    activeWhiteList = null;
}

/**
 * Patch an interaction before it's loaded in the iframe.
 * This allows modifying interaction behavior for testing.
 *
 * @param {string} interactionName - Name of the interaction to patch
 * @param {Function} patchFn - Function that receives the Interaction class and returns a patched version
 *
 * @example
 * patchBuilderInteraction("website.carousel_bootstrap_upgrade_fix", (InteractionClass) => {
 *     return class extends InteractionClass {
 *         get customBehavior() { return true; }
 *     };
 * });
 */
export function patchBuilderInteraction(interactionName, patchFn) {
    if (!activePatches.has(interactionName)) {
        activePatches.set(interactionName, []);
    }
    activePatches.get(interactionName).push(patchFn);
    captureOriginalContent();
}

/**
 * Clear all interaction patches
 */
export function clearBuilderInteractionPatches() {
    activePatches.clear();
}

/**
 * Mock loadBundle for specific bundles used by interactions.
 * This allows tests to skip loading heavy external libraries.
 *
 * @param {string|string[]} bundleNames - Bundle name(s) to mock
 *
 * @example
 * mockInteractionBundle("web.chartjs_lib");
 * mockInteractionBundle(["web.chartjs_lib", "web.some_other_lib"]);
 */
export function mockInteractionBundle(bundleNames) {
    // eslint-disable-next-line no-undef
    const { patchWithCleanup } = require("@web/../tests/web_test_helpers");
    // const { loadBundle } = require("@web/core/assets");

    const bundles = Array.isArray(bundleNames) ? bundleNames : [bundleNames];

    patchWithCleanup(loadBundle, async (bundleName, options) => {
        if (bundles.includes(bundleName)) {
            return Promise.resolve();
        }
        return loadBundle.wrappedMethod.call(loadBundle, bundleName, options);
    });
}

/**
 * Apply patches to an interaction class
 * @private
 */
function applyInteractionPatches(name, InteractionClass) {
    const patches = activePatches.get(name);
    if (!patches || patches.length === 0) {
        return InteractionClass;
    }

    let PatchedClass = InteractionClass;
    for (const patchFn of patches) {
        PatchedClass = patchFn(PatchedClass);
    }
    return PatchedClass;
}

/**
 * Prepare the iframe window to support interactions.
 * This injects necessary code and prepares the environment.
 *
 * @param {Window} iframeWin - The iframe window object
 * @param {Document} iframeDoc - The iframe document
 */
function prepareIframeForInteractions(iframeWin, iframeDoc) {
    // Ensure wrapwrap exists
    if (!iframeDoc.getElementById("wrapwrap")) {
        const wrap = iframeDoc.querySelector("#wrap");
        if (wrap && wrap.parentElement) {
            wrap.parentElement.id = "wrapwrap";
        }
    }

    // Mark the body as ready for interactions
    if (!iframeDoc.body.hasAttribute("is-ready")) {
        iframeDoc.body.setAttribute("is-ready", "true");
    }
}

/**
 * Initialize the interaction system in the iframe.
 * This function:
 * 1. Prepares the iframe environment
 * 2. Applies whitelisting and patches to registries
 * 3. Returns utilities to control interactions
 *
 * Note: When called after bundles are loaded, the services should already be running.
 *
 * @param {HTMLIFrameElement} iframe - The builder iframe element
 * @param {Object} options - Configuration options
 * @param {boolean} options.editMode - Whether to start in edit mode (default: true)
 * @param {boolean} options.waitForStart - Whether to wait for interactions to start (default: true)
 * @returns {Promise<Object>} Object with interaction service and utilities
 */
export async function initializeBuilderInteractions(iframe, options = {}) {
    const { waitForStart = true } = options;
    const iframeDoc = iframe.contentDocument;
    const iframeWin = iframe.contentWindow;

    if (!iframeDoc || !iframeWin) {
        throw new Error("Invalid iframe: contentDocument or contentWindow is not available");
    }

    // Prepare the iframe environment
    prepareIframeForInteractions(iframeWin, iframeDoc);

    // Apply whitelist and patches to the parent registries
    // This must be done BEFORE bundles are loaded in the iframe
    applyWhitelistAndPatches();

    // Wait for services to be ready (if they're being loaded)
    if (waitForStart && iframeWin.odoo?.__env__?.services?.["public.interactions"]) {
        const service = iframeWin.odoo.__env__.services["public.interactions"];
        if (service.isReady) {
            await service.isReady;
        }
    }

    // Return utilities to control interactions
    return {
        iframe,
        iframeDoc,
        iframeWin,

        /**
         * Get the interaction service from the iframe (if available)
         */
        get interactionService() {
            return iframeWin.odoo?.__env__?.services?.["public.interactions"];
        },

        /**
         * Get the edit service from the iframe (if available)
         */
        get editService() {
            return iframeWin.odoo?.__env__?.services?.website_edit;
        },

        /**
         * Wait for the interaction service to be ready
         */
        waitReady: async () => {
            const service = iframeWin.odoo?.__env__?.services?.["public.interactions"];
            if (service && service.isReady) {
                await service.isReady;
            }
        },

        /**
         * Restart interactions on a specific element
         */
        restartInteractions: async (element = iframeDoc.body) => {
            const service = iframeWin.odoo?.__env__?.services?.["public.interactions"];
            if (service) {
                service.stopInteractions(element);
                await service.startInteractions(element);
            }
        },

        /**
         * Stop all interactions
         */
        stopInteractions: (element = iframeDoc.body) => {
            const service = iframeWin.odoo?.__env__?.services?.["public.interactions"];
            if (service) {
                service.stopInteractions(element);
            }
        },

        /**
         * Switch between edit and preview modes
         */
        switchMode: async (mode) => {
            const editService = iframeWin.odoo?.__env__?.services?.website_edit;
            if (editService) {
                if (mode === "edit") {
                    editService.update(iframeDoc.body, "edit");
                } else if (mode === "preview") {
                    editService.update(iframeDoc.body, "preview");
                } else {
                    editService.update(iframeDoc.body);
                }
            }
        },
    };
}

/**
 * Apply whitelist and patches to the interaction registries
 * @private
 */
function applyWhitelistAndPatches() {
    captureOriginalContent();

    if (activeWhiteList && activeWhiteList.length > 0) {
        // Clear and rebuild with whitelist
        clearRegistry(interactionRegistry);
        clearRegistry(interactionEditRegistry);

        for (const name of activeWhiteList) {
            // Add main interaction
            if (originalInteractionContent[name]) {
                const [sequence, InteractionClass] = originalInteractionContent[name];
                const PatchedClass = applyInteractionPatches(name, InteractionClass);
                interactionRegistry.add(name, PatchedClass, { sequence });
            }

            // Add edit interaction
            if (originalEditContent[name]) {
                const [sequence, editConfig] = originalEditContent[name];
                const patchedConfig = { ...editConfig };
                if (patchedConfig.Interaction) {
                    patchedConfig.Interaction = applyInteractionPatches(
                        name,
                        patchedConfig.Interaction
                    );
                }
                interactionEditRegistry.add(name, patchedConfig, { sequence });
            }
        }
    } else if (activePatches.size > 0) {
        // Only apply patches, keep all interactions
        // We need to re-add with patches applied
        clearRegistry(interactionRegistry);
        clearRegistry(interactionEditRegistry);

        for (const [name, [sequence, InteractionClass]] of Object.entries(
            originalInteractionContent
        )) {
            const PatchedClass = applyInteractionPatches(name, InteractionClass);
            interactionRegistry.add(name, PatchedClass, { sequence });
        }

        for (const [name, [sequence, editConfig]] of Object.entries(originalEditContent)) {
            const patchedConfig = { ...editConfig };
            if (patchedConfig.Interaction) {
                patchedConfig.Interaction = applyInteractionPatches(
                    name,
                    patchedConfig.Interaction
                );
            }
            interactionEditRegistry.add(name, patchedConfig, { sequence });
        }
    }
}

/**
 * Helper to switch to edit mode in an interaction test.
 * This is useful when testing edit-specific behavior.
 *
 * @param {Object} interactionCore - The interaction core returned by startInteractions
 */
export async function switchToEditMode(interactionCore) {
    if (!interactionCore) {
        return;
    }

    // Enable edit mode flag
    interactionCore.editMode = true;

    // Try to load edit interactions
    const editRegistry = registry.category("public.interactions.edit");
    const builders = editRegistry.getAll();

    if (builders.length > 0) {
        try {
            // Try to get the build function
            const websiteEditModule = odoo.loader.modules.get("@website/core/website_edit_service");
            if (websiteEditModule && websiteEditModule.buildEditableInteractions) {
                const { buildEditableInteractions } = websiteEditModule;
                const editableInteractions = buildEditableInteractions(builders);

                // Restart with editable interactions
                interactionCore.stopInteractions();
                interactionCore.activate(editableInteractions);
                await interactionCore.isReady;
            }
        } catch (error) {
            console.warn("Could not switch to edit mode:", error);
        }
    }
}

/**
 * Cleanup function to reset interaction state after tests
 */
export function cleanupBuilderInteractions() {
    // Restore original registries
    if (activeWhiteList || activePatches.size > 0) {
        clearRegistry(interactionRegistry);
        clearRegistry(interactionEditRegistry);

        // Restore original content
        for (const [name, [sequence, InteractionClass]] of Object.entries(
            originalInteractionContent
        )) {
            interactionRegistry.add(name, InteractionClass, { sequence });
        }
        for (const [name, [sequence, editConfig]] of Object.entries(originalEditContent)) {
            interactionEditRegistry.add(name, editConfig, { sequence });
        }
    }

    clearBuilderInteractionWhiteList();
    clearBuilderInteractionPatches();
}
