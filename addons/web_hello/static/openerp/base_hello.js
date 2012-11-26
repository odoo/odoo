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

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

instance.web.Login = instance.web.Login.extend({
    start: function() {
        console.log('Hello there');
        return this._super.apply(this,arguments);
    }
});

};

// vim:et fdc=0 fdl=0:
