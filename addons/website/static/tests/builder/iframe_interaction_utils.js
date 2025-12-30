/**
 * Utilities for enabling and testing interactions within the Website Builder iframe.
 *
 * This module provides mechanisms to:
 * - Load interaction bundles in the iframe
 * - Initialize the interaction service
 * - Whitelist specific interactions
 * - Patch interaction logic before initialization
 * - Communicate with the iframe's interaction service
 */

import { queryOne } from "@odoo/hoot-dom";
import { loadBundle } from "@web/core/assets";
import { session } from "@web/session";

/**
 * Bootstrap code that initializes the interaction system in the iframe.
 * This code is injected and executed in the iframe's context.
 *
 * @type {string}
 */
const IFRAME_BOOTSTRAP_CODE = `
(function() {
    // Store patches to apply before interactions load
    // Note: patches may already be set by patchInitScript
    window.__iframeInteractionPatches = window.__iframeInteractionPatches || {};
    window.__patchedInteractions = new Set();
    
    // Track when the interaction service is ready
    window.__iframeInteractionReady = new Promise((resolve) => {
        window.__resolveInteractionReady = resolve;
    });

    // Helper function to apply patches to interaction classes
    window.__applyInteractionPatches = function() {
        if (!window.__iframeInteractionPatches || Object.keys(window.__iframeInteractionPatches).length === 0) {
            return;
        }
        
        try {
            if (!odoo?.loader?.modules?.has?.('@web/core/registry')) {
                return;
            }
            
            const { registry } = odoo.loader.modules.get('@web/core/registry');
            const interactionRegistry = registry.category('public.interactions');
            const interactionEditRegistry = window.__enableEditInteractions ?
                registry.category('public.interactions.edit') : null;
            for (const [patchName, patchFn] of Object.entries(window.__iframeInteractionPatches)) {
                if (window.__patchedInteractions.has(patchName)) {
                    // Already patched
                    continue;
                }
                
                // Look for the interaction in registry
                if (interactionRegistry.content && interactionRegistry.content[patchName]) {
                    try {
                        let InteractionClass = interactionRegistry.content[patchName][1];

                        // Apply edit mixin if available
                        if (interactionEditRegistry?.content?.[patchName]) {
                            const editEntry = interactionEditRegistry.content[patchName][1];
                            if (editEntry.mixin && typeof editEntry.mixin === 'function') {
                                // Create a new class with the mixin applied
                                InteractionClass = editEntry.mixin(InteractionClass);
                                // Update the registry with the mixed class
                                interactionRegistry.content[patchName][1] = InteractionClass;
                            }
                        }
                        
                        // Call the patch function with the class
                        const patchObj = patchFn(InteractionClass);
                        
                        // Apply patch methods to the class prototype
                        if (patchObj && typeof patchObj === 'object') {
                            for (const [methodName, methodFn] of Object.entries(patchObj)) {
                                if (typeof methodFn === 'function') {
                                    InteractionClass.prototype[methodName] = methodFn;
                                }
                            }
                        }
                        
                        window.__patchedInteractions.add(patchName);
                    } catch (e) {
                        // Patch application failed
                    }
                }
            }
        } catch (e) {
            // Failed to apply patches
        }
    };

    // Expose API for tests to interact with the interaction service
    window.__iframeTestAPI = {
        // Get the current interaction service
        getCore: () => {
            if (odoo?.loader?.modules?.has?.("@web/public/interaction_service")) {
                const module = odoo.loader.modules.get("@web/public/interaction_service");
                return module?.publicInteractionService?.start ? 
                    window.odoo.__websitePublicInteractionService : 
                    null;
            }
            return null;
        },
        
        // Register a patch to be applied before interaction init
        registerPatch: (interactionName, patchFn) => {
            window.__iframeInteractionPatches[interactionName] = patchFn;
        },
        
        // Get registered patches
        getPatches: () => window.__iframeInteractionPatches,
        
        // Check if interaction service is ready
        isReady: () => !!window.__iframeInteractionService,
        
        // Wait for interaction service to be ready
        waitForReady: () => window.__iframeInteractionReady,
    };

    // Listen for interactions being added to the registry
    if (typeof odoo !== 'undefined' && odoo.loader) {
        const originalDefine = odoo.loader.modules.define;
        
        odoo.loader.modules.define = function(name, deps, factory) {
            const result = originalDefine.apply(this, arguments);
            
            // After each module definition, try to apply patches
            // This catches when interaction modules are loaded
            if (window.__iframeInteractionPatches && Object.keys(window.__iframeInteractionPatches).length > 0) {
                // Use a microtask to ensure the module is fully registered
                Promise.resolve().then(() => {
                    window.__applyInteractionPatches();
                });
            }
            
            return result;
        };
    }

    // Apply whitelist filter to interactions registry
    window.__applyWhitelistFilter = function() {
        if (!window.__interactionWhitelist || window.__interactionWhitelist.length === 0) {
            return;
        }

        try {
            if (!odoo?.loader?.modules?.has?.('@web/core/registry')) {
                return;
            }

            const { registry } = odoo.loader.modules.get('@web/core/registry');
            const interactionRegistry = registry.category('public.interactions');
            const editRegistry = registry.category('public.interactions.edit');

            // Store original content
            const originalContent = { ...interactionRegistry.content };
            const originalEditContent = editRegistry ? { ...editRegistry.content } : {};

            // Clear registries
            interactionRegistry.content = {};
            if (editRegistry) {
                editRegistry.content = {};
            }

            // Re-add only whitelisted interactions
            for (const name of window.__interactionWhitelist) {
                if (originalContent[name]) {
                    interactionRegistry.content[name] = originalContent[name];
                }
                if (editRegistry && originalEditContent[name]) {
                    editRegistry.content[name] = originalEditContent[name];
                }
            }
        } catch (e) {
            console.error('Failed to apply whitelist filter:', e);
        }
    };

    // Monitor for the public interaction service being created
    const checkForService = setInterval(() => {
        try {
            // Try to access the service
            if (typeof odoo !== 'undefined' && odoo.loader?.modules?.has?.('@web/public/interaction_service')) {
                clearInterval(checkForService);

                // Apply whitelist BEFORE interactions start
                window.__applyWhitelistFilter();

                // Final attempt to apply all patches before marking ready
                window.__applyInteractionPatches();
                
                // Mark as ready
                window.__iframeInteractionService = true;
                window.__resolveInteractionReady();
            }
        } catch (e) {
            // Service not ready yet
        }
    }, 100);

    // Safety timeout - mark as ready after 5 seconds anyway
    setTimeout(() => {
        clearInterval(checkForService);
        window.__applyInteractionPatches();
        window.__iframeInteractionService = true;
        window.__resolveInteractionReady();
    }, 5000);
})();
`;

