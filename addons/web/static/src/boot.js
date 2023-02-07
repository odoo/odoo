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
            const mods = this.modules;
            // const mod = mods.get(name);
            const require = (name) => mods.get(name);
            this.jobs.delete(name);
            try {
                const value = this.factories.get(name).fn(require);
                if (value instanceof Promise) {
                    console.log(name);
                }
                // if (mod.value instanceof Promise) {
                //     debugger
                // }
                this.modules.set(name, value);
            } catch (error) {
                this.failed.add(name);
                console.error(`Error while loading "${name}":\n`, error);
            }
        }

        // async reportErrors() {
        //     const failed = this.failed;
        //     const unloaded = this.pending;

        //     await owl.whenReady(); // we need the DOM to be ready
        //     console.log('FAIL');
        //     const list = (heading, nameSet) => {
        //         const frag = document.createDocumentFragment();
        //         if (!nameSet.size) {
        //             return frag;
        //         }
        //         frag.textContent = heading;
        //         const ul = document.createElement("ul");
        //         for (const el of nameSet) {
        //             const li = document.createElement("li");
        //             li.textContent = el;
        //             ul.append(li);
        //         }
        //         frag.appendChild(ul);
        //         return frag;
        //     };
        //     // Empty body
        //     while (document.body.childNodes.length) {
        //         document.body.childNodes[0].remove();
        //     }
        //     const container = document.createElement("div");
        //     container.className =
        //         "position-fixed w-100 h-100 d-flex align-items-center flex-column bg-white overflow-auto modal";
        //     container.style.zIndex = "10000";
        //     const alert = document.createElement("div");
        //     alert.className = "alert alert-danger o_error_detail fw-bold m-auto";
        //     container.appendChild(alert);
        //     alert.appendChild(
        //         list(
        //             "The following modules failed to load because of an error, you may find more information in the devtools console:",
        //             this.failed
        //         )
        //     );
        //     alert.appendChild(
        //         list(
        //             "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
        //             this.pending
        //         )
        //     );
        //     document.body.appendChild(container);
        // }
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

    odoo.findMissing = function (name, missing = new Set(), indent = 0) {
        const log = (str) => {
            console.log(str.padStart(str.length + indent, " "));
        };
        log(`checking ${name}`);
        for (const dep of loader.modules.get(name).deps) {
            if (!loader.modules.has(dep)) {
                log(`${name} -> ${dep} is missing`);
                missing.add(dep);
            } else if (!loader.ready.has(dep)) {
                log(`${name} -> ${dep} is present, but not loaded.`);
                odoo.findMissing(dep, missing, indent + 4);
            } else {
                log(`${name} -> ${dep} is present and loaded`);
            }
        }
        return missing;
    };

    odoo.ready = async function (str) {
        return Promise.resolve();
        // function match(name) {
        //     return typeof str === "string" ? name === str : str.test(name);
        // }
        // const proms = [];
        // for (const [name, ] of loader.modules.entries()) {
        //     if (match(mod.name)) {
        //         proms.push(mod.promise);
        //     }
        // }
        // await Promise.all(proms);
        // return proms.length;
    };

    odoo.runtimeImport = function (moduleName) {
        if (!loader.ready.has(moduleName)) {
            throw new Error(`Service "${moduleName} is not defined or isn't finished loading."`);
        }
        return loader.modules.get(moduleName).value;
    };
})();
