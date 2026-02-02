/**
 * Helpers for testing interactions within the Website Builder iframe.
 *
 * This module provides mechanisms to:
 * - Inject interaction loader into iframe
 * - Load specific interactions with patches
 * - Access interaction instances directly
 * - Control interaction lifecycle
 * - Provide rich debugging API
 */

import { registry } from "@web/core/registry";
import { clearRegistry } from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";

// Inlined loader script (injected into iframe)
const loaderScript = `
(function(window) {
    'use strict';

    const InteractionLoader = {
        instances: new Map(),
        classes: new Map(),
        loadedModules: new Set(),
        status: {
            loaded: [],
            active: [],
            patched: [],
            errors: []
        },

        getRegistryKey(interactionName, editMode = false) {
            // If it already looks like a registry key (contains .), use it directly
            if (interactionName.includes('.')) {
                return [interactionName];
            }

            // Try common patterns
            const patterns = [
                \`website.\${interactionName}\`,
                interactionName,
            ];

            // In edit mode, also try _edit suffix
            if (editMode) {
                patterns.unshift(\`website.\${interactionName}_edit\`);
                patterns.push(\`\${interactionName}_edit\`);
            }

            return patterns;
        },

        async loadModule(modulePath) {
            // Check if module is already loaded
            let module = window.odoo.loader.modules.get(modulePath);
            if (module) {
                this.loadedModules.add(modulePath);
                return module;
            }

            // If not loaded, wait a bit and try again (module should be loaded by bundles)
            for (let i = 0; i < 50; i++) {
                await new Promise(resolve => setTimeout(resolve, 100));
                module = window.odoo.loader.modules.get(modulePath);
                if (module) {
                    this.loadedModules.add(modulePath);
                    return module;
                }
            }

            throw new Error(\`Module \${modulePath} not found after waiting\`);
        },

        applyPatches(InteractionClass, patches, name) {
            if (!patches) return InteractionClass;

            const proto = InteractionClass.prototype;
            const patchedMethods = {};

            for (const [methodName, patchFn] of Object.entries(patches)) {
                const original = proto[methodName];

                patchedMethods[methodName] = function(...args) {
                    return patchFn.call(this, original ? original.bind(this) : null, ...args);
                };
            }

            Object.assign(proto, patchedMethods);

            this.status.patched.push(name);
            return InteractionClass;
        },

        async load(config) {
            const { interactions, editMode = false, patches = {}, autoStart = true } = config;

            // Get registry from module loader
            const registryModule = window.odoo.loader.modules.get('@web/core/registry');
            if (!registryModule) {
                throw new Error('Registry module not found');
            }

            const registry = registryModule.registry;
            const interactionRegistry = editMode
                ? registry.category('public.interactions.edit')
                : registry.category('public.interactions');

            for (const interactionName of interactions) {
                try {
                    // Get possible registry keys
                    const registryKeys = this.getRegistryKey(interactionName, editMode);

                    let registryEntry = null;
                    let foundKey = null;

                    // Try each possible registry key
                    for (const key of registryKeys) {
                        registryEntry = interactionRegistry.get(key, null);
                        if (registryEntry) {
                            foundKey = key;
                            break;
                        }
                    }

                    if (!registryEntry) {
                        // Try to find it by searching all registry entries
                        const allEntries = interactionRegistry.getEntries();
                        for (const [key, entry] of allEntries) {
                            if (key.endsWith(\`.\${interactionName}\`) ||
                                key.endsWith(\`.\${interactionName}_edit\`) ||
                                key === interactionName) {
                                registryEntry = entry;
                                foundKey = key;
                                break;
                            }
                        }
                    }

                    if (!registryEntry) {
                        const availableKeys = interactionRegistry.getEntries().map(([k]) => k).join(', ');
                        throw new Error(\`Interaction not found in registry. Tried: \${registryKeys.join(', ')}. Available: \${availableKeys}\`);
                    }

                    let InteractionClass;
                    if (editMode && registryEntry.Interaction) {
                        InteractionClass = registryEntry.mixin
                            ? registryEntry.mixin(registryEntry.Interaction)
                            : registryEntry.Interaction;
                    } else {
                        InteractionClass = editMode ? registryEntry : registryEntry;
                    }

                    if (patches[interactionName]) {
                        InteractionClass = this.applyPatches(
                            InteractionClass,
                            patches[interactionName],
                            interactionName
                        );
                    }

                    this.classes.set(interactionName, InteractionClass);
                    this.status.loaded.push(interactionName);

                    if (autoStart) {
                        await this.start(interactionName);
                    }

                } catch (error) {
                    this.status.errors.push({
                        interaction: interactionName,
                        error: error.message,
                        stack: error.stack
                    });
                    console.error(\`Failed to load interaction \${interactionName}:\`, error);
                }
            }

            return this.getStatus();
        },

        async start(interactionName, selector = null) {
            const InteractionClass = this.classes.get(interactionName);
            if (!InteractionClass) {
                throw new Error(\`Interaction \${interactionName} not loaded\`);
            }

            // Find elements to attach to
            let elements;
            if (selector) {
                elements = Array.from(window.document.querySelectorAll(selector));
            } else {
                // Use default selector based on interaction name
                const defaultSelector = \`.s_\${interactionName}\`;
                elements = Array.from(window.document.querySelectorAll(defaultSelector));
            }

            if (elements.length === 0) {
                return;
            }

            // Get environment from Owl Component (set by createPublicRoot)
            const { Component } = window.odoo.loader.modules.get('@odoo/owl');
            const env = Component.env;

            if (!env || !env.services) {
                throw new Error('Environment not available on Component.env');
            }

            // Create and start instances manually
            for (const element of elements) {
                try {
                    // Create instance with iframe's environment
                    // Constructor signature: (el, env, metadata)
                    const metadata = { __colibri__: { name: interactionName } };
                    const instance = new InteractionClass(element, env, metadata);

                    // Call lifecycle methods
                    if (instance.willStart) {
                        await instance.willStart();
                    }

                    if (instance.start) {
                        await instance.start();
                    }

                    // Store instance with a unique key
                    const key = \`\${interactionName}:\${element.dataset?.snippet || this.instances.size}\`;
                    this.instances.set(key, instance);

                    if (!this.status.active.includes(interactionName)) {
                        this.status.active.push(interactionName);
                    }

                } catch (error) {
                    this.status.errors.push({
                        interaction: interactionName,
                        element: element.outerHTML.slice(0, 100),
                        error: error.message,
                        stack: error.stack
                    });
                    console.error(\`Failed to start interaction \${interactionName}:\`, error);
                }
            }
        },

        getInstance(interactionName, index = 0) {
            const keys = Array.from(this.instances.keys())
                .filter(k => k.startsWith(\`\${interactionName}:\`));

            if (keys.length === 0) return null;
            return this.instances.get(keys[index]);
        },

        getAllInstances(interactionName) {
            const instances = [];
            for (const [key, instance] of this.instances.entries()) {
                if (key.startsWith(\`\${interactionName}:\`)) {
                    instances.push(instance);
                }
            }
            return instances;
        },

        async stop() {
            // Destroy all instances we created
            for (const [key, instance] of this.instances.entries()) {
                try {
                    if (instance.destroy) {
                        await instance.destroy();
                    }
                } catch (error) {
                    console.error(\`Error destroying \${key}:\`, error);
                }
            }

            this.instances.clear();
            this.status.active = [];
        },

        getStatus() {
            return {
                ...this.status,
                instanceCount: this.instances.size,
                loadedModules: Array.from(this.loadedModules)
            };
        },

        async trigger(selector, interactionName) {
            const elements = Array.from(window.document.querySelectorAll(selector));
            if (elements.length === 0) {
                throw new Error(\`No elements found for selector: \${selector}\`);
            }

            await this.start(interactionName, selector);
        }
    };

    window.__interactionLoader = InteractionLoader;

})(window);
`;

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
 * Initialize the interaction system in the iframe using the injected loader.
 *
 * @param {HTMLIFrameElement} iframe - The builder iframe element
 * @param {Object} options - Configuration options
 * @param {string[]} options.interactions - Array of interaction names to load
 * @param {boolean} options.editMode - Whether to load edit interactions (default: true)
 * @param {Object} options.patches - Patches to apply to interactions
 * @param {boolean} options.autoStart - Whether to auto-start interactions (default: true)
 * @returns {Promise<Object>} Interaction API object
 */
