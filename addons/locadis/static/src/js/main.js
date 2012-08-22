openerp.locadis = function(instance){

    var module = instance.point_of_sale;
    var QWeb = instance.web.qweb;

    module.ProductListWidget = module.ProductListWidget.extend({
        template_empty: 'ProductEmptyListWidget',
        get_category: function(){
            return this.getParent().product_categories_widget.category;
        },
        renderElement: function(){
            var ss = this.pos_widget.screen_selector;
            console.log('ss',ss);
            if(this.get_category().name === 'Root' && ss && ss.get_user_mode() === 'cashier'){
                this.replaceElement(_.str.trim(QWeb.render(this.template_empty,{widget:this})));
            }else{
                this._super();
            }
        },
    });
};
            
        
    