/**
 * Injects and initializes the interaction system in an iframe.
 *
 * @param {HTMLIFrameElement} iframe - The iframe element
 * @param {Object} options - Configuration options
 * @param {string[]} options.whitelistInteractions - Array of interaction names to load
 * @param {Object.<string, Function>} options.patches - Patches to apply to interactions
 * @param {boolean} options.loadFrontendAssets - Whether to load web.assets_frontend (default: true)
 * @param {boolean} options.enableEditInteractions - Whether to load and apply edit mixins (default: false)
 * @returns {Promise<Object>} API object for interacting with iframe's interaction service
 */
export async function setupInteractionsInIframe(iframe, options = {}) {
    // eslint-disable-next-line no-unused-vars
    const {
        // eslint-disable-next-line no-unused-vars
        whitelistInteractions = [],
        patches = {},
        loadFrontendAssets = true,
        enableEditInteractions = false,
    } = options;

    const iframeDoc = iframe.contentDocument;
    const iframeWindow = iframe.contentWindow;

    // 1. Register patches FIRST - before any code runs
    // Store patch functions directly on iframe window so they're available when needed
    iframeWindow.__iframeInteractionPatches = iframeWindow.__iframeInteractionPatches || {};
    iframeWindow.__enableEditInteractions = enableEditInteractions;

    // Store all patch functions on the iframe window
    for (const [interactionName, patchFn] of Object.entries(patches)) {
        iframeWindow.__iframeInteractionPatches[interactionName] = patchFn;
    }

    // 2. Inject bootstrap code
    const bootstrapScript = iframeDoc.createElement("script");
    bootstrapScript.type = "text/javascript";
    bootstrapScript.textContent = IFRAME_BOOTSTRAP_CODE;
    iframeDoc.head.appendChild(bootstrapScript);

    // 3. Setup session info if needed
    if (loadFrontendAssets) {
        const sessionScript = iframeDoc.createElement("script");
        sessionScript.type = "text/javascript";
        sessionScript.textContent = `
            if (typeof odoo === 'undefined') {
                window.odoo = {};
            }
            if (typeof odoo.__session_info__ === 'undefined') {
                odoo.__session_info__ = ${JSON.stringify(session || {})};
            }
        `;
        iframeDoc.head.appendChild(sessionScript);
    }

    // 4. Load frontend assets (this will trigger interaction initialization)
    if (loadFrontendAssets) {
        await loadBundle("web.assets_frontend", {
            targetDoc: iframeDoc,
            js: true, // Enable JS loading
        });

        // 4b. If edit interactions are enabled, load the builder iframe bundle
        // which contains all edit interactions
        if (enableEditInteractions) {
            await loadBundle("website.assets_inside_builder_iframe", {
                targetDoc: queryOne("iframe[data-src^='/website/force/1']").contentDocument,
                js: true,
            });

            // Wait for bundles to fully load
            await new Promise((resolve) => setTimeout(resolve, 100));

            // Activate edit mode via website_edit service
            // This properly applies mixins using buildEditableInteractions()
            const activateEditScript = iframeDoc.createElement("script");
            activateEditScript.type = "text/javascript";
            activateEditScript.textContent = `
                (function() {
                    // Wait for website_edit service to be available
                    const waitForService = setInterval(() => {
                        try {
                            const websiteEdit = odoo.loader.modules.get('@website/core/website_edit_service');
                            if (websiteEdit && websiteEdit.websiteEditService) {
                                clearInterval(waitForService);

                                // Get the service instance
                                const env = odoo.__WOWL_DEBUG__?.root?.env;
                                if (env?.services?.website_edit) {
                                    const target = document.querySelector('#wrapwrap') || document.body;
                                    env.services.website_edit.update(target, 'edit');
                                }
                            }
                        } catch (e) {
                            // Service not ready yet
                        }
                    }, 50);

                    // Timeout after 2 seconds
                    setTimeout(() => clearInterval(waitForService), 2000);
                })();
            `;
            iframeDoc.head.appendChild(activateEditScript);
            // Wait for edit mode activation
            await new Promise((resolve) => setTimeout(resolve, 200));
        }
    }

    // 5. Give interactions a moment to initialize, then apply patches if not done yet
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Force apply patches in case they weren't applied during module loading
    const forceApplyScript = iframeDoc.createElement("script");
    forceApplyScript.type = "text/javascript";
    forceApplyScript.textContent = `
        if (window.__applyInteractionPatches) {
            window.__applyInteractionPatches();
        }
    `;
    iframeDoc.head.appendChild(forceApplyScript);

    // 6. Wait for the interaction service to be ready
    const iframeAPI = iframeWindow.__iframeTestAPI;
    if (iframeAPI?.waitForReady) {
        await iframeAPI.waitForReady();
        // Give it a moment to fully initialize
        await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // 6. Return API wrapper for test access
    return {
        /**
         * Get the interaction service from the iframe
         */
        getCore: () => {
            if (!iframeWindow.__iframeTestAPI) {
                throw new Error("Interaction API not initialized in iframe");
            }
            // The public interaction service is created by the startService function
            // Access it through the iframe window
            return iframeWindow.odoo?.loader?.modules?.get?.("@web/public/interaction_service")
                ?.publicInteractionService?.start;
        },

        /**
         * Check if interactions are ready
         */
        isReady: () => iframeWindow.__iframeTestAPI?.isReady?.() || false,

        /**
         * Wait for interactions to be ready
         */
        waitForReady: () => iframeWindow.__iframeTestAPI?.waitForReady?.() || Promise.resolve(),

        /**
         * Access the test API directly (advanced usage)
         */
        getTestAPI: () => iframeWindow.__iframeTestAPI,

        /**
         * Stop all interactions in the iframe
         */
        stopInteractions: (el) => {
            // Try multiple ways to get the service
            let service = iframeWindow.odoo?.__websitePublicInteractionService;

            // Fallback: try to get from env.services if available
            if (!service) {
                const env = iframeWindow.odoo?.__WOWL_DEBUG__?.root?.env;
                service = env?.services?.["public.interactions"];
            }

            if (service?.stopInteractions) {
                return service.stopInteractions(el);
            } else {
                console.warn("Cannot stop interactions: service not found or not ready");
            }
        },

        /**
         * Start interactions in the iframe
         */
        startInteractions: (el) => {
            // Try multiple ways to get the service
            let service = iframeWindow.odoo?.__websitePublicInteractionService;

            // Fallback: try to get from env.services if available
            if (!service) {
                const env = iframeWindow.odoo?.__WOWL_DEBUG__?.root?.env;
                service = env?.services?.["public.interactions"];
            }

            if (service?.startInteractions) {
                return service.startInteractions(el);
            } else {
                console.warn("Cannot start interactions: service not found or not ready");
            }
        },

        /**
         * Restart a specific interaction (stop then start on same element)
         * Useful when element attributes change and interaction needs to re-initialize
         */
        restartInteraction: (el) => {
            let service = iframeWindow.odoo?.__websitePublicInteractionService;

            if (!service) {
                const env = iframeWindow.odoo?.__WOWL_DEBUG__?.root?.env;
                service = env?.services?.["public.interactions"];
            }

            if (service?.stopInteractions && service?.startInteractions) {
                service.stopInteractions(el);
                return service.startInteractions(el);
            } else {
                console.warn("Cannot restart interaction: service not found or not ready");
            }
        },
    };
}

/**
 * Creates a patching function that can be registered with setupInteractionsInIframe.
 *
 * @param {HTMLIFrameElement} iframe - The iframe element
 * @returns {Promise<Object>} The interaction service instance
 */
export async function getIframeInteractionService(iframe) {
    const iframeWindow = iframe.contentWindow;

    // Wait for the service to be ready
    if (iframeWindow.__iframeTestAPI?.waitForReady) {
        await iframeWindow.__iframeTestAPI.waitForReady();
    }

    // The service is exposed as a singleton on the window
    return iframeWindow.odoo?.__publicInteractionService;
}
