// @odoo-module ignore

//-----------------------------------------------------------------------------
// Odoo Web Boostrap Code
//-----------------------------------------------------------------------------

(function () {
    "use strict";

    if (globalThis.odoo?.loader) {
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
         * @param {HTMLElement} [target]
         */
        constructor(target) {
            this.target = target || window.top.document.body;
        }

        /** @type {OdooModuleLoader["addJob"]} */
        addJob(name) {
            this.jobs.add(name);
            this.startModules();
        }

        /** @type {OdooModuleLoader["checkAndReportErrors"]} */
        async checkAndReportErrors() {
            const { failed, cycle, missing, unloaded } = this.findErrors();
            if (!failed.length && !unloaded.length) {
                return;
            }

            /**
             * @param {string} heading
             * @param {string[]} names
             */
            function createList(heading, names) {
                const frag = document.createDocumentFragment();
                if (!names || !names.length) {
                    return frag;
                }
                frag.textContent = heading;
                const ul = document.createElement("ul");
                for (const el of names) {
                    const li = document.createElement("li");
                    li.textContent = el;
                    ul.append(li);
                }
                frag.appendChild(ul);
                return frag;
            }

            const document = this.target.ownerDocument;
            if (document.readyState === "loading") {
                await new Promise((resolve) =>
                    document.addEventListener("DOMContentLoaded", resolve)
                );
            }

            // Empty body
            this.target.innerHTML = "";

            const container = document.createElement("div");
            container.className =
                "o_module_error position-fixed w-100 h-100 d-flex align-items-center flex-column bg-white overflow-auto modal";
            container.style.zIndex = "10000";
            const alert = document.createElement("div");
            alert.className = "alert alert-danger o_error_detail fw-bold m-auto";
            container.appendChild(alert);
            alert.appendChild(
                createList(
                    "The following modules failed to load because of an error, you may find more information in the devtools console:",
                    failed
                )
            );
            alert.appendChild(
                createList(
                    "The following modules could not be loaded because they form a dependency cycle:",
                    cycle && [cycle]
                )
            );
            alert.appendChild(
                createList(
                    "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:",
                    missing
                )
            );
            alert.appendChild(
                createList(
                    "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
                    unloaded
                )
            );
            this.target.appendChild(container);
        }

        /** @type {OdooModuleLoader["define"]} */
        define(name, deps, factory, lazy = false) {
            if (typeof name !== "string") {
                throw new Error(`Module name should be a string, got: ${name}`);
            }
            if (!Array.isArray(deps) || deps.some((dep) => typeof dep !== "string")) {
                throw new Error(`Module dependencies should be an array of strings, got: ${deps}`);
            }
            if (typeof factory !== "function") {
                throw new Error(`Module factory should be a function, got: ${factory}`);
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
                    this.checkAndReportErrors();
                    this.checkErrorProm = null;
                });
            }
        }

        /** @type {OdooModuleLoader["findErrors"]} */
        findErrors() {
            /**
             * @param {string[]} jobs
             * @param {string[]} visited
             */
            function visitJobs(jobs, visited = new Set()) {
                for (const job of jobs) {
                    if (visited.has(job)) {
                        const jobs = [...visited, job];
                        const index = jobs.indexOf(job);
                        return jobs
                            .slice(index)
                            .map((j) => `"${j}"`)
                            .join(" => ");
                    }
                    const deps = dependencyGraph[job];
                    if (deps) {
                        return visitJobs(deps, new Set(visited).add(job));
                    }
                }
                return null;
            }

            /**
             * cycle detection
             * @type {Record<string, string[]>}
             */
            const dependencyGraph = Object.create(null);

            /**
             * missing dependencies
             * @type {Set<string>}
             */
            const missing = new Set();

            for (const job of this.jobs) {
                const { deps, ignoreMissingDeps } = this.factories.get(job);

                dependencyGraph[job] = deps;

                if (ignoreMissingDeps) {
                    continue;
                }
                for (const dep of deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            return {
                cycle: visitJobs(this.jobs),
                failed: [...this.failed],
                missing: [...missing],
                unloaded: [...this.jobs].filter((j) => !this.factories.get(j).ignoreMissingDeps),
            };
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
            let value = null;
            try {
                value = factory.fn(require);
            } catch (error) {
                this.failed.add(name);
                throw new Error(`Error while loading "${name}":\n${error}`);
            }
            this.modules.set(name, value);
            this.bus.dispatchEvent(
                new CustomEvent("module-started", {
                    detail: { moduleName: name, module: value },
                })
            );
            return value;
        }
    }

    const odoo = (globalThis.odoo ||= {});
    if (odoo.debug && !new URLSearchParams(location.search).has("debug")) {
        // remove debug mode if not explicitely set in url
        odoo.debug = "";
    }

    const loader = new ModuleLoader();
    odoo.define = loader.define.bind(loader);
    odoo.loader = loader;
})();
