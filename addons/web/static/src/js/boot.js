/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 */
(function() {
    if (this.openerp)
        return;
    var session_counter = 0;

    var openerp = this.openerp =  {
        // Per session namespace
        // openerp.<module> will map to
        // openerp.instances.sessionname.<module> using a closure
        instances: {},
        /**
         * OpenERP instance constructor
         *
         * @param {Array} modules list of modules to initialize
         */
        init: function(modules) {
            // By default only web will be loaded, the rest will be by loaded
            // by openerp.web.Session on the first session_authenticate
            modules = _.union(['web'], modules || []);
            var new_instance = {
                // links to the global openerp
                _openerp: openerp,
                // this unique id will be replaced by hostname_databasename by
                // openerp.web.Session on the first connection
                _session_id: "instance" + session_counter++,
                _modules: modules,
                web: {},
                web_mobile: {}
            };
            openerp.instances[new_instance._session_id] = new_instance;
            for(var i=0; i < modules.length; i++) {
                new_instance[modules[i]] = {};
                if (openerp[modules[i]]) {
                    openerp[modules[i]](new_instance,new_instance[modules[i]]);
                }
            }
            return new_instance;
        }
    };
})();

/*---------------------------------------------------------
 * OpenERP Web web module split
 *---------------------------------------------------------*/
openerp.web = function(session) {
    var files = ["corelib","coresetup","dates","formats","chrome","data","views","search","list","form","list_editable","web_mobile","view_tree","data_export","data_import"];
    for(var i=0; i<files.length; i++) {
        if(openerp.web[files[i]]) {
            openerp.web[files[i]](session);
        }
    }
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
