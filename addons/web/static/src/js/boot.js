/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 *
 * Each module can return a deferred. In that case, the module is marked as loaded
 * only when the deferred is resolved, and its value is equal to the resolved value.
 * The module can be rejected (unloaded). This will be logged in the console as info.
 *
 * logs: 
 *      Missing dependencies:
 *          These modules do not appear in the page. It is possible that the
 *          JavaScript file is not in the page or that the module name is wrong
 *      Failed modules:
 *          A javascript error is detected
 *      Rejected modules:
 *          The module returns a rejected deferred. It (and its dependent modules)
 *          is not loaded.
 *      Rejected linked modules:
 *          Modules who depend on a rejected module
 *      Non loaded modules:
 *          Modules who depend on a missing or a failed module
 *      Debug:
 *          Non loaded or failed module informations for debugging
 */

(function() {
    "use strict";

    var jobs = [];
    var factories = Object.create(null);
    var job_names = [];
    var job_deps = [];
    var job_deferred = [];

    var services = Object.create({
        qweb: new QWeb2.Engine(),
        $: $,
        _: _,
    });

    var commentRegExp = /(\/\*([\s\S]*?)\*\/|([^:]|^)\/\/(.*)$)/mg;
    var cjsRequireRegExp = /[^.]\s*require\s*\(\s*["']([^'"\s]+)["']\s*\)/g;

    var debug = ($.deparam($.param.querystring()).debug !== undefined);

    var odoo = window.odoo = {
        testing: typeof QUnit === "object",
        debug: debug,
        remaining_jobs: jobs,

        __DEBUG__: {
            get_dependencies: function (name, transitive) {
                var deps = name instanceof Array ? name: [name],
                    changed;
                do {
                    changed = false;
                    _.each(job_deps, function (dep) {
                        if (_.contains(deps, dep.to) && (!_.contains(deps, dep.from))) {
                            deps.push(dep.from);
                            changed = true;
                        }
                    });
                } while (changed && transitive);
                return deps;
            },
            get_dependents: function (name) {
                return _.pluck(_.where(job_deps, {from: name}), 'to');
            },
            get_waited_jobs: function () {
                return _.uniq(_.map(jobs, function(job) {return job.name;}));
            },
            get_missing_jobs: function () {
                var self = this;
                var waited = this.get_waited_jobs();
                var missing = [];
                _.each(waited, function(job) {
                    _.each(self.get_dependencies(job), function(job) {
                        if (!(job in self.services)) {
                            missing.push(job);
                        }
                    });
                });
                return _.filter(_.difference(_.uniq(missing), waited), function (job) {return !job.error;});
            },
            get_failed_jobs: function () {
                return _.filter(jobs, function (job) {return !!job.error;});
            },
            factories: factories,
            services: services,
        },
        define: function () {
            var args = Array.prototype.slice.call(arguments);
            var name = typeof args[0] === 'string' ? args.shift() : _.uniqueId('__job');
            var factory = args[args.length - 1];
            var deps;
            if (args[0] instanceof Array) {
                deps = args[0];
            } else {
                deps = [];
                factory.toString()
                    .replace(commentRegExp, '')
                    .replace(cjsRequireRegExp, function (match, dep) {
                        deps.push(dep);
                    });
            }

            if (odoo.debug) {
                if (!(deps instanceof Array)) {
                    throw new Error ('Dependencies should be defined by an array', deps);
                }
                if (typeof factory !== 'function') {
                    throw new Error ('Factory should be defined by a function', factory);
                }
                if (typeof name !== 'string') {
                    throw new Error("Invalid name definition (should be a string", name);
                }
                if (name in factories) {
                    throw new Error("Service " + name + " already defined");
                }
            }

            factory.deps = deps;
            factories[name] = factory;

            jobs.push({
                name: name,
                factory: factory,
                deps: deps,
            });

            job_names.push(name);
            _.each(deps, function (dep) {
                job_deps.push({from:dep, to:name});
            });

            this.process_jobs(jobs, services);
        },
        log: function () {
            if (jobs.length) {
                var debug_jobs = {};
                var rejected = [];
                var rejected_linked = [];
                var job;
                var jobdep;

                for (var k=0; k<jobs.length; k++) {
                    debug_jobs[jobs[k].name] = job = {
                        dependencies: jobs[k].deps,
                        dependents: odoo.__DEBUG__.get_dependents(jobs[k].name),
                        name: jobs[k].name
                    };
                    if (jobs[k].error) {
                        job.error = jobs[k].error;
                    }
                    if (jobs[k].rejected) {
                        job.rejected = jobs[k].rejected;
                        rejected.push(job.name);
                    }
                    var deps = odoo.__DEBUG__.get_dependencies( job.name );
                    for (var i=0; i<deps.length; i++) {
                        if (job.name !== deps[i] && !(deps[i] in services)) {
                            jobdep = debug_jobs[deps[i]] || (deps[i] in factories && _.find(jobs, function (job) { return job.name === deps[i];}));
                            if (jobdep && jobdep.rejected) {
                                if (!job.rejected) {
                                    job.rejected = [];
                                    rejected_linked.push(job.name);
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
                var missing = odoo.__DEBUG__.get_missing_jobs();
                var failed = odoo.__DEBUG__.get_failed_jobs();
                var unloaded = _.filter(debug_jobs, function (job) { return job.missing; });

                var log = [(_.isEmpty(failed) ? (_.isEmpty(unloaded) ? 'info' : 'warning' ) : 'error') + ':', 'Some modules could not be started'];
                if (missing.length)             log.push('\nMissing dependencies:   ', missing);
                if (!_.isEmpty(failed))         log.push('\nFailed modules:         ', _.pluck(failed, 'name'));
                if (!_.isEmpty(rejected))       log.push('\nRejected modules:       ', rejected);
                if (!_.isEmpty(rejected_linked))log.push('\nRejected linked modules:', rejected_linked);
                if (!_.isEmpty(unloaded))       log.push('\nNon loaded modules:     ', _.pluck(unloaded, 'name'));
                if (odoo.debug && !_.isEmpty(debug_jobs)) log.push('\nDebug:                  ', debug_jobs);

                if (odoo.debug || !_.isEmpty(failed) || !_.isEmpty(unloaded)) {
                    console[_.isEmpty(unloaded) ? 'info' : 'error'].apply(console, log);
                }
            }
        },
        process_jobs: function (jobs, services) {
            var job;
            var require;
            var time;

            function process_job (job) {
                var require = make_require(job);
                try {
                    var def = $.Deferred();
                    $.when(job.factory.call(null, require)).then(
                        function (data) {
                            services[job.name] = data;
                            clearTimeout(time);
                            time = _.defer(odoo.process_jobs, jobs, services);
                            def.resolve();
                        }, function (e) {
                            job.rejected = e || true;
                            jobs.push(job);
                            def.resolve();
                        });
                    jobs.splice(jobs.indexOf(job), 1);
                    job_deferred.push(def);
                } catch (e) {
                    job.error = e;
                }
            }

            function is_ready (job) {
                return !job.error && !job.rejected && _.every(job.factory.deps, function (name) { return name in services; });
            }

            function make_require (job) {
                var deps = _.pick(services, job.deps);

                function require (name) {
                    if (!(name in deps)) {
                        console.error('Undefined dependency: ', name);
                    } else {
                        require.__require_calls++;
                    }
                    return deps[name];
                }

                require.__require_calls = 0;
                return require;
            }

            while (jobs.length && (job = _.find(jobs, is_ready))) {
                process_job(job);
            }

            return services;
        }
    };

    // automatically log errors detected when loading modules
    var log_when_loaded = function () {
        _.delay(function () {
            var len = job_deferred.length;
            $.when.apply($, job_deferred).then(function () {
                if (len === job_deferred.length) {
                    odoo.log();
                } else {
                    log_when_loaded();
                }
            });
        }, 4000);
    };
    $(log_when_loaded);

})();
