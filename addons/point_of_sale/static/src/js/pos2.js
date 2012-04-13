openerp.point_of_sale = function(instance) {
    instance.point_of_sale = {};
    instance.point_of_sale.test = instance.web.Widget.extend({
        template: 'EmptyComponent',
        start: function() {
            var self = this;
            this.$element.addClass('openerp');
            return this.rpc('/pos/dispatch', {iface: 'light', status: 1}, function(result) {
                console.log(result);
            });
        },
    });
};
