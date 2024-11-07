// @odoo-module ignore

//-----------------------------------------------------------------------------
// Odoo Web Boostrap Code
//-----------------------------------------------------------------------------

(function (odoo) {
    "use strict";

    if (odoo.loader) {
        // Allows for duplicate calls to `module_loader`: only the first one is
        // executed.
        return;
    }

    class ModuleLoader {
        /** @type {OdooModuleLoader["bus"]} */
        bus = new EventTarget();
        /** @type {OdooModuleLoader["checkErrorProm"]} */
        checkErrorProm = null;
        /** @type {OdooModuleLoader["factories"]} */
        factories = new Map();
        /** @type {OdooModuleLoader["failed"]} */
        failed = new Set();
        /** @type {OdooModuleLoader["jobs"]} */
        jobs = new Set();
        /** @type {OdooModuleLoader["modules"]} */
        modules = new Map();

        /**
         * @param {HTMLElement} [root]
         */
        constructor(root) {
            this.root = root;
        }

        /** @type {OdooModuleLoader["addJob"]} */
        addJob(name) {
            this.jobs.add(name);
            this.startModules();
        }

        /** @type {OdooModuleLoader["define"]} */
        define(name, deps, factory, lazy = false) {
            if (typeof name !== "string") {
                throw new Error(`Module name should be a string, got: ${String(name)}`);
            }
            if (!Array.isArray(deps)) {
                throw new Error(
                    `Module dependencies should be a list of strings, got: ${String(deps)}`
                );
            }
            if (typeof factory !== "function") {
                throw new Error(`Module factory should be a function, got: ${String(factory)}`);
            }
            if (this.factories.has(name)) {
                return; // Ignore duplicate modules
            }
            this.factories.set(name, {
                deps,
                fn: factory,
                ignoreMissingDeps: globalThis.__odooIgnoreMissingDependencies || lazy,
            });
            if (!lazy) {
                this.addJob(name);
                this.checkErrorProm ||= Promise.resolve().then(() => {
                    this.checkErrorProm = null;
                    this.reportErrors(this.findErrors());
                });
            }
        }

        /** @type {OdooModuleLoader["findErrors"]} */
        findErrors(moduleNames) {
            /**
             * @param {Iterable<string>} currentModuleNames
             * @param {Set<string>} visited
             * @returns {string | null}
             */
            const findCycle = (currentModuleNames, visited) => {
                for (const name of currentModuleNames || []) {
                    if (visited.has(name)) {
                        const cycleModuleNames = [...visited, name];
                        return cycleModuleNames
                            .slice(cycleModuleNames.indexOf(name))
                            .map((j) => `"${j}"`)
                            .join(" => ");
                    }
                    const cycle = findCycle(dependencyGraph[name], new Set(visited).add(name));
                    if (cycle) {
                        return cycle;
                    }
                }
                return null;
            };

            moduleNames ||= this.jobs;

            /** @type {Record<string, Iterable<string>>} */
            const dependencyGraph = Object.create(null);
            /** @type {Set<string>} */
            const missing = new Set();
            /** @type {Set<string>} */
            const unloaded = new Set();

            for (const moduleName of moduleNames) {
                const { deps, ignoreMissingDeps } = this.factories.get(moduleName);

                dependencyGraph[moduleName] = deps;

                if (ignoreMissingDeps) {
                    continue;
                }

                unloaded.add(moduleName);
                for (const dep of deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            const cycle = findCycle(unloaded, new Set());
            const errors = {};
            if (cycle) {
                errors.cycle = cycle;
            }
            if (this.failed.size) {
                errors.failed = this.failed;
            }
            if (missing.size) {
                errors.missing = missing;
            }
            if (unloaded.size) {
                errors.unloaded = unloaded;
            }
            return errors;
        }

        /** @type {OdooModuleLoader["findJob"]} */
        findJob() {
            for (const job of this.jobs) {
                if (this.factories.get(job).deps.every((dep) => this.modules.has(dep))) {
                    return job;
                }
            }
            return null;
        }

        /** @type {OdooModuleLoader["reportErrors"]} */
        async reportErrors(errors) {
            if (!Object.keys(errors).length) {
                return;
            }

            const document = this.root?.ownerDocument || globalThis.document;
            if (document.readyState === "loading") {
                await new Promise((resolve) =>
                    document.addEventListener("DOMContentLoaded", resolve)
                );
            }

            this.root ||= document.body;

            const containerEl = document.createElement("div");
            containerEl.className =
                "o_module_error position-fixed w-100 h-100 d-flex align-items-center flex-column bg-white overflow-auto modal";
            containerEl.style.zIndex = "10000";

            const alertEl = document.createElement("div");
            alertEl.className = "alert alert-danger o_error_detail fw-bold m-auto";
            containerEl.appendChild(alertEl);

            const errorHeadings = [];

            if (errors.failed) {
                errorHeadings.push([
                    "The following modules failed to load because of an error, you may find more information in the devtools console:",
                    [...errors.failed],
                ]);
            }
            if (errors.cycle) {
                errorHeadings.push([
                    "The following modules could not be loaded because they form a dependency cycle:",
                    [errors.cycle],
                ]);
            }
            if (errors.missing) {
                errorHeadings.push([
                    "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:",
                    [...errors.missing],
                ]);
            }
            if (errors.unloaded) {
                errorHeadings.push([
                    "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
                    [...errors.unloaded],
                ]);
            }

            for (const [heading, moduleNames] of errorHeadings) {
                const listEl = document.createElement("ul");
                for (const moduleName of moduleNames) {
                    const listItemEl = document.createElement("li");
                    listItemEl.textContent = moduleName;
                    listEl.appendChild(listItemEl);
                }

                alertEl.appendChild(document.createTextNode(heading));
                alertEl.appendChild(listEl);
            }

            this.root.innerHTML = "";
            this.root.appendChild(containerEl);
        }

        /** @type {OdooModuleLoader["startModules"]} */
        startModules() {
            let job;
            while ((job = this.findJob())) {
                this.startModule(job);
            }
        }

        /** @type {OdooModuleLoader["startModule"]} */
        startModule(name) {
            /** @type {(dependency: string) => OdooModule} */
            const require = (dependency) => this.modules.get(dependency);
            this.jobs.delete(name);
            const factory = this.factories.get(name);
            /** @type {OdooModule | null} */
            let module = null;
            try {
                module = factory.fn(require);
            } catch (error) {
                this.failed.add(name);
                throw new Error(`Error while loading "${name}":\n${error}`);
            }
            this.modules.set(name, module);
            this.bus.dispatchEvent(
                new CustomEvent("module-started", {
                    detail: { moduleName: name, module },
                })
            );
            return module;
        }
    }

    if (odoo.debug && !new URLSearchParams(location.search).has("debug")) {
        // remove debug mode if not explicitely set in url
        odoo.debug = "";
    }

    const loader = new ModuleLoader();
    odoo.define = loader.define.bind(loader);
    odoo.loader = loader;
})((globalThis.odoo ||= {}));
