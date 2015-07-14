/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 */

(function() {
    "use strict";

    var jobs = [];
    var factories = Object.create(null);
    var job_names = [];
    var job_deps = [];

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
        init: function () {
            odoo.__DEBUG__.remaining_jobs = jobs;
            odoo.__DEBUG__.web_client = services['web.web_client'];

            if (jobs.length) {
                var debug_jobs = {}, job;

                for (var k=0; k<jobs.length; k++) {
                    debug_jobs[jobs[k].name] = job = {
                        dependencies: jobs[k].deps,
                        dependents: odoo.__DEBUG__.get_dependents(jobs[k].name),
                        name: jobs[k].name
                    };
                    if (jobs[k].error) {
                        job.error = jobs[k].error;
                    }
                    var deps = odoo.__DEBUG__.get_dependencies( job.name );
                    for (var i=0; i<deps.length; i++) {
                        if (job.name !== deps[i] && !(deps[i] in services)) {
                            if (!job.missing) {
                                job.missing = [];
                            }
                            job.missing.push(deps[i]);
                        }
                    }
                }
                var missing = odoo.__DEBUG__.get_missing_jobs();
                var failed = odoo.__DEBUG__.get_failed_jobs();
                console.error('Warning: Some modules could not be started !'+
                    '\nMissing dependencies: ', !missing.length ? null : missing,
                    '\nFailed modules:       ', _.isEmpty(failed) ? null : _.map(failed, function (job) {return job.name;}),
                    '\nUnloaded modules:     ', _.isEmpty(debug_jobs) ? null : debug_jobs);
            }
        },
        process_jobs: function (jobs, services) {
            var job, require;
            while (jobs.length && (job = _.find(jobs, is_ready))) {
                require = make_require(job);
                try {
                    services[job.name] = job.factory.call(null, require);
                    jobs.splice(jobs.indexOf(job), 1);
                } catch (e) {
                    job.error = e;
                }
            }
            return services;

            function is_ready (job) {
                return !job.error && _.every(job.factory.deps, function (name) { return name in services; });
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
        }
    };

})();
