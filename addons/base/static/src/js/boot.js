//---------------------------------------------------------
// OpenERP Web Boostrap
//---------------------------------------------------------

/**
 * @name openerp
 * @namespace openerp
 * @namespace window.openerp
 */
(function() {
    if (this.openerp)
        return;
    var session_counter = 0;

    /** @lends openerp */
    var openerp = this.openerp =  {
        /**
         * Debug flag turns on logging
         */
        debug: true,
        // element_ids registry linked to all controllers on the page
        // TODO rename to elements, or keep gtk naming?
        screen: {},
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
                screen: openerp.screen,
                sessions: openerp.sessions,
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

//---------------------------------------------------------
// OpenERP base module split
//---------------------------------------------------------

openerp.base = function(instance) {
    openerp.base.core(instance);
    openerp.base.dates(instance);
    openerp.base.chrome(instance);
    openerp.base.data(instance);
    if (openerp.base.views) {
        openerp.base.views(instance);
    }
    if (openerp.base.search) {
        openerp.base.search(instance);
    }
    if (openerp.base.list) {
        openerp.base.list(instance);
    }
    if (openerp.base. m2o) {
        openerp.base.m2o(instance);
    }
    if (openerp.base.form) {
        openerp.base.form(instance);
    }
    if (openerp.base.list && openerp.base.list.editable) {
        openerp.base.list.editable(instance);
    }
    if (openerp.web_mobile) {
        openerp.web_mobile(instance);
    }
    if (openerp.base.view_tree) {
        openerp.base.view_tree(instance);
    }
    if (openerp.base.data_export) {
        openerp.base.data_export(instance);
    }
    if (openerp.base.data_import){
        openerp.base.data_import(instance);
    }
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
