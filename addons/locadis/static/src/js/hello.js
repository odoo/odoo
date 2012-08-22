
openerp.locadis = function(instance){
    console.log('Hello World!:',instance);
    instance.point_of_sale.PosWidget = instance.point_of_sale.PosWidget.extend({
        init:function(parent,options){
            console.log('Tadaaam!',parent,options);
            this._super(parent,options);
        },
    });

    /* REMOVE PRODUCTS FROM FIRST LEVEL IN SELF CHECKOUT */
};