export async function initializeBuilderInteractions(iframe, options = {}) {
    const { interactions = [], editMode = true, patches = {}, autoStart = true } = options;

    const iframeDoc = iframe.contentDocument;
    const iframeWin = iframe.contentWindow;

    if (!iframeDoc || !iframeWin) {
        throw new Error("Invalid iframe: contentDocument or contentWindow is not available");
    }

    // Wait for Odoo to be loaded in iframe
    await waitForOdooReady(iframeWin);

    // Wait for iframe environment to be initialized
    await waitForIframeEnv(iframeWin);

    // Inject the loader script into iframe
    const scriptEl = iframeDoc.createElement("script");
    scriptEl.textContent = loaderScript;
    iframeDoc.head.appendChild(scriptEl);

    // Wait for loader to be available
    await new Promise((resolve) => {
        const checkLoader = () => {
            if (iframeWin.__interactionLoader) {
                resolve();
            } else {
                setTimeout(checkLoader, 10);
            }
        };
        checkLoader();
    });

    const loader = iframeWin.__interactionLoader;

    // Convert patches to serializable format (functions to objects)
    const serializablePatches = {};
    for (const [name, patchFn] of Object.entries(patches)) {
        if (typeof patchFn === "function") {
            // Call patch function to get the patch object
            serializablePatches[name] = patchFn();
        } else {
            serializablePatches[name] = patchFn;
        }
    }

    // Load interactions
    await loader.load({
        interactions,
        editMode,
        patches: serializablePatches,
        autoStart,
    });

    // Return API for controlling interactions
    return {
        iframe,
        iframeDoc,
        iframeWin,
        loader,

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
         * Get a specific interaction instance
         */
        getInstance(name, index = 0) {
            return loader.getInstance(name, index);
        },

        /**
         * Get all instances of an interaction
         */
        getAllInstances(name) {
            return loader.getAllInstances(name);
        },

        /**
         * Get current status of loaded interactions
         */
        getStatus() {
            return loader.getStatus();
        },

        /**
         * Start an interaction on specific elements
         */
        async start(name, selector = null) {
            return loader.start(name, selector);
        },

        /**
         * Trigger an interaction on specific element
         */
        async trigger(selector, name) {
            return loader.trigger(selector, name);
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
        async restartInteractions(element = iframeDoc.body) {
            const service = iframeWin.odoo?.__env__?.services?.["public.interactions"];
            if (service) {
                service.stopInteractions(element);
                await service.startInteractions(element);
            }
        },

        /**
         * Stop all interactions
         */
        async stopInteractions(element = iframeDoc.body) {
            await loader.stop();

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
 * Wait for iframe environment to be initialized with services
 * The env is stored on Component.env by createPublicRoot
 */
async function waitForIframeEnv(iframeWin, timeout = 5000) {
    const start = Date.now();

    while (Date.now() - start < timeout) {
        try {
            const { Component } = iframeWin.odoo?.loader?.modules?.get("@odoo/owl") || {};
            if (Component?.env?.services) {
                return;
            }
            // eslint-disable-next-line no-unused-vars
        } catch (e) {
            // Module not loaded yet, continue waiting
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }

    throw new Error("Timeout waiting for iframe Component.env to be initialized");
}

/**
 * Wait for Odoo to be loaded in iframe
 */
async function waitForOdooReady(iframeWin, timeout = 15000) {
    const start = Date.now();
    let lastCheck = {};

    while (Date.now() - start < timeout) {
        // Check if Odoo module system is available
        const hasOdoo = !!iframeWin.odoo;
        const hasLoader = !!iframeWin.odoo?.loader;
        const hasModules = !!iframeWin.odoo?.loader?.modules;

        lastCheck = { hasOdoo, hasLoader, hasModules };

        if (hasLoader && hasModules) {
            // Check if we can access the registry module
            try {
                const registryModule = iframeWin.odoo.loader.modules.get("@web/core/registry");
                if (registryModule?.registry) {
                    return;
                }
                // eslint-disable-next-line no-unused-vars
            } catch (e) {
                // Registry not ready yet, continue waiting
            }
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }

    throw new Error(
        `Timeout waiting for Odoo to be ready in iframe. Last check: ${JSON.stringify(lastCheck)}`
    );
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
