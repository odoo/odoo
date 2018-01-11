/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 */
(function() {
    // copy everything in the openerp namespace to openerp.web
    openerp.web = _.clone(openerp);

    var inited = false;

    _.extend(openerp, {
        // Per session namespace
        // openerp.<module> will map to
        // openerp.instances.sessionname.<module> using a closure
        instances: {instance0: openerp},
        // links to the global openerp
        _openerp: openerp,
        // this unique id will be replaced by hostname_databasename by
        // openerp.web.Session on the first connection
        _session_id: "instance0",
        _modules: openerp._modules || ['web'],
        web_mobile: {},
        /**
         * OpenERP instance constructor
         *
         * @param {Array|String} modules list of modules to initialize
         */
        init: function(modules) {
            if (modules === undefined) {
                modules = openerp._modules;
            }
            modules = _.without(modules, "web");
            if (inited)
                throw new Error("OpenERP was already inited");
            inited = true;
            for(var i=0; i < modules.length; i++) {
                var fct = openerp[modules[i]];
                if (typeof(fct) === "function") {
                    openerp[modules[i]] = {};
                    for (var k in fct) {
                        openerp[modules[i]][k] = fct[k];
                    }
                    fct(openerp, openerp[modules[i]]);
                }
            }
            openerp._modules = ['web'].concat(modules);
            return openerp;
        }
    });
})();

