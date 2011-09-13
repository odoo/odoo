
openerp.web_process = function (openerp) {
var QWeb = openerp.web.qweb;
QWeb.add_template('/web_process/static/src/xml/web_process.xml');
openerp.web.SearchView = openerp.web.SearchView.extend({
    init: function(parent, element_id, dataset, view_id, defaults) {
        this._super(parent, element_id, dataset, view_id, defaults);
    },
    on_loaded: function(data) {
        var self = this;
        this._super(data);
        this.$element.find("#ProcessView").click(function() {
            self.on_click();
        });
    },
    on_click: function() {
        this.widget_parent.$element.replaceWith(QWeb.render("ProcessView"));
    },
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
