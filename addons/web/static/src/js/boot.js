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

    var jobs = {};
    var services = {};
    var jobs_deferred = {};
    var require = function (name) { return services[name]; };
    var timeDeferred;
    var masterDef = new $.Deferred();
    masterDef.__deferred__ = [];

    var commentRegExp = /(\/\*([\s\S]*?)\*\/|([^:]|^)\/\/(.*)$)/mg;
    var cjsRequireRegExp = /[^.]\s*require\s*\(\s*["']([^'"\s]+)["']\s*\)/g;

    var debug = ($.deparam($.param.querystring()).debug !== undefined);

    var odoo = window.odoo = window.odoo || {};
    _.extend(odoo, {
        testing: typeof QUnit === "object",
        debug: debug,
        subsets: [],

        __DEBUG__: {
            get_dependencies: function (name) {
                if (!jobs[name]) return [];
                if (!jobs[name].dependencies) {
                    var self = this;
                    var deps = [];
                    _.each(jobs[name].deps, function (dep) {
                        deps.push(dep);
                        deps = deps.concat(self.get_dependencies(dep));
                    });
                    jobs[name].dependencies = _.uniq(deps);
                }
                return jobs[name].dependencies;
            },
            get_dependents: function (name) {
                if (!jobs[name]) return [];
                if (!jobs[name].dependents) {
                    var self = this;
                    var deps = [];
                    _.each(jobs, function (job, key) {
                        if (job.deps.indexOf(name) !== -1) {
                            deps.push(key);
                            deps = deps.concat(self.get_dependencies(key));
                        }
                    });
                    jobs[name].dependents = _.uniq(deps);
                }
                return jobs[name].dependents;
            },
            get_waited_jobs: function () {
                return _.uniq(_.map(jobs, function (job, key) {return key;}));
            },
            get_missing_jobs: function () {
                var self = this;
                var waited = this.get_waited_jobs();
                var missing = [];
                _.each(waited, function (job) {
                    _.each(self.get_dependencies(job), function (job) {
                        if (!(job in self.services)) {
                            missing.push(job);
                        }
                    });
                });
                return _.filter(_.difference(_.uniq(missing), waited), function (job) {return !job.error;});
            },
            get_failed_jobs: function () {
                return _.filter(jobs, function (job, key) {return !!job.error;});
            },
            jobs: jobs,
            services: services,
        },
        deferred: masterDef,
        define: function () {
            var args = Array.prototype.slice.call(arguments);
            var name = typeof args[0] === 'string' ? args.shift() : _.uniqueId('__job');
            var deps = args[0] instanceof Array && args.shift();
            var factory = args.shift();
            var subset = args.shift();
            var _jobs_deferred, _require, _deferred, _services, _jobs;
            clearTimeout(timeDeferred);

            if (subset) {
                _jobs_deferred = subset.jobs_deferred;
                _require = subset.require;
                _services = subset.services;
                _jobs = subset.jobs;
            } else {
                _jobs_deferred = jobs_deferred;
                _require = require;
                _services = services;
                _jobs = jobs;
            }

            if (!deps) {
                deps = [];
                factory.toString()
                    .replace(commentRegExp, '')
                    .replace(cjsRequireRegExp, function (match, dep) {
                        deps.push(dep);
                    });
            }

            if (!subset && odoo.debug) {
                if (!(deps instanceof Array)) {
                    throw new Error ('Dependencies should be defined by an array', deps);
                }
                if (typeof factory !== 'function') {
                    throw new Error ('Factory should be defined by a function', factory);
                }
                if (typeof name !== 'string') {
                    throw new Error("Invalid name definition (should be a string", name);
                }
                if (_jobs[name] && _jobs[name].defined) {
                    throw new Error("Service " + name + " already defined");
                }
            }

            var def = _jobs_deferred[name] || (_jobs_deferred[name] = $.Deferred());
            _jobs[name] = {
                'defined': true,
                'name': name,
                'deps': deps,
                'factory': factory
            };

            // launch module when deps are ready

            if (subset) {
                deps = deps.map(function (dep) {
                    if (!_jobs_deferred[dep]) {
                        var job = subset.jobs[dep] || jobs[dep];
                        odoo.define(job.name, job.deps, job.factory, subset);
                    }
                    return _jobs_deferred[dep];
                });
            } else {
                deps = deps.map(function (dep) {
                    return _jobs_deferred[dep] || (_jobs_deferred[dep] = $.Deferred());
                });
            }

            $.when.apply($, deps).then(
                function () {
                    setTimeout(function process_job () {
                        try {
                            var job_exec = factory(_require);
                            if (job_exec && job_exec.then && job_exec.promise) {
                                job_exec.then(
                                    function (data) {
                                        _services[name] = data;
                                        def.resolve();
                                    },
                                    def.reject);
                            } else {
                                _services[name] = job_exec;
                                def.resolve();
                            }
                        } catch (e) {
                            console.error(e);
                            def.reject(_jobs[name].error = e);
                        }
                    });
                },
                def.reject);

            // Global deferred

            var masterDef = subset ? subset.deferred : odoo.deferred;
            masterDef.__deferred__.push(def);
            def.always(function () {
                clearTimeout(timeDeferred);
                timeDeferred = setTimeout(function () {
                    var waited = _.filter(_jobs_deferred, function (def) { return def.state() === 'pending';}).length;
                    if (masterDef.state() === "pending" && !waited) {
                        masterDef.resolve(_services);
                    }
                });
            });
        },
        subset: function (modules, subset, replace) {
            var masterDef = new $.Deferred();
            masterDef.__deferred__ = [];
            var options = subset ? Object(subset) : {
                "id": odoo.subsets.length,
                "jobs_deferred": {},
                "jobs": {},
                "replace": {},
                "services": {},
                "modules": [],
                "deferred": masterDef,
                "require": function require (name) { return options.services[name]; }
            };

            if (subset) {
                options.jobs_deferred = Object(options.jobs_deferred);
                options.jobs = Object(options.jobs);
                options.replace = Object(options.replace);
                options.services = Object(options.services);
                options.modules = Object(options.modules);
            }

            odoo.subsets.push(options);


            if (replace) {
                for (var k in replace) {
                    options.replace[k] = replace[k];
                }
            }

            var _jobs = Object(jobs);
            for (var k in options.replace) {
                _jobs[k] = options.replace[k];
            }

            for (var k in _jobs) {
                var job = _jobs[k];
                if (!(job.name in options.services) && (!modules || modules.indexOf(job.name) !== -1)) {
                    options.modules.push(job.name);
                    odoo.define(job.name, job.deps, job.factory, options);
                }
            }

            return options.deferred.then(function (subset_services) {
                // reset original services and prepare for extend subset
                if (odoo.debug) {
                    console.log("Use a subset's services ("+options.id+")",
                        "\nNeed: ", options.modules,
                        "\nUsed: ", _.pluck(options.jobs, 'name'));
                }
                subset_services.subset = options;
                return subset_services;
            });
        },
        log: function () {
            if (!_.keys(jobs).length || odoo.__DEBUG__.create_subset) {
                return;
            }
            if (!debug) {
                var errors = _.filter(jobs, function (job) {return job.error;}).map(function (job) {return job.name;});
                if (errors.length) {
                    console.error('Failed modules: ' + errors.join(","));
                }
            }

            var debug_jobs = {};
            var rejected = [];
            var rejected_linked = [];
            var job;
            var jobdep;

            _.each(jobs, function (value, key) {
                if (key in services) {
                    return;
                }
                debug_jobs[key] = job = {'name': key};
                var deps = odoo.__DEBUG__.get_dependents(key);
                if (deps.length) {
                    job.dependents = deps;
                }
                if (value.deps.length) {
                    job.dependencies = value.deps;
                }
                if (value.error) {
                    job.error = value.error;
                } else if (jobs_deferred[key].state() === 'rejected') {
                    job.rejected = true;
                    rejected.push(job.name);
                }

                var deps = odoo.__DEBUG__.get_dependencies( job.name );
                for (var i=0; i<deps.length; i++) {
                    if (job.name !== deps[i] && !(deps[i] in services) && (!jobs[deps[i]] || jobs[deps[i]].error)) {
                        if (!job.missing) {
                            job.missing = [];
                        }
                        job.missing.push(deps[i]);
                        if (job.rejected) {
                            rejected.splice(rejected.indexOf(deps[i]), 1);
                            delete job.rejected;
                        }
                    }
                }
            });
            var missing = odoo.__DEBUG__.get_missing_jobs();
            var failed = odoo.__DEBUG__.get_failed_jobs();
            var unloaded = _.filter(debug_jobs, function (job) { return !!job.missing; });

            var log = [(_.isEmpty(failed) ? (_.isEmpty(unloaded) ? 'info' : 'warning' ) : 'error') + ':', 'Some modules could not be started'];
            if (missing.length)             log.push('\nMissing dependencies:   ', missing);
            if (!_.isEmpty(failed))         log.push('\nFailed modules:         ', _.pluck(failed, 'name'));
            if (!_.isEmpty(rejected))       log.push('\nRejected modules:       ', rejected);
            if (!_.isEmpty(rejected_linked))log.push('\nRejected linked modules:', rejected_linked);
            if (!_.isEmpty(unloaded))       log.push('\nNon loaded modules:     ', _.pluck(unloaded, 'name'));
            if (odoo.debug && !_.isEmpty(debug_jobs)) log.push('\nDebug:                  ', debug_jobs);

            if ((odoo.debug || !_.isEmpty(failed) || !_.isEmpty(unloaded)) && log.length > 2) {
                console[_.isEmpty(unloaded) ? 'info' : 'error'].apply(console, log);
            }
        },
    });

    // automatically log errors
    $(function () {
        var last_check = 0;
        var checktime = setInterval(function () {
            if (odoo.deferred.state() === 'pending') {
                var pending = _.filter(jobs_deferred, function (def) { return def.state() === 'pending';}).length;
                if (pending !== last_check) {
                    last_check = pending;
                    return;
                }
            }
            clearInterval(checktime);
            odoo.log();
        }, 500);
    });

})();
