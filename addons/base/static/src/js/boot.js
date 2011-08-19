/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 * @namespace window.openerp
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
         * @param {Boolean} skip_init if true, skips the built-in initialization
         */
        init: function(skip_init) {
            var new_instance = {
                // links to the global openerp
                _openerp: openerp,
                // Only base will be loaded, the rest will be by loaded by
                // openerp.base.Connection on the first connection
                _modules_loaded: false,
                // this unique id will be replaced by hostname_databasename by
                // openerp.base.Connection on the first connection
                _session_id: "session" + session_counter++,
                base: {},
                web_mobile: {}
            };
            openerp.sessions[new_instance._session_id] = new_instance;
            if (!skip_init){
                openerp.base(new_instance);
            }
            return new_instance;
        }
    };
})();

/*---------------------------------------------------------
 * OpenERP Web base module split
 *---------------------------------------------------------*/

openerp.base = function(instance) {
    openerp.base.core(instance);
    openerp.base.formats(instance);
    openerp.base.chrome(instance);
    openerp.base.data(instance);
    files = ["views","search","list","form","list_editable","web_mobile","view_tree","data_export"];
    for(i=0; i<files.length; i++) {
        if(openerp.base[files[i]]) {
            openerp.base[files[i]](instance);
        }
    }
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
