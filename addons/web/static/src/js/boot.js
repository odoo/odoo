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
        // openerp.sessions.sessionname.<module> using a closure
        sessions: {},
        /**
         * OpenERP instance constructor
         *
         * @param {Array} modules list of modules to initialize
         */
        init: function(modules) {
            var new_instance = {
                // links to the global openerp
                _openerp: openerp,
                // Only web will be loaded, the rest will be by loaded by
                // openerp.web.Connection on the first connection
                _modules_loaded: false,
                // this unique id will be replaced by hostname_databasename by
                // openerp.web.Connection on the first connection
                _session_id: "session" + session_counter++,
                web: {},
                web_mobile: {}
            };
            openerp.sessions[new_instance._session_id] = new_instance;
            modules = modules || ["web"];
            for(var i=0; i < modules.length; i++) {
                openerp[modules[i]](new_instance);
            }
            return new_instance;
        }
    };
})();

/*---------------------------------------------------------
 * OpenERP Web web module split
 *---------------------------------------------------------*/

/**
 * @namespace
 */
openerp.web = function(instance) {
    openerp.web.core(instance);
    if (openerp.web.dates) {
        openerp.web.dates(instance);
    }
    openerp.web.formats(instance);
    openerp.web.chrome(instance);
    openerp.web.data(instance);
    var files = ["views","search","list","form","list_editable","web_mobile","view_tree","data_export","data_import"];
    for(var i=0; i<files.length; i++) {
        if(openerp.web[files[i]]) {
            openerp.web[files[i]](instance);
        }
    }
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
