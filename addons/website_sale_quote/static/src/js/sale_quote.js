openerp.base_calendar = function(instance) {
var _t = instance.web._t;
var QWeb = instance.web.qweb;
instance.base_calendar = {}

    instance.sale_quote.quotation = instance.web.Widget.extend({

        init: function(parent, db, action, id, view, quotation) {
            this._super();
            this.db =  db;
            this.action =  action;
            this.id = id;
            this.view = view;
            this.quotation = quotation;
        },
        start: function() {
            var self = this;
            self.open_invitation_form(self.quotation);
        },
        open_quotation : function(quotation){
            alert('aaa');
            this.$el.html(QWeb.render('quotation_view', {'quotation': JSON.parse(quotation)}));
        },
    });

    instance.sale_quote.view = function (db, action, id, view, quotation) {
        instance.session.session_bind(instance.session.origin).done(function () {
            new instance.sale_quote.quotation(null,db,action,id,view,quotation).appendTo($("body").addClass('openerp'));
        });
    }
};
//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
