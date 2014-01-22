/*---------------------------------------------------------
 * OpenERP base_hello (Example module)
 *---------------------------------------------------------*/

openerp.web_hello = function(instance) {

instance.web.SearchView = instance.web.SearchView.extend({
    init:function() {
        this._super.apply(this,arguments);
        this.on('search_data', this, function(){console.log('hello');});
    }
});

};

// vim:et fdc=0 fdl=0:
