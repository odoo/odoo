/**
 *------------------------------------------------------------------------------
 * Odoo Web Boostrap Code
 *------------------------------------------------------------------------------
 */
(function () {
    "use strict";

    class ModuleLoader {
        /** @type {Map<string,{fn: Function, deps: string[]}>} mapping name => deps/fn */
        factories = new Map();
        /** @type {Set<string>} names of modules waiting to be started */
        jobs = new Set();
        /** @type {Set<string>} names of failed modules */
        failed = new Set();

        /** @type {Map<string,any>} mapping name => value */
        modules = new Map();

        bus = new EventTarget();

        checkErrorProm = null;

        /**
         * @param {string} name
         * @param {string[]} deps
         * @param {Function} factory
         */
        define(name, deps, factory) {
            if (typeof name !== "string") {
                throw new Error(`Invalid name definition: ${name} (should be a string)"`);
            }
            if (!(deps instanceof Array)) {
                throw new Error(`Dependencies should be defined by an array: ${deps}`);
            }
            if (typeof factory !== "function") {
                throw new Error(`Factory should be defined by a function ${factory}`);
            }
            if (!this.factories.has(name)) {
                this.factories.set(name, {
                    deps,
                    fn: factory,
                    ignoreMissingDeps: globalThis.__odooIgnoreMissingDependencies,
                });
                this.addJob(name);
                this.checkErrorProm ||= Promise.resolve().then(() => {
                    this.checkAndReportErrors();
                    this.checkErrorProm = null;
                });
            }
        }

        addJob(name) {
            this.jobs.add(name);
            this.startModules();
        }

        findJob() {
            for (const job of this.jobs) {
                if (this.factories.get(job).deps.every((dep) => this.modules.has(dep))) {
                    return job;
                }
            }
            return null;
        }

        startModules() {
            let job;
            while ((job = this.findJob())) {
                this.startModule(job);
            }
        }

        startModule(name) {
            const require = (name) => this.modules.get(name);
            this.jobs.delete(name);
            const factory = this.factories.get(name);
            let value = null;
            try {
                value = factory.fn(require);
            } catch (error) {
                this.failed.add(name);
                throw new Error(`Error while loading "${name}":\n${error}`);
            }
            this.modules.set(name, value);
            this.bus.dispatchEvent(
                new CustomEvent("module-started", { detail: { moduleName: name, module: value } })
            );
        }

        findErrors() {
            // cycle detection
            const dependencyGraph = new Map();
            for (const job of this.jobs) {
                dependencyGraph.set(job, this.factories.get(job).deps);
            }
            function visitJobs(jobs, visited = new Set()) {
                for (const job of jobs) {
                    const result = visitJob(job, visited);
                    if (result) {
                        return result;
                    }
                }
                return null;
            }

            function visitJob(job, visited) {
                if (visited.has(job)) {
                    const jobs = Array.from(visited).concat([job]);
                    const index = jobs.indexOf(job);
                    return jobs
                        .slice(index)
                        .map((j) => `"${j}"`)
                        .join(" => ");
                }
                const deps = dependencyGraph.get(job);
                return deps ? visitJobs(deps, new Set(visited).add(job)) : null;
            }

            // missing dependencies
            const missing = new Set();
            for (const job of this.jobs) {
                const factory = this.factories.get(job);
                if (factory.ignoreMissingDeps) {
                    continue;
                }
                for (const dep of factory.deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            return {
                failed: [...this.failed],
                cycle: visitJobs(this.jobs),
                missing: [...missing],
                unloaded: [...this.jobs].filter((j) => !this.factories.get(j).ignoreMissingDeps),
            };
        }

        async checkAndReportErrors() {
            const { failed, cycle, missing, unloaded } = this.findErrors();
            if (!failed.length && !unloaded.length) {
                return;
            }

            function domReady(cb) {
                if (document.readyState === "complete") {
                    cb();
                } else {
                    document.addEventListener("DOMContentLoaded", cb);
                }
            }

            function list(heading, names) {
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

            domReady(() => {
                    const customJSUnloaded = unloaded.some((module) =>
                    module.includes("user_custom_javascript")
                );

                if (customJSUnloaded && (document.querySelector(".o_frontend_to_backend_edit_btn") || window.location.href.includes("/web/login"))) {
                    if (document.querySelector(".custom-js-unloaded-popup")) {
                        return; // Popup already displayed, do nothing
                    }

                    const overlay = document.createElement("div");
                    overlay.className = "custom-js-unloaded-overlay position-fixed top-0 start-0 w-100 h-100";
                    overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
                    overlay.style.zIndex = "10000";

                    const popup = document.createElement("div");
                    popup.className =
                        "custom-js-unloaded-popup position-fixed start-50 translate-middle bg-danger text-white p-3 rounded shadow";
                    popup.style.top = "40%";
                    popup.style.zIndex = "10001";
                    popup.style.border = "2px solid black";

                    const message = document.createElement("div");
                    message.textContent =
                        "Custom JavaScript code has been disabled. You may proceed, but some features may not work as expected.";
                    popup.appendChild(message);

                    const closeButton = document.createElement("button");
                    closeButton.className = "btn btn-light mt-2";
                    closeButton.textContent = "Close";
                    closeButton.onclick = () => {
                        overlay.remove();
                        popup.remove();
                    };
                    popup.appendChild(closeButton);

                    document.body.appendChild(overlay);
                    document.body.appendChild(popup);
                    return;
                }

                while (document.body.childNodes.length) {
                    document.body.childNodes[0].remove();
                }
                const container = document.createElement("div");
                container.className =
                    "o_module_error position-fixed w-100 h-100 d-flex align-items-center flex-column bg-white overflow-auto modal";
                container.style.zIndex = "10000";
                const alert = document.createElement("div");
                alert.className = "alert alert-danger o_error_detail fw-bold m-auto";
                container.appendChild(alert);
                alert.appendChild(
                    list(
                        "The following modules failed to load because of an error, you may find more information in the devtools console:",
                        failed
                    )
                );
                alert.appendChild(
                    list(
                        "The following modules could not be loaded because they form a dependency cycle:",
                        cycle && [cycle]
                    )
                );
                alert.appendChild(
                    list(
                        "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:",
                        missing
                    )
                );
                alert.appendChild(
                    list(
                        "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
                        unloaded
                    )
                );
                document.body.appendChild(container);
            });
        }
    }

    if (!globalThis.odoo) {
        globalThis.odoo = {};
    }
    const odoo = globalThis.odoo;
    if (odoo.debug && !new URLSearchParams(location.search).has("debug")) {
        // remove debug mode if not explicitely set in url
        odoo.debug = "";
    }

    const loader = new ModuleLoader();
    odoo.define = loader.define.bind(loader);

    odoo.loader = loader;
})();
