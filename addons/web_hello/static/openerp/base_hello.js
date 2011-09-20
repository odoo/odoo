/*---------------------------------------------------------
 * OpenERP base_hello (Example module)
 *---------------------------------------------------------*/

openerp.web_hello = function(openerp) {

openerp.web.SearchView = openerp.web.SearchView.extend({
    init:function() {
        this._super.apply(this,arguments);
        this.on_search.add(function(){console.log('hello');});
    }
});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

openerp.web.Login = openerp.web.Login.extend({
    start: function() {
        console.log('Hello there');
        this._super.apply(this,arguments);
    }
});

};

// vim:et fdc=0 fdl=0:
