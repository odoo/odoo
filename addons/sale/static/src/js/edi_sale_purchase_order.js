openerp.web.edi_sale_purchase_order = function(openerp) {
var QWeb = new QWeb2.Engine();

openerp.web.edi_views.add('view_center_sale_order' , 'openerp.web.EdiViewCenterSalePurchase');
openerp.web.edi_views.add('view_center_purchase_order' , 'openerp.web.EdiViewCenterSalePurchase');
openerp.web.EdiViewCenterSalePurchase = openerp.web.Class.extend({
    init: function(element, edi){
        var self = this;
        this.edi_document = eval(edi.document)
        this.$element = element;
        QWeb.add_template("/web_edi_sale_purchase/static/src/xml/edi_sale_purchase_order.xml");
        
    },
    start: function() {
	},
    render: function(){
        template = "OrderEdiView";
        this.$element.append($(QWeb.render(template, {'orders': this.edi_document})));
    },
    
});
}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
