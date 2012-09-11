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
 * duration: this is the duration of the scrolling animation
 * wheel_step: the target will be scrolled by wheel_step pixels on each mouse scroll.
 * track_bottom: the target will be kept on bottom when it's on the bottom and the size has changed
 * on_show: this function will be called with the scrollbar as sole argument when the scrollbar is shown
 * on_hide: this function will be called with the scrollbar as sole argument when the scrollbar is hidden
 */
function openerp_pos_scrollbar(instance, module){ //module is instance.point_of_sale

    module.ScrollbarWidget = instance.web.Widget.extend({
        template:'ScrollbarWidget',

        init: function(parent,options){
            var self = this;
            options = options || {};
            this._super(parent,options);
            this.target_widget = options.target_widget;
            this.target_selector = options.target_selector;
            this.scroll_target = this.target().scrollTop();
            this.scroll_step   = options.step || 0.8;
            this.scroll_duration  = options.duration || 250;
            this.wheel_step = options.wheel_step || 80;
            this.name = options.name || 'unnamed';
            this.bottom = false;  // true if the scroller cannot be scrolled further 
            this.track_bottom = options.track_bottom || false;
            this.on_show = options.on_show || function(){};
            this.on_hide = options.on_hide || function(){};

            // these handlers are declared once for the object's lifetime so that we can bind and unbind them.
            this.resize_handler = function(){
                setTimeout(function(){
                    if(self.bottom && self.track_bottom){
                        self.set_position(Number.MAX_VALUE);
                    }
                    self.update_scroller_dimensions();
                    self.update_button_status();
                    self.auto_hide(false);
                },0);
            };
            this.target_mousewheel_handler = function(event,delta){
                self.scroll(delta*self.wheel_step);
            }
        },

        renderElement: function(){
            this._super();
            var self = this;
            this.$('.up-button').off('click').click(function(){
                self.page_up();
            });
            this.$('.down-button').off('click').click(function(){
                self.page_down();
            });
            this.update_scroller_dimensions(false);
            this.update_button_status();
            this.auto_hide(false);
            this.$el.bind('mousewheel',function(event,delta){
                self.scroll(delta*self.wheel_step);
                return false;
            });
            this.$el.bind('click',function(event){
                var vpos = event.pageY - self.$el.offset().top;
                var spos = self.scroller_dimensions();
                if(vpos > spos.bar_pos && vpos < spos.pos){
                    self.page_up();
                }else if(   (vpos < spos.bar_pos + spos.bar_height) && 
                            (vpos > spos.pos + spos.height) ){
                    self.page_down();
                }
            });
            // FIXME: use the event bus to handle window resize events
            $(window).unbind('resize',this.resize_handler);
            $(window).bind('resize',this.resize_handler);

            this.target().unbind('mousewheel',this.target_mousweheel_handler);
            this.target().bind('mousewheel',this.target_mousewheel_handler);
            
            // because the rendering is asynchronous we must wait for the next javascript update
            // for good dimensions values
            setTimeout(function(){
                self.update_scroller_dimensions(false);
                self.update_button_status();
                self.auto_hide(false);
            },0);
        },

        // binds the window resize and the target scrolling events.
        // it is good advice not to bind these multiple_times
        bind_events:function(){
            $(window).resize(function(){     
            });
            this.target().bind('mousewheel',function(event,delta){
                self.scroll(delta*self.wheel_step);
            });
        },

        // shows the scrollbar. if animated is true, it will do it in an animated fashion
        show: function(animated){   //FIXME: animated show and hide don't work ... ? 
            if(animated){
                this.$el.show().animate({'width':'48px'}, 500, 'swing');
            }else{
                this.$el.show().css('width','48px');
            }
            this.on_show(this);
        },

        // hides the scrollbar. if animated is true, it will do it in a animated fashion
        hide: function(animated){
            var self = this;
            if(animated){
                this.$el.animate({'width':'0px'}, 500, 'swing', function(){ self.$el.hide();});
            }else{
                this.$el.hide().css('width','0px');
            }
            this.on_hide(this);
        },

        // returns the scroller position and other information as a dictionnary with the following fields:
        // pos: the position in pixels of the top of the scroller starting from the top of the scrollbar
        // height: the height of the scroller in pixels
        // bar_pos: the position of the top of the scrollbar's inner region, starting from the top
        // bar_height: the height of the scrollbar's inner region
        scroller_dimensions: function(){
            var target = this.target()[0];
            var scroller_height = target.clientHeight / target.scrollHeight || 0;
            var scroller_pos    = this.scroll_target / target.scrollHeight || 0;
            var button_up_height = this.$('.up-button')[0].offsetHeight || 48;
            var button_down_height = this.$('.down-button')[0].offsetHeight || 48;
            
            var bar_height = this.$el[0].offsetHeight || 96;
            var scrollbar_height = bar_height - button_up_height - button_down_height;
            
            scroller_pos = scroller_pos * scrollbar_height + button_up_height;
            scroller_height = scroller_height * scrollbar_height;

            return { pos: Math.round(scroller_pos), 
                     height: Math.round(scroller_height),
                     bar_pos: button_up_height,
                     bar_height: scrollbar_height };
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
            var target = this.target()[0];
            if(animated){
                this.$('.scroller').animate({'top':dim.pos+'px', 'height': dim.height+'px'},this.scroll_duration);
            }else{
                this.$('.scroller').css({'top':dim.pos+'px', 'height': dim.height+'px'});
            }
            if(this.scroll_target + target.clientHeight >= target.scrollHeight){
                this.bottom = true;
            }else{
                this.bottom = false;
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
                    return this.target_widget.$el;
                }
            }else if(this.target_selector){
                return $(this.target_selector);
            }else{
                return undefined;
            }
        },

        //scroll one page up
        page_up: function(){
            return this.set_position(this.scroll_target - this.get_scroll_step(), true);
        },

        //scroll one page down
        page_down: function(){
            return this.set_position(this.scroll_target + this.get_scroll_step(), true);
        },

        //scrolls up or down by pixels
        scroll: function(pixels){
            return this.set_position(this.scroll_target - pixels, false);
        },

        //scroll to a specific position (in pixels). 
        //if animated is true, it will do this in an animated fashion with a duration equal to scroll_duration 
        set_position: function(position,animated){
            var self = this;
            var target = this.target()[0];
            var bottom = target.scrollHeight-target.clientHeight;
            this.scroll_target = Math.max(0,Math.min(bottom,position));
            if(this.scroll_target === 0){
                this.position = 'top';
            }else if(this.scroll_target === 'bottom'){
                this.position = 'bottom';
            }else{
                this.position = 'center';
            }
            if(animated){
                this.target().animate({'scrollTop':this.scroll_target},this.scroll_duration);
                this.update_button_status();
                this.update_scroller_dimensions(true);
            }else{
                this.target().scrollTop(this.scroll_target);
                this.update_scroller_dimensions(false);
                this.update_button_status();
            }
            return this.scroll_target;
        },
        
        //returns the current position of the scrollbar
        get_position: function(){
            return this.scroll_target;
        },
        
        //returns true if it cannot be scrolled further down
        is_at_bottom: function(){
            return this.bottom;
        }
            
    });
}
