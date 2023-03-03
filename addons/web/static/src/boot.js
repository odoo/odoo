/**
 *------------------------------------------------------------------------------
 * Odoo Web Boostrap Code
 *------------------------------------------------------------------------------
 */
(function () {
    "use strict";

    const commentRegExp = /(\/\*([\s\S]*?)\*\/|([^:]|^)\/\/(.*)$)/gm;
    const cjsRequireRegExp = /[^.]\s*require\s*\(\s*["']([^'"\s]+)["']\s*\)/g;

    class ModuleLoader {
        autoStart = true;

        /** @type {Map<string,{fn: Function, deps: string[]}} mapping name => deps/fn */
        factories = new Map();

        /** @type {Set<string>} names of modules waiting to be started */
        jobs = new Set();
        /** @type {Set<string>} names of failed modules */
        failed = new Set();

        /** @type {Map<string,any} mapping name => value */
        modules = new Map();

        /**
         * @param {string} name
         * @param {string[]|Function} arg1
         * @param {Function|undefined} arg2
         */
        define(name, arg1, arg2) {
            let deps = arg1;
            let factory = arg2;
            if (!Array.isArray(arg1)) {
                // odoo.define is called without explicit dependencies. this is
                // deprecated and support for this should be removed in the future
                factory = arg1;
                deps = [];
                factory
                    .toString()
                    .replace(commentRegExp, "")
                    .replace(cjsRequireRegExp, (match, dep) => deps.push(dep));
            }
            if (typeof name !== "string") {
                throw new Error(`Invalid name definition: ${name} (should be a string)"`);
            }
            if (!(deps instanceof Array)) {
                throw new Error(`Dependencies should be defined by an array: ${deps}`);
            }
            if (typeof factory !== "function") {
                throw new Error("Factory should be defined by a function", factory);
            }
            if (this.factories.has(name)) {
                throw new Error("Module " + name + " already defined");
            }
            this.factories.set(name, { deps, fn: factory });

            if (this.autoStart) {
                this.addJob(name);
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
            try {
                const value = this.factories.get(name).fn(require);
                if (value instanceof Promise) {
                    console.log(name);
                }
                this.modules.set(name, value);
            } catch (error) {
                this.failed.add(name);
                console.error(`Error while loading "${name}":\n`, error);
            }
        }

        findErrors() {
            // cycle
            const dependencyGraph = new Map();
            for (const job of this.jobs) {
                dependencyGraph.set(job, this.factories.get(job).deps);
            }
            // cycle detection
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
                for (const dep of this.factories.get(job).deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            return {
                failed: [...this.failed],
                cycle: visitJobs(this.jobs),
                missing: [...missing],
                unloaded: [...this.jobs],
            };
        }

        validate() {
            if (!this.failed.size && !this.jobs.size) {
                return;
            }
            const errors = this.findErrors();
            throw new Error("boom" + errors);
        }

        async checkAndReportErrors() {
            if (!this.failed.size && !this.jobs.size) {
                return;
            }
            const { failed, cycle, missing, unloaded } = this.findErrors();

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
                // Empty body
                while (document.body.childNodes.length) {
                    document.body.childNodes[0].remove();
                }
                const container = document.createElement("div");
                container.className =
                    "position-fixed w-100 h-100 d-flex align-items-center flex-column bg-white overflow-auto modal";
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

    const loader = new ModuleLoader();
    odoo.define = loader.define.bind(loader);

    // debug
    odoo.__DEBUG__ = {};
    odoo.loader = loader;

    odoo.ready = async function (str) {
        return Promise.resolve();
    };

    odoo.runtimeImport = function (moduleName) {
        if (!loader.modules.has(moduleName)) {
            throw new Error(`Service "${moduleName} is not defined or isn't finished loading."`);
        }
        return loader.modules.get(moduleName);
    };

})();
