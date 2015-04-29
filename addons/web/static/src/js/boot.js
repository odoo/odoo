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
                } while (changed && transitive)
                return deps;
            },
            get_dependents: function (name) {
                return _.pluck(_.where(job_deps, {from: name}), 'to');            
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
                for (var k=0; k<jobs.length; k++) {
                    var deps = odoo.__DEBUG__.get_dependencies( jobs[k].name );
                    for (var i=0; i<deps.length; i++) {
                        if (jobs[k].name !== deps[i] && !(deps[i] in services)) {
                            if (!jobs[k].missing) {
                                jobs[k].missing = [];
                            }
                            jobs[k].missing.push(deps[i]);
                        }
                    }
                }
                console.warn('Warning: some modules could not be started, most likely because of missing dependencies.', jobs);
            }
            // _.each(factories, function (value, key) {
            //     delete factories[key];
            // });
        },
        process_jobs: function (jobs, services) {
            var job, require;
            while (jobs.length && (job = _.find(jobs, is_ready))) {
                require = make_require(job);
                try {
                    services[job.name] = job.factory.call(null, require);
                } catch (e) {
                    console.error("Error: at least one error are found in module '"+job.name+"'", e);
                }
                jobs.splice(jobs.indexOf(job), 1);
            }
            return services;

            function is_ready (job) {
                return _.every(job.factory.deps, function (name) { return name in services; });
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
