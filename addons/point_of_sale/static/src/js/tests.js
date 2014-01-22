function openerp_pos_tests(instance, module){ //module is instance.point_of_sale

    // Various UI Tests to measure performance and memory leaks.
    module.UiTester = function(){
        var running = false;
        var queue = new module.JobQueue();

        // stop the currently running test
        this.stop = function(){
            queue.clear();
        };

        // randomly switch product categories
        this.category_switch = function(interval){
            queue.schedule(function(){
                var breadcrumbs = $('.breadcrumb-button');
                var categories  = $('.category-button');
                if(categories.length > 0){
                    var rnd = Math.floor(Math.random()*categories.length);
                    categories.eq(rnd).click();
                }else{
                    var rnd = Math.floor(Math.random()*breadcrumbs.length);
                    breadcrumbs.eq(rnd).click();
                }
            },{repeat:true, duration:interval});
        };

        // randomly order products then resets the order
        this.order_products = function(interval){

            queue.schedule(function(){
                var def = new $.Deferred();
                var order_queue = new module.JobQueue();
                var order_size = 1 + Math.floor(Math.random()*10);

                while(order_size--){
                    order_queue.schedule(function(){
                        var products = $('.product');
                        if(products.length > 0){
                            var rnd = Math.floor(Math.random()*products.length);
                            products.eq(rnd).click();
                        }
                    },{duration:20});
                }
                order_queue.finished().then(function(){
                        $('.deleteorder-button').click();
                        def.resolve();
                });
                return def;
            },{repeat:true, duration: interval});

        };

        // makes a complete product order cycle ( print via proxy must be activated, and scale deactivated ) 
        this.full_order_cycle = function(interval){
            queue.schedule(function(){
                var def = new $.Deferred();
                var order_queue = new module.JobQueue();
                var order_size = 1 + Math.floor(Math.random()*50);

                while(order_size--){
                    order_queue.schedule(function(){
                        var products = $('.product');
                        if(products.length > 0){
                            var rnd = Math.floor(Math.random()*products.length);
                            products.eq(rnd).click();
                        }
                    },{duration:50});
                }
                order_queue.schedule(function(){
                    $('.paypad-button:first').click();
                },{duration:250});
                order_queue.schedule(function(){
                    $('.paymentline-input:first').val(10000);
                    $('.paymentline-input:first').keydown();
                    $('.paymentline-input:first').keyup();
                },{duration:250});
                order_queue.schedule(function(){
                    $('.pos-actionbar-button-list .button:eq(2)').click();
                },{duration:250});
                order_queue.schedule(function(){
                    def.resolve();
                });
                return def;
            },{repeat: true, duration: interval});
        };
    };
    
    if(jQuery.deparam(jQuery.param.querystring()).debug !== undefined){
        window.pos_test_ui = new module.UiTester();
    }

}
