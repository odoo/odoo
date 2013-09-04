(function () {
    'use strict';

    var website = openerp.website;
    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click button[data-action=snippet]': 'snippet',
        }),
        start: function () {
            return this._super().then(function () {
                this.$buttons.snippet = this.$('button[data-action=snippet]');
                window.snippets = this.snippets = new website.Snippets();
                this.snippets.appendTo($(document.body));
            }.bind(this));
        },
        snippet: function (ev) {
            this.snippets.toggle();
        },
    });

    website.RTE.include({
        start_edition: function ($elements) {
            this.snippet_carousel();
            return this._super($elements);
        },
        // TODO clean
        snippet_carousel: function () {
            var self = this;
            var $carousel_options = $('.carousel .js_carousel_options');
            $carousel_options.on('click', '.label', function (e) {
                e.preventDefault();
                var $button = $(e.currentTarget);
                var $c = $button.parents(".carousel:first");
                var $carousel_inner = $c.find('.carousel-inner');

                if($button.hasClass("js_add")) {
                    var cycle = $carousel_inner.find('.item').size();
                    $carousel_inner.append(openerp.qweb.render('website.carousel'));
                    $c.carousel(cycle);
                }
                else {
                    $carousel_inner
                        .find('.item.active').remove().end()
                        .find('.item:first').addClass('active');
                    $c.carousel(0);
                    self.trigger('change', self, null);
                }
            });
            $carousel_options.show();
        },
    });

    /* ----- SNIPPET SELECTOR ---- */
    website.Snippets = openerp.Widget.extend({
        template: 'website.snippets',
        init: function () {
            this._super.apply(this, arguments);
        },
        start: function() {
            var self = this;

            $.ajax({
                type: "GET",
                url:  "/page/website.snippets",
                dataType: "text",
                success: function(snippets){
                    self.$el.html(snippets);
                    self.start_snippets();
                },
            });

        },
        path_eval: function(path){
            var obj = window;
            path = path.split('.');
            do{
                obj = obj[path.shift()];
            }while(path.length && obj);
            return obj;
        },

        // setup widget and drag and drop
        start_snippets: function(){
            var self = this;

            this.$('.oe_snippet').draggable({
                helper: 'clone',
                zIndex: '1000',
                appendTo: 'body',
                start: function(){
                    var snippet = $(this);
                    var action  = snippet.data('action');

                    self.deactivate_snippet_manipulators();
                    if( action === 'insert'){
                        self.activate_insertion_zones({
                            siblings: snippet.data('selector-siblings'),
                            childs:   snippet.data('selector-childs')
                        });
                    }else if( action === 'mutate' ){
                        self.activate_overlay_zones(snippet.data('selector'));
                    }

                    $('.oe_drop_zone').droppable({
                        over:   function(){
                            // FIXME: stupid hack to prevent multiple droppable to activate at once ...
                            // it's not even working properly but it's better than nothing.
                            $(".oe_drop_zone.oe_hover").removeClass("oe_hover");
                            $(this).addClass("oe_hover");
                        },
                        out:    function(){
                            $(this).removeClass("oe_hover");
                        },
                        drop:   function(){
                            if( action === 'insert' ){
                                $(".oe_drop_zone.oe_hover")
                                    .replaceWith(snippet.find('.oe_snippet_body').clone())
                                    .removeClass('oe_snippet_body');
                            }else if( action === 'mutate' ){
                                self.path_eval(snippet.data('action-function'))( $(".oe_drop_zone.oe_hover").data('target') );
                            }
                        },
                    });
                },
                stop: function(){
                    self.deactivate_zones();
                    self.activate_snippet_manipulators();
                },
            });

        },
        // Create element insertion drop zones. two css selectors can be provided
        // selector.childs -> will insert drop zones as direct child of the selected elements
        //   in case the selected elements have children themselves, dropzones will be interleaved
        //   with them.
        // selector.siblings -> will insert drop zones after and before selected elements
        activate_insertion_zones: function(selector){
            var self = this;
            var i, len, $zones;
            var child_selector   =  selector.childs   || '';
            var sibling_selector =  selector.siblings || '';
            var zone_template = "<div class='oe_drop_zone oe_insert'></div>";
            var $drop_zone = $('.oe_drop_zone');

            $drop_zone.remove();

            if(child_selector){
                $zones = $(child_selector);
                for(i = 0, len = $zones.length; i < len; i++ ){
                    $zones.eq(i).find('> *:not(.oe_drop_zone)').after(zone_template);
                    $zones.eq(i).prepend(zone_template);
                }
            }

            if(sibling_selector){
                $zones = $(sibling_selector);
                for(i = 0, len = $zones.length; i < len; i++ ){
                    if($zones.eq(i).prev('.oe_drop_zone').length === 0){
                        $zones.eq(i).before(zone_template);
                    }
                    if($zones.eq(i).next('.oe_drop_zone').length === 0){
                        $zones.eq(i).after(zone_template);
                    }
                }
            }

            // Cleaning up unnecessary zones
            $('.oe_snippets .oe_drop_zone').remove();   // no zone in the snippet selector ...
            $('#website-top-view').find('.oe_drop_zone').remove();   // no zone in the top bars ...
            $('#website-top-edit').find('.oe_drop_zone').remove();
            var count;
            do {
                count = 0;
                $zones = $('.oe_drop_zone + .oe_drop_zone');    // no two consecutive zones
                count += $zones.length;
                $zones.remove();

                $zones = $('.oe_drop_zone > .oe_drop_zone').remove();   // no recusrive zones
                count += $zones.length;
                $zones.remove();
            }while(count > 0);

            // Cleaning up zones placed between floating or inline elements. We do not like these kind of zones.
            $zones = $drop_zone;
            for(i = 0, len = $zones.length; i < len; i++ ){
                var zone = $zones.eq(i);
                var prev = zone.prev();
                var next = zone.next();
                var float_prev = prev.css('float')   || 'none';
                var float_next = next.css('float')   || 'none';
                var disp_prev  = prev.css('display') ||  null;
                var disp_next  = next.css('display') ||  null;
                if(     (float_prev === 'left' || float_prev === 'right')
                    &&  (float_next === 'left' || float_next === 'right')  ){
                    zone.remove();
                }else if( !( disp_prev === null
                          || disp_next === null
                          || disp_prev === 'block'
                          || disp_next === 'block' )){
                    zone.remove();
                }
            }
        },
        deactivate_zones: function(){
            $('.oe_drop_zone').remove();
        },

        activate_overlay_zones: function(selector){
            var $targets = $(selector);

            function is_visible($el){
                return     $el.css('display')    != 'none'
                        && $el.css('opacity')    != '0'
                        && $el.css('visibility') != 'hidden';
            }

            // filter out invisible elements
            $targets = $targets.filter(function(){ return is_visible($(this)); });

            // filter out elements with invisible parents
            $targets = $targets.filter(function(){
                var parents = $(this).parents().filter(function(){ return !is_visible($(this)); });
                return parents.length === 0;
            });

            var zone_template = "<div class='oe_drop_zone oe_overlay'></div>";
            $('.oe_drop_zone').remove();

            for(var i = 0, len = $targets.length; i < len; i++){
                var $target = $targets.eq(i);
                var $zone = $(zone_template);
                this.cover_target($zone,$target);
                $zone.appendTo('body');
                $zone.data('target',$target);
            }
        },
        cover_target: function($el, $target){
            $el.css({
                'position': 'absolute',
                'width': $target.outerWidth(),
                'height': $target.outerHeight(),
            });
            $el.css($target.offset());
        },
        activate_snippet_manipulators: function(){
            var self = this;
            this.activate_overlay_zones('#wrap .container');
            var $snippets = $('.oe_drop_zone');

            for(var i = 0, len = $snippets.length; i < len; i++){
                var $snippet = $snippets.eq(i);
                var $manipulator = $(openerp.qweb.render('website.snippet_manipulator'));
                $manipulator.css({
                    'top':    $snippet.css('top'),
                    'left':   $snippet.css('left'),
                    'width':  $snippet.css('width'),
                    'height': $snippet.css('height'),
                });
                $manipulator.data('target',$snippet.data('target'));
                $manipulator.appendTo('body');
                $snippet.remove();

                $manipulator.find('.oe_handle').mousedown(function(event){
                    var $handle = $(this);
                    var $manipulator = $handle.parent();
                    var $snippet = $manipulator.data('target');
                    var x = event.pageX;
                    var y = event.pageY;

                    var pt = $snippet.css('padding-top');
                    var pb = $snippet.css('padding-bottom');
                    pt = Number(pt.slice(0, -2)) || 0; //FIXME something cleaner to remove 'px'
                    pb = Number(pb.slice(0, -2)) || 0;

                    $manipulator.addClass('oe_hover');
                    event.preventDefault();

                    $(document.body).on({
                        mousemove: function(event){
                            var dx = event.pageX - x;
                            var dy = event.pageY - y;
                            event.preventDefault();
                            if($handle.hasClass('n') || $handle.hasClass('nw') || $handle.hasClass('ne')){
                                $snippet.css('padding-top',pt-dy+'px');
                                self.cover_target($manipulator,$snippet);
                            }else if($handle.hasClass('s') || $handle.hasClass('sw') || $handle.hasClass('se')){

                                $snippet.css('padding-bottom',pb+dy+'px');
                                self.cover_target($manipulator,$snippet);
                            }
                        },
                        mouseup: function(){
                            $body.off('mouseup mousemove');
                            self.deactivate_snippet_manipulators();
                            self.activate_snippet_manipulators();
                        }
                    });
                });

            }
        },
        deactivate_snippet_manipulators: function(){
            $('.oe_snippet_manipulator').remove();
        },
        toggle: function(){
            if(this.$el.hasClass('hide')){
                this.$el.removeClass('hide');
                this.activate_snippet_manipulators();
            }else{
                this.$el.addClass('hide');
                this.deactivate_snippet_manipulators();
            }
        },
    });
})();
