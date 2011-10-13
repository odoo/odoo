/*---------------------------------------------------------
 * EDI Web Interface for Invoice
 *---------------------------------------------------------*/
//

openerp.web.edi_invoice = function(openerp) {
var QWeb = new QWeb2.Engine();

openerp.web.edi_views.add('view_center_account_invoice' , 'openerp.web.EdiViewCenterInvoice');
openerp.web.EdiViewCenterInvoice = openerp.web.Class.extend({
    init: function(element, edi){
        var self = this;
        this.edi_document = eval(edi.document)
        this.$element = element;
        QWeb.add_template("/web_edi_invoice/static/src/xml/edi_invoice.xml");
        this.$_element = $('<div>')
            .appendTo(document.body)
            .delegate('#oe_edi_invoice_button_pay', 'click', {'edi': edi} , this.do_pay)
    },
    start: function() {
	},
    render: function(){
        template = "InvoiceEdiView";
        if (this.$current) {
            this.$current.remove();
        }
        this.$current = this.$_element.clone(true);
        this.$current.empty().append($(QWeb.render(template, {'invoices': this.edi_document})));
        this.$element.append(this.$current);
    },
    do_pay: function(e){
        $element = $(e.view.document.body)
        token = e.data.edi.token
        db = e.data.edi.db
        var current_url = $(location).attr('href')
        var pathName = current_url.substring(0, current_url.lastIndexOf('/') +1);

        if ($element.find('#oe_edi_invoice_rd_pay_paypal').attr('checked') == 'checked')
        {
            alert('Pay Invoice using Paypal service');
            
        }
        if ($element.find('#oe_edi_invoice_rd_pay_google_checkout').attr('checked') == 'checked')
        {
            alert('Pay Invoice using Google Checkout');
        }
        if ($element.find('#oe_edi_invoice_rd_pay_bank').attr('checked') == 'checked')
        {
            alert('Pay Invoice using Bankwire Trasnfer')
        }
    }
});

}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
