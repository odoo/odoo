function openerp_pos_basewidget(instance, module){ //module is instance.point_of_sale

    // This is a base class for all Widgets in the POS. It exposes relevant data to the 
    // templates : 
    // - widget.currency : { symbol: '$' | '€' | ..., position: 'before' | 'after }
    // - widget.format_currency(amount) : this method returns a formatted string based on the
    //   symbol, the position, and the amount of money.
    // if the PoS is not fully loaded when you instanciate the widget, the currency might not
    // yet have been initialized. Use __build_currency_template() to recompute with correct values
    // before rendering.

    module.PosBaseWidget = instance.web.Widget.extend({
        init:function(parent,options){
            this._super(parent);
            options = options || {};
            this.pos = options.pos || (parent ? parent.pos : undefined);
            this.pos_widget = options.pos_widget || (parent ? parent.pos_widget : undefined);
            this.build_currency_template();
        },
        build_currency_template: function(){

            if(this.pos && this.pos.get('currency')){
                this.currency = this.pos.get('currency');
            }else{
                this.currency = {symbol: '$', position: 'after'};
            }

            this.format_currency = function(amount){
                if(this.currency.position === 'after'){
                    return Math.round(amount*100)/100 + ' ' + this.currency.symbol;
                }else{
                    return this.currency.symbol + ' ' + Math.round(amount*100)/100;
                }
            }

        },
        show: function(){
            this.$el.show();
        },
        hide: function(){
            this.$el.hide();
        },
    });

}
