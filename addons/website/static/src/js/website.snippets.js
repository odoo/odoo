(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.snippets.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click button[data-action=snippet]': 'snippet',
        }),
        start: function () {
            return this._super().then(function () {

                this.$buttons.snippet = this.$('button[data-action=snippet]');
                window.snippets = this.snippets = new website.snippet.BuildingBlock();
                this.snippets.appendTo($(document.body));

            }.bind(this));
        },
        edit: function () {
            var res = this._super.apply(this, arguments);
            var self = this;
            var instanceReady = false;
            this.rte.on('instanceReady', this, function () {
                clearTimeout(instanceReady);
                instanceReady = setTimeout(function () { self.snippetBind(); }, 0);
            });
            return res;
        },
        snippet: function (ev) {
            this.snippets.toggle();
        },

        snippetBind: function () {
            var self = this;
            var $snipped_id = false;
            var snipped_event_flag = false;
            $("[data-snippet-id]")
                .filter(function() {
                    return !!website.snippet.editorRegistry[$(this).data("snippet-id")];
                })
                .on('click', function (event) {
                    if (snipped_event_flag) {
                        return;
                    }

                    snipped_event_flag = true;
                    setTimeout(function () {snipped_event_flag = false;}, 0);

                    if ($snipped_id && $snipped_id.get(0) == event.currentTarget) {
                        return;
                    }

                    self.snippetblur($snipped_id);

                    $snipped_id = $(event.currentTarget);

                    if (typeof $snipped_id.data("snippet-editor") === 'undefined' &&
                            website.snippet.editorRegistry[$snipped_id.data("snippet-id")]) {
                        $snipped_id.data("snippet-editor", new website.snippet.editorRegistry[$snipped_id.data("snippet-id")](self, $snipped_id));
                    }
                    self.snippetFocus($snipped_id);
                });
            $("body > :not(:has(#website-top-view))").on('click', function (ev) {
                    if (!snipped_event_flag && $snipped_id) {
                        self.snippetblur($snipped_id);
                        $snipped_id = false;
                    }
                });
        },

        snippetblur: function ($snipped_id) {
            if ($snipped_id) {
                if ($snipped_id.data("snippet-editor")) {
                    $snipped_id.data("snippet-editor").onBlur();
                }
                if ($snipped_id.data("snippet-view")) {
                    $snipped_id.data("snippet-view").onBlurEdit();
                }
            }
        },
        snippetFocus: function ($snipped_id) {
            if ($snipped_id) {
                if ($snipped_id.data("snippet-view")) {
                    $snipped_id.data("snippet-view").onFocusEdit();
                }
                if ($snipped_id.data("snippet-editor")) {
                    $snipped_id.data("snippet-editor").onFocus();
                }
            }
        },
    });

    /* ----- SNIPPET SELECTOR ---- */
    
    website.snippet = {};

    website.snippet.BuildingBlock = openerp.Widget.extend({
        template: 'website.snippets',
        init: function () {
            this._super.apply(this, arguments);
            if(!$('#oe_manipulators').length){
                $("<div id='oe_manipulators'></div>").appendTo('body');
            }
        },
        start: function() {
            var self = this;

            $.ajax({
                type: "GET",
                url:  "/page/website.snippets",
                dataType: "text",
                success: function(snippets){
                    self.$el.html(snippets);
                    self.$('.oe_snippet').each(function(index,snippet){
                        self.make_snippet_draggable($(snippet));
                    });
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

        // activate drag and drop for the snippets in the snippet toolbar
        make_snippet_draggable: function($snippet){
            var self = this;

            $snippet.draggable({
                helper: 'clone',
                zIndex: '1000',
                appendTo: 'body',
                start: function(){
                    var action  = $snippet.data('action');

                    self.deactivate_snippet_manipulators();
                    if( action === 'insert'){
                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            childs:   $snippet.data('selector-childs')
                        });
                    }else if( action === 'mutate' ){
                        self.activate_overlay_zones($snippet.data('selector'));
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
                                var $toInsert = $snippet.find('.oe_snippet_body').clone();
                                $toInsert.removeClass('oe_snippet_body');
                                $toInsert.addClass('oe_snippet_instance');
                                $toInsert.data('snippet-id',$snippet.data('snippet-id'));
                                $(".oe_drop_zone.oe_hover").replaceWith($toInsert);
                            }else if( action === 'mutate' ){
                                self.path_eval($snippet.data('action-function'))( $(".oe_drop_zone.oe_hover").data('target') );
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

        // return the original snippet in the editor bar from a snippet id (string)
        get_snippet_from_id: function(id){
            return $('.oe_snippet').filter(function(){
                    return $(this).data('snippet-id') === id;
                }).first();
        },
        // WIP
        make_draggable_instance: function($instance){
            var self = this;
            var $snippet = get_snippet_from_id($instance.data('snippet-id'));

            $instance.draggable({
                helper:   'clone',
                zIndex:   '1000',
                appendTo: 'body',
                start: function(){
                    var action = $snippet.data('action');
                    if(action === 'insert'){

                        self.deactivate_snippet_manipulators();
                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            child: $snippet.data('selector-childs')
                        });

                    }
                }
            });
        },

        // Create element insertion drop zones. two css selectors can be provided
        // selector.childs -> will insert drop zones as direct child of the selected elements
        //   in case the selected elements have children themselves, dropzones will be interleaved
        //   with them.
        // selector.siblings -> will insert drop zones after and before selected elements
        activate_insertion_zones: function(selector){
            var self = this;
            var child_selector   =  selector.childs   || '';
            var sibling_selector =  selector.siblings || '';
            var zone_template = "<div class='oe_drop_zone oe_insert'></div>";

            $('.oe_drop_zone').remove();

            if(child_selector){
                var $zones = $(child_selector);
                for( var i = 0, len = $zones.length; i < len; i++ ){
                    $zones.eq(i).find('> *:not(.oe_drop_zone)').after(zone_template);
                    $zones.eq(i).prepend(zone_template);
                }
            }

            if(sibling_selector){
                var $zones = $(sibling_selector);
                for( var i = 0, len = $zones.length; i < len; i++ ){
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
            $('#website-top-view .oe_drop_zone').remove();   // no zone in the top bars ...
            $('#website-top-edit .oe_drop_zone').remove();
            var count;
            do {
                count = 0;
                var $zones = $('.oe_drop_zone + .oe_drop_zone');    // no two consecutive zones
                count += $zones.length;
                $zones.remove();

                $zones = $('.oe_drop_zone > .oe_drop_zone').remove();   // no recusrive zones
                count += $zones.length;
                $zones.remove();
            }while(count > 0);

            // Cleaning up zones placed between floating or inline elements. We do not like these kind of zones.
            var $zones = $('.oe_drop_zone');
            for( var i = 0, len = $zones.length; i < len; i++ ){
                var zone = $zones.eq(i);
                var prev = zone.prev();
                var next = zone.next();
                var float_prev = zone.prev().css('float')   || 'none';
                var float_next = zone.next().css('float')   || 'none';
                var disp_prev  = zone.prev().css('display') ||  null;
                var disp_next  = zone.next().css('display') ||  null;
                if(     (float_prev === 'left' || float_prev === 'right')
                    &&  (float_next === 'left' || float_next === 'right')  ){
                    zone.remove();
                    continue;
                }else if( !( disp_prev === null
                          || disp_next === null
                          || disp_prev === 'block'
                          || disp_next === 'block' )){
                    zone.remove();
                    continue;
                }
            }
        },
        deactivate_zones: function(){
            $('.oe_drop_zone').remove();
        },

        // generate drop zones covering the elements selected by the selector
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
                $zone.appendTo('#oe_manipulators');
                $zone.data('target',$target);
            }
        },

        // puts $el at the same absolute position as $target
        cover_target: function($el, $target){
            $el.css({
                'position': 'absolute',
                'width': $target.outerWidth(),
                'height': $target.outerHeight(),
            });
            $el.css($target.offset());
        },

        // activates the manipulator boxes (with resizing handles) for all snippets
        activate_snippet_manipulators: function(){
            var self = this;
            // we generate overlay drop zones only to get an idea of where the snippet are, the drop
            // zones are replaced by manipulators
            this.activate_overlay_zones('#wrap .container');

            var $active_manipulator = null;
            var locked = false;

            $('.oe_drop_zone').each(function(){;

                var $zone = $(this);
                var $snippet = $zone.data('target');
                var $manipulator = $(openerp.qweb.render('website.snippet_manipulator'));

                self.cover_target($manipulator, $zone);
                $manipulator.data('target',$snippet);
                $manipulator.appendTo('#oe_manipulators');
                $zone.remove();

                $manipulator.mouseover(function(){
                    if(!locked && $active_manipulator != $manipulator){
                        if($active_manipulator){
                            $active_manipulator.removeClass('oe_selected');
                        }
                        $active_manipulator = $manipulator;
                        $manipulator.addClass('oe_selected');
                    }
                });
                /*$manipulator.mouseleave(function(){
                    if(!locked && $active_manipulator){
                        $active_manipulator.removeClass('oe_selected');
                        $active_manipulator = null;
                    }
                });*/
                /*
                $manipulator.click(function(){
                    if($active_manipulator === $manipulator){
                        selected = !selected;
                        $manipulator.toggleClass('oe_selected',selected);
                    }
                });
                */

                $manipulator.find('.oe_handle').mousedown(function(event){
                    locked = true;
                    var $handle = $(this);
                    var x = event.pageX;
                    var y = event.pageY;

                    var pt = $snippet.css('padding-top');
                    var pb = $snippet.css('padding-bottom'); 
                    pt = Number(pt.slice(0,pt.length - 2)) || 0; //FIXME something cleaner to remove 'px'
                    pb = Number(pb.slice(0,pb.length - 2)) || 0;
                    
                    $manipulator.addClass('oe_hover');
                    event.preventDefault();

                    $('body').mousemove(function(event){
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
                    });

                    $('body').mouseup(function(){
                        locked = false;
                        $('body').unbind('mousemove');
                        $('body').unbind('mouseup');
                        self.deactivate_snippet_manipulators();
                        self.activate_snippet_manipulators();
                    });
                });
                    
            });
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


    website.snippet.viewRegistry = {};
    website.snippet.View = openerp.Class.extend({
        $: function () {
            return this.$el.find.apply(this.$el, arguments);
        },
        init: function (dom) {
            this.$el = $(dom);
            this._super.apply(this, arguments);
        },
        /* onFocusEdit
        *  if they are an editor for this snippet-id 
        *  Called before onFocus of snippet editor
        */
        onFocusEdit : function () {},

        /* onBlurEdit
        *  if they are an editor for this snippet-id 
        *  Called after onBlur of snippet editor
        */
        onBlurEdit : function () {},

        /* getOptions
        *  get the options saved in the html view
        */
        getOptions: function () {
            var options = this.$el.data("snippet-options");
            return options ? JSON.parse(options) : undefined;
        },
    });


    website.snippet.editorRegistry = {};
    website.snippet.Editor = openerp.Widget.extend({
        init: function (parent, dom) {
            this.$target = $(dom);
            this.parent = parent;
            this._super.apply(this, arguments);
            this.renderElement();
            this.start();
        },

        renderElement: function() {
            var $el;
            if (this.template) {
                $el = $(openerp.qweb.render(this.template, {widget: this}).trim());
            } else {
                $el = this._make_descriptive();
            }
            $el = $('<li id="website-top-edit-snippet-option"></li>').append($el);
            this.replaceElement($el);
        },

        /* onFocus
        *  called when the user click inside the snippet dom
        */
        onFocus : function () {
            this.$el.prependTo(this.parent.$('#website-top-edit .nav.pull-right'));
        },

        /* onFocus
        *  called when the user click outide the snippet dom
        */
        onBlur : function () {
            this.$el.detach();
        },

        /* setOptions
        *  saved the options in the html view
        */
        setOptions: function (options) {
            $target.attr("data-snippet-options", JSON.stringify(options));
        },

        /* getOptions
        *  get the options saved in the html view
        */
        getOptions: function () {
            var options = this.$target.data("snippet-options");
            return options ? JSON.parse(options) : undefined;
        },
    });


    website.snippet.editorRegistry.carousel = website.snippet.Editor.extend({
        template : "website.snippets.EditorBar.carousel",
        start : function () {
            var self = this;

            self.$(".js_add").on('click', function (e) {
                e.preventDefault();
                var $inner = self.$target.find('.carousel-inner');
                var cycle = $inner.find('.item').size();
                $inner.append(openerp.qweb.render('website.carousel'));
                self.$target.carousel(cycle);
            });


            self.$(".js_remove").on('click', function (e) {
                e.preventDefault();
                var $inner = self.$target.find('.carousel-inner');
                if ($inner.find('.item').size() > 1) {
                    $inner
                        .find('.item.active').remove().end()
                        .find('.item:first').addClass('active');
                    self.$target.carousel(0);
                }
            });


            var bg = this.$target.find('.carousel-inner .item.active').css('background-image').replace(/url\((.*)\)/g, '\$1');
            this.$( 'select[name="carousel-background"] option[value="'+bg+'"], select[name="carousel-background"] option[value="'+bg.replace(window.location.protocol+'//'+window.location.host, '')+'"]')
                .prop('selected', true);
            self.$('select[name="carousel-background"]').on('change', function () {
                self.$target.find('.carousel-inner .item.active').css('background-image', 'url(' + $(this).val() + ')');
                $(this).val("");
            });


            self.$('select[name="carousel-style"]').on('change', function () {
                var $container = self.$target.find('.carousel-inner .item.active .container');
                $('.content_image', $container).remove();
                switch ($(this).val()) {
                    case 'no_image':
                        $('.content', $container).attr("class", "content");
                        break;
                    case 'image_left':
                        $('.content', $container).attr("class", "content col-md-6")
                            .before('<div class="content_image col-md-5"><img class="img-rounded img-responsive" src="/website/static/src/img/china.jpg"></div>');
                    break;
                    case 'image_right':
                        $('.content', $container).attr("class", "content col-md-6")
                            .after('<div class="content_image col-md-5 col-lg-offset-1"><img class="img-rounded img-responsive" src="/website/static/src/img/china.jpg"></div>');
                    break;
                }
                $(this).val("");
            });
        }
    });

})();
