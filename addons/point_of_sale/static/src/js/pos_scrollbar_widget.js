/*
 * This Widget provides a javascript scrollbar that is suitable to use with resistive 
 * tactile screens. 
 *
 * Options:
 * target_widget : the widget that will be scrolled. 
 * target_selector : if you don't want to scroll the root element of the the widget, you can provide a
 *   jquery selector string that will match on the widget's dom element. If there is no widget provided,
 *   it will match on the document
 * step: on each click, the target will be scrolled by it's deplayed size multiplied by this value. 
 * delay: this is the duration of the scrolling animation
 * wheel_step: the target will be scrolled by wheel_step pixels on each mouse scroll.
 */
function openerp_pos_scrollbar(instance, module){ //module is instance.point_of_sale

    module.ScrollbarWidget = instance.web.Widget.extend({
        template:'ScrollbarWidget',

        init: function(parent,options){
            options = options || {};
            this._super(parent,options);
            this.target_widget = options.target_widget;
            this.target_selector = options.target_selector;
            this.scroll_target = this.target().scrollTop();
            this.scroll_step   = options.step || 0.8;
            this.scroll_delay  = options.delay || 250;
            this.wheel_step = options.wheel_step || 80;
        },

        start: function(){
            var self = this;
            this.$('.up-button').off('click').click(function(){
                self.page_up();
            });
            this.$('.down-button').off('click').click(function(){
                self.page_down();
            });
            this.update_scroller_dimensions();
            this.update_button_status();
            this.auto_hide(false);
            $(window).resize(function(){    //FIXME REMOVE HANDLER ... 
                self.update_scroller_dimensions();
                self.update_button_status();
                self.auto_hide(false);
            });
            this.target().bind('mousewheel',function(event,delta){
                self.scroll(delta*self.wheel_step);
            });
            this.$element.bind('mousewheel',function(event,delta){
                self.scroll(delta*self.wheel_step);
            });
            this.$element.bind('click',function(event){
                var vpos = event.pageY - self.$element.offset().top;
                var spos = self.scroller_dimensions();
                if(vpos > spos.bar_pos && vpos < spos.pos){
                    self.page_up();
                }else if(   (vpos < spos.bar_pos + spos.bar_height) && 
                            (vpos > spos.pos + spos.height) ){
                    self.page_down();
                }
            });

        },

        // shows the scrollbar. if animated is true, it will do it in an animated fashion
        show: function(animated){   //FIXME: animated show and hide don't work ... ? 
            if(animated){
                this.$element.show().animate({'width':'48px'}, 500, 'swing');
            }else{
                this.$element.show().css('width','48px');
            }
        },

        // hides the scrollbar. if animated is true, it will do it in a animated fashion
        hide: function(animated){
            var self = this;
            if(animated){
                this.$element.animate({'width':'0px'}, 500, 'swing', function(){ self.$element.hide();});
            }else{
                this.$element.hide().css('width','0px');
            }
        },

        // returns the scroller position and other information as a dictionnary with the following fields:
        // pos: the position in pixels of the top of the scroller starting from the top of the scrollbar
        // height: the height of the scroller in pixels
        // bar_pos: the position of the top of the scrollbar's inner region, starting from the top
        // bar_height: the height of the scrollbar's inner region
        scroller_dimensions: function(){
            var target = this.target()[0];
            var scroller_height = target.clientHeight / target.scrollHeight;
            var scroller_pos    = this.scroll_target / target.scrollHeight;
            var button_up_height = this.$('.up-button')[0].offsetHeight;
            var button_down_height = this.$('.down-button')[0].offsetHeight;
            
            var bar_height = this.$element[0].offsetHeight;
            var scrollbar_height = bar_height - button_up_height - button_down_height;
            
            scroller_pos = scroller_pos * scrollbar_height + button_up_height;
            scroller_height = scroller_height * scrollbar_height;

            return { pos: Math.round(scroller_pos), 
                     height: Math.round(scroller_height),
                     bar_pos: button_up_height,
                     bar_height: scrollbar_height };
        },

        //scrolls up or down by pixels
        scroll: function(pixels){
            var target = this.target()[0];
            this.scroll_target = this.scroll_target - pixels;
            this.scroll_target = Math.max(0,Math.min(target.scrollHeight-target.clientHeight, this.scroll_target));
            this.target().scrollTop(this.scroll_target);
            this.update_scroller_dimensions();
            this.update_button_status();
        },

        //checks if it should show or hide the scrollbar based on the target content and then show or hide it
        // if animated is true, then the scrollbar will be shown or hidden with an animation
        auto_hide: function(animated){
            var target = this.target()[0];
            if(target.clientHeight && (target.clientHeight === target.scrollHeight)){
                this.hide(animated);
            }else{
                this.show(animated);
            }
        },

        //returns the pageup/down scrolling distance in pixels
        get_scroll_step: function(){
            var target = this.target()[0];
            var step = target.clientHeight * this.scroll_step;
            var c    = target.scrollHeight / step;
            var c    = Math.max(1,Math.ceil(c));
            return target.scrollHeight / c;
        },

        //sets the scroller to the correct size and position based on the target scrolling status
        //if animated is true, the scroller will move smoothly to its destination
        update_scroller_dimensions: function(animated){
            var dim = this.scroller_dimensions();
            if(animated){
                this.$('.scroller').animate({'top':dim.pos+'px', 'height': dim.height+'px'},this.scroll_delay);
            }else{
                this.$('.scroller').css({'top':dim.pos+'px', 'height': dim.height+'px'});
            }
        },

        //disable or enable the up/down buttons according to the scrolled position
        update_button_status: function(){
            var target = this.target()[0];
            this.$('.up-button').removeClass('disabled');
            this.$('.down-button').removeClass('disabled');
            if(this.scroll_target === 0){
                this.$('.up-button').addClass('disabled');
            }
            if(this.scroll_target + target.clientHeight >= target.scrollHeight){
                this.$('.down-button').addClass('disabled');
            }
        },

        //returns the jquery object of the scrolling target
        target: function(){
            if(this.target_widget){
                if(this.target_selector){
                    return this.target_widget.$(this.target_selector);
                }else{
                    return this.target_widget.$element;
                }
            }else if(this.target_selector){
                return $(this.target_selector);
            }else{
                return undefined;
            }
        },

        //scroll one page up
        page_up: function(){
            var target = this.target()[0]
            if(this.scroll_target <= 0){
                return;
            }
            this.scroll_target = this.scroll_target - this.get_scroll_step();
            this.scroll_target = Math.max(0,this.scroll_target);
            this.target().animate({'scrollTop':this.scroll_target},this.scroll_delay);
            this.update_scroller_dimensions(true);
            this.update_button_status();
        },

        //scroll one page down
        page_down: function(){
            var target = this.target()[0];
            var max_scroll = target.scrollHeight - target.clientHeight;

            if(this.scroll_target >= max_scroll){
                this.scroll_target = max_scroll;
                this.target().scrollTop(max_scroll);
                return;
            }
            this.scroll_target = this.scroll_target + this.get_scroll_step();
            this.scroll_target = Math.min(this.scroll_target, max_scroll);
            this.target().animate({'scrollTop':this.scroll_target},this.scroll_delay);
            this.update_scroller_dimensions(true);
            this.update_button_status();
        },
    });
}
