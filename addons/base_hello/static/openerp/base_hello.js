/*---------------------------------------------------------
 * OpenERP base_hello (Example module)
 *---------------------------------------------------------*/

openerp.base_hello = function(openerp) {

openerp.base_hello.HelloController = openerp.base.Controller.extend({
    init:function() {
        this._super.apply(this,arguments);
    },
    do_hello:function() {
        alert("hello");
    },
});

openerp.base.SearchView = openerp.base.SearchView.extend({
    init:function() {
        this._super.apply(this,arguments);
        this.hello = openerp.base_hello.HelloController();
        this.on_search.add(this.hello.do_hello);
    },
});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

}

// vim:et fdc=0 fdl=0:
