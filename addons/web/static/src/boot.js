/**
 *------------------------------------------------------------------------------
 * Odoo Web Boostrap Code
 *------------------------------------------------------------------------------
 *
 * Each module can return a promise. In that case, the module is marked as loaded
 * only when the promise is resolved, and its value is equal to the resolved value.
 * The module can be rejected (unloaded). This will be logged in the console as info.
 *
 * logs:
 *      Missing dependencies:
 *          These modules do not appear in the page. It is possible that the
 *          JavaScript file is not in the page or that the module name is wrong
 *      Failed modules:
 *          A javascript error is detected
 *      Rejected modules:
 *          The module returns a rejected promise. It (and its dependent modules)
 *          is not loaded.
 *      Rejected linked modules:
 *          Modules who depend on a rejected module
 *      Non loaded modules:
 *          Modules who depend on a missing or a failed module
 *      Debug:
 *          Non loaded or failed module informations for debugging
 */
(function () {
    "use strict";

    var jobUID = Date.now();

    var jobs = [];
    var factories = Object.create(null);
    var jobDeps = [];
    var jobPromises = [];

    var services = Object.create({});

    var commentRegExp = /(\/\*([\s\S]*?)\*\/|([^:]|^)\/\/(.*)$)/gm;
    var cjsRequireRegExp = /[^.]\s*require\s*\(\s*["']([^'"\s]+)["']\s*\)/g;
    if (!globalThis.odoo) {
        globalThis.odoo = {};
    }
    var odoo = globalThis.odoo;
    var debug = odoo.debug;

    var didLogInfoResolve;
    var didLogInfoPromise = new Promise(function (resolve) {
        didLogInfoResolve = resolve;
    });

    odoo.remainingJobs = jobs;
    odoo.__DEBUG__ = {
        didLogInfo: didLogInfoPromise,
        getDependencies: function (name, transitive) {
            var deps = name instanceof Array ? name : [name];
            var changed;
            do {
                changed = false;
                jobDeps.forEach(function (dep) {
                    if (deps.indexOf(dep.to) >= 0 && deps.indexOf(dep.from) < 0) {
                        deps.push(dep.from);
                        changed = true;
                    }
                });
            } while (changed && transitive);
            return deps;
        },
        getDependents: function (name) {
            return jobDeps
                .filter(function (dep) {
                    return dep.from === name;
                })
                .map(function (dep) {
                    return dep.to;
                });
        },
        getWaitedJobs: function () {
            return jobs
                .map(function (job) {
                    return job.name;
                })
                .filter(function (item, index, self) {
                    // uniq
                    return self.indexOf(item) === index;
                });
        },
        getMissingJobs: function () {
            var self = this;
            var waited = this.getWaitedJobs();
            var missing = [];
            waited.forEach(function (job) {
                self.getDependencies(job).forEach(function (job) {
                    if (!(job in self.services)) {
                        missing.push(job);
                    }
                });
            });
            return missing
                .filter(function (item, index, self) {
                    return self.indexOf(item) === index;
                })
                .filter(function (item) {
                    return waited.indexOf(item) < 0;
                })
                .filter(function (job) {
                    return !job.error;
                });
        },
        getFailedJobs: function () {
            return jobs.filter(function (job) {
                return !!job.error;
            });
        },
        processJobs: function () {
            var job;

            function processJob(job) {
                var require = makeRequire(job);

                var jobExec;
                function onError(e) {
                    job.error = e;
                    console.error(`Error while loading ${job.name}: ${e.message}`, e);
                }
                var def = new Promise(function (resolve) {
                    try {
                        jobExec = job.factory.call(null, require);
                        jobs.splice(jobs.indexOf(job), 1);
                    } catch (e) {
                        onError(e);
                    }
                    if (!job.error) {
                        Promise.resolve(jobExec)
                            .then(function (data) {
                                services[job.name] = data;
                                resolve();
                                odoo.__DEBUG__.processJobs();
                            })
                            .guardedCatch(function (e) {
                                job.rejected = e || true;
                                jobs.push(job);
                            })
                            .catch(function (e) {
                                if (e instanceof Error) {
                                    onError(e);
                                }
                                resolve();
                            });
                    } else {
                        resolve();
                    }
                });
                jobPromises.push(def);
                def.then(job.resolve);
            }

            function isReady(job) {
                return (
                    !job.error &&
                    !job.rejected &&
                    job.factory.deps.every(function (name) {
                        return name in services;
                    })
                );
            }

            function makeRequire(job) {
                var deps = {};
                Object.keys(services)
                    .filter(function (item) {
                        return job.deps.indexOf(item) >= 0;
                    })
                    .forEach(function (key) {
                        deps[key] = services[key];
                    });

                return function require(name) {
                    if (!(name in deps)) {
                        console.error("Undefined dependency: ", name);
                    }
                    return deps[name];
                };
            }

            while (jobs.length) {
                job = undefined;
                for (var i = 0; i < jobs.length; i++) {
                    if (isReady(jobs[i])) {
                        job = jobs[i];
                        break;
                    }
                }
                if (!job) {
                    break;
                }
                processJob(job);
            }

            return services;
        },
        factories: factories,
        services: services,
    };
    odoo.define = function () {
        var args = Array.prototype.slice.call(arguments);
        var name = typeof args[0] === "string" ? args.shift() : "__odoo_job" + jobUID++;
        var factory = args[args.length - 1];
        var deps;
        if (args[0] instanceof Array) {
            deps = args[0];
        } else {
            deps = [];
            factory
                .toString()
                .replace(commentRegExp, "")
                .replace(cjsRequireRegExp, function (match, dep) {
                    deps.push(dep);
                });
        }

        if (!(deps instanceof Array)) {
            throw new Error("Dependencies should be defined by an array", deps);
        }
        if (typeof factory !== "function") {
            throw new Error("Factory should be defined by a function", factory);
        }
        if (typeof name !== "string") {
            throw new Error("Invalid name definition (should be a string", name);
        }
        if (name in factories) {
            throw new Error("Service " + name + " already defined");
        }

        factory.deps = deps;
        factories[name] = factory;

        let promiseResolve;
        const promise = new Promise(resolve => {promiseResolve = resolve;});
        jobs.push({
            name: name,
            factory: factory,
            deps: deps,
            resolve: promiseResolve,
            promise: promise,
        });

        deps.forEach(function (dep) {
            jobDeps.push({ from: dep, to: name });
        });

        odoo.__DEBUG__.processJobs();
    };
    odoo.log = function () {
        var missing = [];
        var failed = [];
        var cycle = null;

        if (jobs.length) {
            var debugJobs = {};
            var rejected = [];
            var rejectedLinked = [];
            var job;
            var jobdep;

            for (var k = 0; k < jobs.length; k++) {
                debugJobs[jobs[k].name] = job = {
                    dependencies: jobs[k].deps,
                    dependents: odoo.__DEBUG__.getDependents(jobs[k].name),
                    name: jobs[k].name,
                };
                if (jobs[k].error) {
                    job.error = jobs[k].error;
                }
                if (jobs[k].rejected) {
                    job.rejected = jobs[k].rejected;
                    rejected.push(job.name);
                }
                var deps = odoo.__DEBUG__.getDependencies(job.name);
                for (var i = 0; i < deps.length; i++) {
                    if (job.name !== deps[i] && !(deps[i] in services)) {
                        jobdep = debugJobs[deps[i]];
                        if (!jobdep && deps[i] in factories) {
                            for (var j = 0; j < jobs.length; j++) {
                                if (jobs[j].name === deps[i]) {
                                    jobdep = jobs[j];
                                    break;
                                }
                            }
                        }
                        if (jobdep && jobdep.rejected) {
                            if (!job.rejected) {
                                job.rejected = [];
                                rejectedLinked.push(job.name);
                            }
                            job.rejected.push(deps[i]);
                        } else {
                            if (!job.missing) {
                                job.missing = [];
                            }
                            job.missing.push(deps[i]);
                        }
                    }
                }
            }
            missing = odoo.__DEBUG__.getMissingJobs();
            failed = odoo.__DEBUG__.getFailedJobs();
            var unloaded = Object.keys(debugJobs) // Object.values is not supported
                .map(function (key) {
                    return debugJobs[key];
                })
                .filter(function (job) {
                    return job.missing;
                });

            if (debug || failed.length || unloaded.length) {
                var log = globalThis.console[
                    !failed.length || !unloaded.length ? "info" : "error"
                ].bind(globalThis.console);
                log(
                    (failed.length ? "error" : unloaded.length ? "warning" : "info") +
                        ": Some modules could not be started"
                );
                if (missing.length) {
                    log("Missing dependencies:    ", missing);
                }
                if (failed.length) {
                    log(
                        "Failed modules:          ",
                        failed.map(function (fail) {
                            return fail.name;
                        })
                    );
                }
                if (rejected.length) {
                    log("Rejected modules:        ", rejected);
                }
                if (rejectedLinked.length) {
                    log("Rejected linked modules: ", rejectedLinked);
                }
                if (unloaded.length) {
                    cycle = findCycle(unloaded);
                    if (cycle) {
                        console.error("Cyclic dependencies: " + cycle);
                    }
                    log(
                        "Non loaded modules:      ",
                        unloaded.map(function (unload) {
                            return unload.name;
                        })
                    );
                }
                if (debug && Object.keys(debugJobs).length) {
                    log("Debug:                   ", debugJobs);
                }
            }
        }
        odoo.__DEBUG__.jsModules = {
            missing: missing,
            failed: failed.map((mod) => mod.name),
            unloaded: unloaded ? unloaded.map((mod) => mod.name) : [],
            cycle,
        };
        didLogInfoResolve(true);
    };
    /**
     * Returns a resolved promise when the targeted services are loaded.
     * If no service is found the promise is used directly.
     *
     * @param {string|RegExp} serviceName name of the service to expect
     *      or regular expression matching the service.
     * @returns {Promise<number>} resolved when the services ares
     *      loaded. The value is equal to the number of services found.
     */
    odoo.ready = async function (serviceName) {
        function match (name) {
            return typeof serviceName === 'string' ? name === serviceName : serviceName.test(name);
        }
        await Promise.all(jobs.filter(job => match(job.name)).map(job => job.promise));
        return Object.keys(factories).filter(match).length;
    };

    // Automatically log errors detected when loading modules
    globalThis.addEventListener("load", function logWhenLoaded() {
        const len = jobPromises.length;
        Promise.all(jobPromises).then(function () {
            if (len === jobPromises.length) {
                odoo.log();
            } else {
                logWhenLoaded();
            }
        });
    });

    /**
     * Visit the list of jobs, and return the first found cycle, if any
     *
     * @param {any[]} jobs
     * @returns {null | string} either a string describing a cycle, or null
     */
    function findCycle(jobs) {
        // build dependency graph
        const dependencyGraph = new Map();
        for (const job of jobs) {
            dependencyGraph.set(job.name, job.dependencies);
        }

        // helpers
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

        // visit each root to find cycles
        return visitJobs(jobs.map((j) => j.name));
    }
})();
