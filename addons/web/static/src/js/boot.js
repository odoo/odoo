/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 */
(function() {
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
        _modules: ['web'],
        web_mobile: {},
        /**
         * OpenERP instance constructor
         *
         * @param {Array|String} modules list of modules to initialize
         */
        init: function(modules) {
            if (modules === null) {
                modules = [];
            }
            if (inited)
                throw new Error("OpenERP was already inited");
            inited = true;
            init_web_modules();
            for(var i=0; i < modules.length; i++) {
                if (modules[i] === "web")
                    continue;
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

    /*---------------------------------------------------------
     * OpenERP Web web module split
     *---------------------------------------------------------*/
    function init_web_modules() {
        var files = ["pyeval", "corelib","coresetup","dates","formats","chrome","data","views","search","list","form","list_editable","web_mobile","view_tree","data_export","data_import"];
        for(var i=0; i<files.length; i++) {
            var fct = openerp.web[files[i]];
            if(typeof(fct) === "function") {
                openerp.web[files[i]] = {};
                for (var k in fct) {
                    openerp.web[files[i]][k] = fct[k];
                }
                fct(openerp, openerp.web[files[i]]);
            }
        }
    }
})();

