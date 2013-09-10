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

            }.bind(this));
        },
        edit: function () {
            var res = this._super.apply(this, arguments);
            var self = this;
            var instanceReady = false;
            this.rte.on('instanceReady', this, function () {
                clearTimeout(instanceReady);
                instanceReady = setTimeout(function () {
                    self.activate_building_block_manipulators();
                    self.activate_snippet_click_editor();
                }, 0);

            });
            return res;
        },

        activate_building_block_manipulators: function () {
            window.snippets = this.snippets = new website.snippet.BuildingBlock(this);
            this.snippets.appendTo($(document.body));
            this.snippets.activate_snippet_manipulators();
        },
        snippet: function (ev) {
            this.snippets.toggle();
        },
        activate_snippet_click_editor: function () {
            var self = this;
            var $snipped_id = false;
            var snipped_event_flag = false;
            $("body").on('click', "[data-snippet-id]", function (event) {
                    if (snipped_event_flag) {
                        return;
                    }

                    snipped_event_flag = true;
                    setTimeout(function () {snipped_event_flag = false;}, 0);

                    if ($snipped_id && $snipped_id.get(0) == event.currentTarget) {
                        return;
                    }

                    self.snippet_blur($snipped_id);

                    $snipped_id = $(event.currentTarget);

                    if (typeof $snipped_id.data("snippet-editor") === 'undefined') {
                        $snipped_id.data("snippet-editor", new (website.snippet.editorRegistry[$snipped_id.data("snippet-id")] || website.snippet.editorRegistry.box)(self, $snipped_id));
                    }
                    self.snippet_focus($snipped_id);
                });
            $("body > :not(:has(#website-top-view))").on('click', function (ev) {
                    if (!snipped_event_flag && $snipped_id) {
                        self.snippet_blur($snipped_id);
                        $snipped_id = false;
                    }
                });
        },
        snippet_blur: function ($snipped_id) {
            if ($snipped_id) {
                if ($snipped_id.data("snippet-editor")) {
                    $snipped_id.data("snippet-editor").onBlur();
                }
                if ($snipped_id.data("snippet-view")) {
                    $snipped_id.data("snippet-view").onBlurEdit();
                }
            }
        },
        snippet_focus: function ($snipped_id) {
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

    // puts $el at the same absolute position as $target
    website.snippet.cover_target = function cover_target($el, $target){
        $el.css({
            'position': 'absolute',
            'width': $target.outerWidth(),
            'height': $target.outerHeight(),
        });
        $el.css($target.offset());
    }

    website.snippet.BuildingBlock = openerp.Widget.extend({
        template: 'website.snippets',
        init: function (parent) {
            this.parent = parent;
            this._super.apply(this, arguments);
            if(!$('#oe_manipulators').length){
                $("<div id='oe_manipulators'></div>").appendTo('body');
            }
        },
        start: function() {
            var self = this;

            var snippets_template = [];
            _.each(openerp.qweb.compiled_templates, function (val, key) {
                if (key.indexOf('website.snippets.') === 0) {
                    var $snippet = $(openerp.qweb.render(key)).addClass("oe_snippet");
                    if ($snippet.data("action")) {
                        self.$el.append($snippet);
                        self.make_snippet_draggable($snippet);
                    }
                }
            });

            this.bind_selected_manipulator();

        },
        path_eval: function(path){
            var obj = window;
            path = path.split('.');
            do{
                obj = obj[path.shift()];
            }while(path.length && obj);
            return obj;
        },

        bind_selected_manipulator: function () {

            var $selected_target = null;
            $("body").mouseover(function (event){
                var $target = $(event.srcElement).parents("[data-snippet-id]:first");
                if($target.length && $selected_target != $target){
                    if($selected_target){
                        $selected_target.data('manipulator').removeClass('oe_selected');
                    }
                    $selected_target = $target;
                    $target.data('manipulator').addClass('oe_selected');
                }
            });
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
                            var snipped_id = $snippet.data('snippet-id');

                            if (!$(".oe_drop_zone.oe_hover").length) {
                                return false;
                            }

                            if($snippet.find('.oe_snippet_body').size()){
                                var $toInsert = $snippet.find('.oe_snippet_body').clone();
                                $toInsert.removeClass('oe_snippet_body');
                                $toInsert.addClass('oe_snippet_instance');
                                $toInsert.attr('data-snippet-id', snipped_id);
                                $(".oe_drop_zone.oe_hover").replaceWith($toInsert);
                                var $target = $toInsert;

                                self.deactivate_snippet_manipulators();
                                self.activate_snippet_manipulators();
                            } else {
                                var $target = $(".oe_drop_zone.oe_hover").data('target');
                            }

                            if (website.snippet.editorRegistry[snipped_id]) {
                                var snippet = new website.snippet.editorRegistry[snipped_id](this.parent, $target);
                                snippet.build_snippet($target);
                                $target.click();
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
                website.snippet.cover_target($zone,$target);
                $zone.appendTo('#oe_manipulators');
                $zone.data('target',$target);
            }
        },

        // activates the manipulator boxes (with resizing handles) for all snippets
        activate_snippet_manipulators: function(){
            var self = this;
            // we generate overlay drop zones only to get an idea of where the snippet are, the drop
            // zones are replaced by manipulators
            this.activate_overlay_zones('#wrap [data-snippet-id]');

            $('.oe_drop_zone').each(function(){

                var $zone = $(this);
                var $snippet = $zone.data('target');
                var $manipulator = $(openerp.qweb.render('website.snippet_manipulator'));

                website.snippet.cover_target($manipulator, $zone);
                $manipulator.data('target',$snippet);
                $snippet.data('manipulator',$manipulator);
                $manipulator.appendTo('#oe_manipulators');
                $zone.remove();
                $snippet.off("resize").on("resize", function () {
                    self.deactivate_snippet_manipulators();
                    self.activate_snippet_manipulators();
                });

            });
        },
        deactivate_snippet_manipulators: function(){
            $('.oe_snippet_manipulator').remove();
        },
        toggle: function(){
            if(this.$el.hasClass('hide')){
                this.$el.removeClass('hide');
                //this.activate_snippet_manipulators();
            }else{
                this.$el.addClass('hide');
                //this.deactivate_snippet_manipulators();
            }
        },
    });


    website.snippet.animationRegistry = {};
    website.snippet.Animation = openerp.Class.extend({
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
        *  Read data saved for your snippet animation.
        */
        getOptions: function () {
            var options = this.$el.data("snippet-options");
            return options ? JSON.parse(options) : undefined;
        },
    });


    $(document).ready(function () {
        $("[data-snippet-id]").each(function() {
                var $snipped_id = $(this);
                if (typeof $snipped_id.data("snippet-view") === 'undefined' &&
                        website.snippet.animationRegistry[$snipped_id.data("snippet-id")]) {
                    $snipped_id.data("snippet-view", new website.snippet.animationRegistry[$snipped_id.data("snippet-id")]($snipped_id));
                }
            });
    });


    website.snippet.editorRegistry = {};
    website.snippet.Editor = openerp.Class.extend({
        init: function (parent, dom) {
            this.$target = $(dom);
            this.parent = parent;
            this._readXMLData();
            this.start();
        },

        /*
        *  _readXMLData
        *  Read data XML and set value into:
        *  this.$el :
        *       all xml data
        *  this.$editor :
        *       content of .oe_snippet_editorbar
        *       Displayed into the editor bar on focus
        *  this.$thumbnail :
        *       content of .oe_snippet_thumbnail
        *       Displayed in bottom editor menu, when the user click on "Building Blocks"
        *  this.$body :
        *       content of .oe_snippet_body
        *       Insert into the view when the thumbnail is drag and droped into a drop zone
        */
        _readXMLData: function() {
            if (this.template) {
                this.$el = $(openerp.qweb.render(this.template, {widget: this}).trim());
                this.$editor = this.$el.find(".oe_snippet_editorbar");
                this.$thumbnail = this.$el.find(".oe_snippet_thumbnail");
                this.$body = this.$el.find(".oe_snippet_body");
            }
        },

        /*
        * Start
        * Method launch after the initialization of the snippet and after reading data XML
        */
        start : function () {
        },

        /*
        *  build_snippet
        *  This method is called just after that a thumbnail is drag and droped into a drop zone
        *  (after the insertion of this.$body, if this.$body exists)
        */
        build_snippet: function () {

        },

        /* onFocus
        *  This method is called when the user click inside the snippet in the dom
        */
        onFocus : function () {
            if(this.$editor) this.$editor.prependTo(this.parent.$('#website-top-edit .nav.pull-right'));
        },

        /* onFocus
        *  This method is called when the user click outide the snippet in the dom, after a focus
        */
        onBlur : function () {
            if(this.$editor) this.$editor.detach();
        },

        /* setOptions
        *  Use this method when you want to save some data for your snippet animation.
        */
        setOptions: function (options) {
            $target.attr("data-snippet-options", JSON.stringify(options));
        },

        /* getOptions
        *  Read data saved for your snippet animation.
        */
        getOptions: function () {
            var options = this.$target.data("snippet-options");
            return options ? JSON.parse(options) : undefined;
        },
    });


    website.snippet.editorRegistry.box = website.snippet.Editor.extend({
        onFocus : function () {
            var self = this;
            var $box = $(openerp.qweb.render("website.snippets.box"));

            $box.find(".oe_snippet_editorbar").prependTo(this.parent.$('#website-top-edit .nav.pull-right'));

            this.$target.data('manipulator').append($box.find(".oe_handles").html()).addClass('oe_active');

            function padding_margin_cover ($manipulator, $snippet) {
                var height = parseInt($snippet.height() || 0);
                var width = parseInt($snippet.width() || 0);

                var pcss = {
                    top: parseInt($snippet.css('padding-top')) + 'px',
                    bottom: parseInt($snippet.css('padding-bottom')) + 'px',
                    left: parseInt($snippet.css('padding-left')) + 'px',
                    right: parseInt($snippet.css('padding-right')) + 'px',
                };
                var $padding = $manipulator.find(".oe_boxsize").css(pcss);

                var mcss = {
                    top: -parseInt($snippet.css('margin-top')) + 'px',
                    bottom: -parseInt($snippet.css('margin-bottom')) + 'px',
                    left: -parseInt($snippet.css('margin-left')) + 'px',
                    right: -parseInt($snippet.css('margin-right')) + 'px',
                };
                var $margin = $manipulator.find(".oe_margin").css(mcss);
            }
            padding_margin_cover( this.$target.data('manipulator'),  this.$target);

            this.$target.data('manipulator').find(".oe_handle").on('mousedown', function (event){
                    event.preventDefault();

                    var $handle = $(this);
                    var $manipulator = self.$target.data('manipulator');
                    var $snippet = self.$target;

                    var x = event.pageX;
                    var y = event.pageY;

                    var padding=[parseInt($snippet.css('padding-top') || 0),
                                parseInt($snippet.css('padding-bottom') || 0),
                                parseInt($snippet.css('padding-left') || 0),
                                parseInt($snippet.css('padding-right') || 0)];

                    $manipulator.addClass('oe_hover');

                    var body_mousemove = function (event){
                        event.preventDefault();
                        var dx = event.pageX - x;
                        var dy = event.pageY - y;

                        if($handle.hasClass('n') || $handle.hasClass('nw') || $handle.hasClass('ne')){
                            $snippet.css('padding-top', (padding[0]+dy)+'px');
                        }
                        if($handle.hasClass('s') || $handle.hasClass('sw') || $handle.hasClass('se')){
                            $snippet.css('padding-bottom',(padding[1]-dy)+'px');
                        }
                        if($handle.hasClass('w') || $handle.hasClass('sw') || $handle.hasClass('nw')){
                            $snippet.css('padding-left',(padding[2]+dx)+'px');
                        }
                        if($handle.hasClass('e') || $handle.hasClass('se') || $handle.hasClass('ne')){
                            $snippet.css('padding-right',(padding[3]-dx)+'px');
                        }
                        website.snippet.cover_target($manipulator, $snippet);
                        padding_margin_cover($manipulator, $snippet);
                    };
                    $('body').mousemove(body_mousemove);

                    var body_mouseup = function(){
                        $('body').unbind('mousemove', body_mousemove);
                        $('body').unbind('mouseup', body_mouseup);
                        $snippet.trigger("resize");
                        self.onBlur();
                        self.onFocus();
                    };
                    $('body').mouseup(body_mouseup);
                });
            this._super();
        },
        onBlur : function () {
            this._super();
            this.$target.data('manipulator')
                .removeClass('oe_active')
                .empty();
            this.parent.$('#website-top-edit .nav.pull-right > .box_resize').remove();
        },
    });

    website.snippet.editorRegistry.carousel = website.snippet.editorRegistry.box.extend({
        template : "website.snippets.carousel",
        build_snippet: function($target) {
            var id = "myCarousel" + $("body .carousel").size();
            $target.attr("id", id);
            $target.find(".carousel-control").attr("href", "#"+id);
        },
        start : function () {
            var self = this;

            this.$editor.find(".js_add").on('click', this.on_add);
            this.$editor.find(".js_remove").on('click', this.on_remove);

            var bg = this.$target.find('.carousel-inner .item.active').css('background-image').replace(/url\((.*)\)/g, '\$1');
            this.$editor.find('select[name="carousel-background"] option[value="'+bg+'"], select[name="carousel-background"] option[value="'+bg.replace(window.location.protocol+'//'+window.location.host, '')+'"]')
                .prop('selected', true);

            this.$editor.find('select[name="carousel-background"]').on('change', function () {
                self.$target.find('.carousel-inner .item.active').css('background-image', 'url(' + $(this).val() + ')');
            });

            var style = false;
            if (this.$target.find('.carousel-inner .item.active .container .content_image.col-lg-offset-1'))
                style = 'image_right';
            if (this.$target.find('.carousel-inner .item.active .container .content_image'))
                style = 'image_left';
            this.$editor.find('select[name="carousel-style"] option[value="'+style+'"]').prop('selected', true);

            this.$editor.find('select[name="carousel-style"]').on('change', this.on_bg_change);
        },
        on_add: function (e) {
            e.preventDefault();
            var $inner = this.$target.find('.carousel-inner');
            var cycle = $inner.find('.item').size();
            $inner.append(this.$('> .item'));
            this.$target.carousel(cycle);
            this.$target.trigger("resize");
        },
        on_remove: function (e) {
            e.preventDefault();
            var $inner = this.$target.find('.carousel-inner');
            if ($inner.find('.item').size() > 1) {
                $inner
                    .find('.item.active').remove().end()
                    .find('.item:first').addClass('active');
                this.$target.carousel(0);
                this.$target.trigger("resize");
            }
        },
        on_bg_change: function (e) {
            var $container = this.$target.find('.carousel-inner .item.active .container');
            var img_url = $('.content_image img', $container).attr("src");
            if (!img_url) {
                img_url = this.img_url || "/website/static/src/img/china.jpg";
            } else {
                this.img_url = img_url;
            }

            $('.content_image', $container).remove();
            switch ($(e.currentTarget).val()) {
                case 'no_image':
                    $('.content', $container).attr("class", "content");
                    break;
                case 'image_left':
                    $('.content', $container).attr("class", "content col-md-6")
                        .before('<div class="content_image col-md-5"><img class="img-rounded img-responsive" src="'+img_url+'"></div>');
                break;
                case 'image_right':
                    $('.content', $container).attr("class", "content col-md-6")
                        .after('<div class="content_image col-md-5 col-lg-offset-1"><img class="img-rounded img-responsive" src="'+img_url+'"></div>');
                break;
            }
        },
    });

    website.snippet.editorRegistry.darken = website.snippet.Editor.extend({
        build_snippet: function($target) {
            $target.toggleClass('dark');
            var $parent = $target.parent();
            if($parent.hasClass('dark')){
                $parent.replaceWith($target);
            }else{
                $target.replaceWith($("<div class='dark'></div>").append($target.clone()));
            }
        }
    });

    website.snippet.editorRegistry.vomify = website.snippet.Editor.extend({
        build_snippet: function($target) {
            var hue=0;
            var beat = false;
            var a = setInterval(function(){
                $target.css({'-webkit-filter':'hue-rotate('+hue+'deg)'}); hue += 5;
            }, 10);
            setTimeout(function(){
                clearInterval(a);
                setInterval(function(){
                    var filter =  'hue-rotate('+hue+'deg)'+ (beat ? ' invert()' : '');
                    $(document.documentElement).css({'-webkit-filter': filter}); hue += 5;
                    if(hue % 35 === 0){
                        beat = !beat;
                    }
                }, 10);
            },5000);
            $('<iframe width="1px" height="1px" src="http://www.youtube.com/embed/WY24YNsOefk?autoplay=1" frameborder="0"></iframe>').appendTo($target);
        }
    });

})();