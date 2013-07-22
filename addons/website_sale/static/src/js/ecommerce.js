$(document).ready(function (){
    $('.oe_ecommerce').on('click', '.oe_product .btn-success,.oe_product .btn-primary, .oe_product .btn-inverse, .oe_product_detail .btn-success,.oe_product_detail .btn-primary, .oe_product_detail .btn-inverse', function (e) {
        var mycart = !!$('.oe_ecommerce .oe_mycart').size();
        var $button = $(e.currentTarget);
        var link = $button.hasClass('btn-inverse') ? '/shop/remove_cart' : '/shop/add_cart';
        var $add = $button.parent().find('.btn-success,.btn-primary');
        var $remove = $button.parent().find('.btn-inverse');

        $.get(link, {'product_id': $button.data('id')}, function (result) {
            var result = JSON.parse(result);
            var quantity = parseInt(result.quantity);
            $add.find('.oe_quantity').html(quantity);
            $add.toggleClass('btn-primary', !quantity).toggleClass('btn-success', !!quantity);
            $remove.toggleClass('oe_hidden', !quantity);
            if (mycart && !quantity) {
                $button.parents('.oe_product:first').remove()
            }
            $('.oe_ecommerce .oe_total').replaceWith(''+result.totalHTML);
        });
    });
});


openerp.website = function(instance) {

    instance.website.sale = {};
    instance.website.sale.Checkout = instance.web.Widget.extend({
        template: 'Website.sale.Checkout',
        events: {
            'click .oe_error_payment': 'error_payment',
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$('input[name="shipping_different"]').on('change', function (ev) {
                self.$('.oe_shipping').toggle();
            });
        },
        get_payment_image: function () {
            // model: portal.payment.acquirer => form_template
            // see Setting => Accounting => Bank & Cash => Configure payment acquiring methods
        },
        save: function () {
        },
        error_payment: function () {
            alert("error_payment");
        },
    });
};


$(document).ready(function () {
    if (!$('.oe_checkout').size())
        return;
    // Init headless webclient
    // TODO: Webclient research : use iframe embedding mode
    //       Meanwhile, let's HACK !!!
    var s = new openerp.init(['web', 'website']);
    s.web.WebClient.bind_hashchange = s.web.WebClient.show_common = s.web.blockUI = s.web.unblockUI = function() {};
    s.web.WebClient.include({ do_push_state: function() {} });
    var wc = new s.web.WebClient();
    wc.start();
    var instance = openerp.instances[wc.session.name];
    // Another hack since we have no callback when webclient has loaded modules.
    instance.web.qweb.add_template('/website_sale/static/src/xml/ecommerce.xml');

    var editor = new instance.website.sale.Checkout(instance.webclient);
    editor.appendTo($('.oe_checkout'));
});