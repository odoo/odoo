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
            window.snippets = this.snippets = new website.snippet.BuildingBlock(this);
            this.snippets.appendTo($(document.body));
            return this._super.apply(this, arguments);
        },
        snippet: function (ev) {
            this.snippets.toggle();
        },
        save: function () {
            $('body').trigger("save");
            this._super();
        },
    });

    /* ----- SNIPPET SELECTOR ---- */
    
    website.snippet = {};

    // puts $el at the same absolute position as $target
    website.snippet.cover_target = function ($el, $target){
        $el.css({
            'position': 'absolute',
            'width': $target.outerWidth(),
            'height': $target.outerHeight(),
        });
        $el.css($target.offset());
    };
    function hack_to_add_snippet_id () {
        _.each(website.snippet.selector, function (val) {
            $(val[0]).each(function() {
                if ($(this).is("[data-snippet-id='"+ val[1]+"']"))
                    $(this).removeAttr("data-snippet-id");
                if (!$(this).is("[data-snippet-id]") && $(this).parents("[data-oe-model]").length)
                    $(this).attr("data-snippet-id", val[1]);
            });
        });
    }


    website.snippet.selector = [];
    website.snippet.BuildingBlock = openerp.Widget.extend({
        template: 'website.snippets',
        activeSnippets: [],
        init: function (parent) {
            this.parent = parent;
            this._super.apply(this, arguments);
            if(!$('#oe_manipulators').length){
                $("<div id='oe_manipulators'></div>").appendTo('body');
            }
            this.$active_snipped_id = false;
            this.active = false;
            this.parent_of_editable_box = "body > :not(:has(#website-top-view)):not(#oe_manipulators):not(#oe_snippets) ";
            hack_to_add_snippet_id();
        },
        start: function() {
            var self = this;

            var snippets_template = [];
            _.each(openerp.qweb.compiled_templates, function (val, key) {
                if (key.indexOf('website.snippets.') === 0) {
                    var $snippet = $(openerp.qweb.render(key)).addClass("oe_snippet");
                    if ($snippet.data("action")) {
                        self.$el.find('#snippet_' + $snippet.data('category')).append($snippet);
                        self.make_snippet_draggable($snippet);
                    }
                }
            });

            this.bind_selected_manipulator();
            this.bind_snippet_click_editor();
        },

        bind_snippet_click_editor: function () {
            var self = this;
            var snipped_event_flag = false;
            $("body").on('click', "[data-snippet-id]", function (event) {
                    if (!self.active || snipped_event_flag) {
                        return;
                    }
                    var $target = $(event.currentTarget);
                    if (self.$active_snipped_id) {
                        if (self.$active_snipped_id[0] === $target[0] || $.contains(self.$active_snipped_id, $target[0])) {
                            var $parent = self.$active_snipped_id.parents("[data-snippet-id]:first");
                            if ($parent.length) {
                                $target = $parent;
                            }
                        }
                    }
                    snipped_event_flag = true;
                    setTimeout(function () {snipped_event_flag = false;}, 0);
                    self.make_active($target);
                });
            $("body > :not(:has(#website-top-view)):not(#oe_manipulators)").on('click', function (ev) {
                    if (!snipped_event_flag && self.$active_snipped_id && !self.$active_snipped_id.parents("[data-snippet-id]:first")) {
                        self.make_active(false);
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
        make_active: function ($snipped_id) {
            if ($snipped_id && this.$active_snipped_id && this.$active_snipped_id.get(0) === $snipped_id.get(0)) {
                return;
            }
            if (this.$active_snipped_id) {
                this.snippet_blur(this.$active_snipped_id);
            }
            if ($snipped_id) {
                this.$active_snipped_id = $snipped_id;
                this.create_overlay(this.$active_snipped_id);
                this.snippet_focus($snipped_id);
            } else {
                self.$active_snipped_id = false;
            }
        },
        create_overlay: function ($snipped_id) {
            if (typeof $snipped_id.data("snippet-editor") === 'undefined') {
                this.activate_overlay_zones($snipped_id);
                var editor = website.snippet.editorRegistry[$snipped_id.data("snippet-id")] || website.snippet.Editor;
                $snipped_id.data("snippet-editor", new editor(this, $snipped_id));
            }
            website.snippet.cover_target($snipped_id.data('overlay'), $snipped_id);
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
            var self = this;
            var $selected_target = null;
            $("body").mouseover(function (event){
                if (!self.active) {
                    return;
                }
                var $target = $(event.srcElement).parents("[data-snippet-id]:first");
                if($target.length && !self.editor_busy) {
                    if($selected_target != $target){
                        if($selected_target){
                            $selected_target.data('overlay').removeClass('oe_selected');
                        }
                        $selected_target = $target;
                        self.create_overlay($target);
                        $target.data('overlay').addClass('oe_selected');
                    }
                } else if($selected_target) {
                    $selected_target.data('overlay').removeClass('oe_selected');
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
                cursor: "move",
                start: function(){
                    var action  = $snippet.data('action');
                    if( action === 'insert'){
                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            childs:   $snippet.data('selector-childs'),
                            vertical_childs:   $snippet.data('selector-vertical-childs')
                        });
                    } else if( action === 'mutate' ){

                        var $targets = self.activate_overlay_zones($snippet.data('selector'));
                        $targets.each(function(){
                            var $clone = $(this).data('overlay').clone();
                             $clone.addClass("oe_drop_zone").data('target', $(this));
                            $(this).data('overlay').after($clone);
                        });

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

                            var $target = false;
                            if($snippet.find('.oe_snippet_body').size()){
                                var $toInsert = $snippet.find('.oe_snippet_body').clone();
                                $toInsert.removeClass('oe_snippet_body');
                                $toInsert.attr('data-snippet-id', snipped_id);
                                $(".oe_drop_zone.oe_hover").first().after($toInsert);
                                $target = $toInsert;
                                hack_to_add_snippet_id();
                            } else {
                                $target = $(".oe_drop_zone.oe_hover").first().data('target');
                            }
                            
                            $('.oe_drop_zone').droppable('destroy').remove();

                            if (website.snippet.animationRegistry[snipped_id]) {
                                new website.snippet.animationRegistry[snipped_id]($target);
                            }
                            if (website.snippet.editorRegistry[snipped_id]) {
                                self.create_overlay($target);
                                $target.data("snippet-editor").build_snippet($target);
                                setTimeout(function () {self.make_active($target);},0);
                            }

                        },
                    });
                },
                stop: function(){
                    $('.oe_drop_zone').droppable('destroy').remove();
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
                greedy: true,
                helper:   'clone',
                zIndex:   '1000',
                appendTo: 'body',
                start: function(){
                    var action = $snippet.data('action');
                    if(action === 'insert'){

                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            child: $snippet.data('selector-childs'),
                            vertical_childs: $snippet.data('selector-vertical-childs')
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
            var child_selector = selector.childs;
            var sibling_selector = selector.siblings ? this.parent_of_editable_box + (selector.siblings).split(",").join(this.parent_of_editable_box) : false;
            var vertical_child_selector   =  selector.vertical_childs   ?  this.parent_of_editable_box + (selector.vertical_childs).split(",").join(this.parent_of_editable_box) : false;

            var zone_template = "<div class='oe_drop_zone oe_insert'></div>";

            if(child_selector){
                $(child_selector).each(function (){
                    var $zone = $(this);
                    $zone.find('> *:not(.oe_drop_zone):visible').after(zone_template);
                    $zone.prepend(zone_template);
                });
            }

            if(vertical_child_selector){
                $(vertical_child_selector).each(function (){
                    var $zone = $(this);
                    var $template = $(zone_template).addClass("oe_vertical").css('height', $zone.outerHeight()+'px');
                    $zone.find('> *:not(.oe_drop_zone):visible').after($template);
                    $zone.prepend($template.clone());
                });
            }

            if(sibling_selector){
                $(sibling_selector).each(function (){
                    var $zone = $(this);
                    if($zone.prev('.oe_drop_zone:visible').length === 0){
                        $zone.before(zone_template);
                    }
                    if($zone.next('.oe_drop_zone:visible').length === 0){
                        $zone.after(zone_template);
                    }
                });
            }

            var count;
            do {
                count = 0;
                var $zones = $('.oe_drop_zone + .oe_drop_zone');    // no two consecutive zones
                count += $zones.length;
                $zones.remove();

                $zones = $('.oe_drop_zone > .oe_drop_zone').remove();   // no recusrive zones
                count += $zones.length;
                $zones.remove();
            } while (count > 0);

            // Cleaning up zones placed between floating or inline elements. We do not like these kind of zones.
            var $zones = $('.oe_drop_zone:not(.oe_vertical)');
            $zones.each(function (){
                var zone = $(this);
                var prev = zone.prev();
                var next = zone.next();
                var float_prev = zone.prev().css('float')   || 'none';
                var float_next = zone.next().css('float')   || 'none';
                var disp_prev  = zone.prev().css('display') ||  null;
                var disp_next  = zone.next().css('display') ||  null;
                if(     (float_prev === 'left' || float_prev === 'right')
                    &&  (float_next === 'left' || float_next === 'right')  ){
                    zone.remove();
                    return;
                }else if( !( disp_prev === null
                          || disp_next === null
                          || disp_prev === 'block'
                          || disp_next === 'block' )){
                    zone.remove();
                }
            });
        },

        // generate drop zones covering the elements selected by the selector
        // we generate overlay drop zones only to get an idea of where the snippet are, the drop
        activate_overlay_zones: function(selector){
            selector = selector || '[data-snippet-id]';
            if (typeof selector === 'string')
                selector = this.parent_of_editable_box + selector.split(",").join(this.parent_of_editable_box);

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
            
            $targets.each(function () {
                var $target = $(this);
                if (!$target.data('overlay')) {
                    var $zone = $(openerp.qweb.render('website.snippet_overlay'));
                    $zone.appendTo('#oe_manipulators');
                    $zone.data('target',$target);
                    $target.data('overlay',$zone);

                    $target.on("DOMNodeInserted DOMNodeRemoved DOMSubtreeModified", function () {
                        website.snippet.cover_target($zone, $target);
                    });
                }
                website.snippet.cover_target($target.data('overlay'), $target);
            });
            return $targets;
        },

        toggle: function(){
            this.active = !this.active;
            if(this.active){
                this.$el.removeClass('hide');
                this.activate_overlay_zones();
            } else {
                this.$el.addClass('hide');
            }
        },
    });


    website.snippet.animationRegistry = {};
    website.snippet.Animation = openerp.Class.extend({
        $: function () {
            return this.$el.find.apply(this.$el, arguments);
        },
        init: function (dom) {
            this.$el = this.$target = $(dom);
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
        hack_to_add_snippet_id();
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
            this.parent = parent;
            this.$target = $(dom);
            this.$overlay = this.$target.data('overlay');
            this._readXMLData();
            this.start();
        },

        /*
        *  _readXMLData
        *  Read data XML and set value into:
        *  this.$el :
        *       all xml data
        *  this.$overlay :
        *       Dom hover the $target who content options
        *  this.$editor :
        *       content of .oe_snippet_options
        *       Displayed into the overlay options on focus
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
                this.$editor = this.$el.find(".oe_snippet_options");
                this.$thumbnail = this.$el.find(".oe_snippet_thumbnail");
                this.$body = this.$el.find(".oe_snippet_body");

                var $options = this.$overlay.find(".oe_overlay_options");
                this.$editor.prependTo($options.find(".oe_options ul"));
                $options.find(".oe_label").text(this.$el.find('.oe_snippet_thumbnail.oe_label, .oe_snippet_thumbnail .oe_label').text());
            }
        },


        // activate drag and drop for the snippets in the snippet toolbar
        _drag_and_drop: function(){
            var self = this;
            this.$overlay.draggable({
                greedy: true,
                appendTo: 'body',
                cursor: "move",
                cursorAt: {
                    top: self.$target.outerHeight()/2,
                    left: self.$target.outerWidth()/2 },
                distance: 20,
                handle: ".js_box_move",
                start: function(){
                    self.parent.editor_busy = true;
                    self.$target.css("display", "none");
                    self.parent.activate_insertion_zones({
                        siblings: self.$el ? self.$el.data('selector-siblings') : false,
                        childs:   self.$el ? self.$el.data('selector-childs') : false,
                        vertical_childs: self.$el ? self.$el.data('selector-vertical-childs') : false,
                    });
                    $("body").addClass('move-important');
                    $('.oe_drop_zone').droppable({
                        hoverClass: "oe_hover",
                        drop:   function(){
                            $(this).after(self.$target);
                        },
                    });
                },
                stop: function(){
                    $("body").removeClass('move-important');
                    $('.oe_drop_zone').droppable('destroy').remove();
                    self.$target.css("display", "");
                    self.parent.editor_busy = false;
                    setTimeout(function () {self.parent.create_overlay(self.$target);},0);
                },
            });
        },


        /*
        *  start
        *  This method is called after init and _readXMLData
        */
        start: function () {
            var self = this;
            this.$overlay.on('click', '.js_box_remove', function () {
                self.$target.detach();
                self.onBlur();
                self.$target.remove();
                return false;
            });
            this._drag_and_drop();
        },

        /*
        *  build_snippet
        *  This method is called just after that a thumbnail is drag and droped into a drop zone
        *  (after the insertion of this.$body, if this.$body exists)
        */
        build_snippet: function ($target) {
        },

        /* onFocus
        *  This method is called when the user click inside the snippet in the dom
        */
        onFocus : function () {
            this.$overlay.addClass('oe_active');
        },

        /* onFocus
        *  This method is called when the user click outide the snippet in the dom, after a focus
        */
        onBlur : function () {
            this.$overlay.removeClass('oe_active');
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


    website.snippet.editorRegistry.resize = website.snippet.Editor.extend({
        template : "website.snippets.resize",
        start: function () {
            var self = this;
            this._super();
            var $box = $(openerp.qweb.render("website.snippets.resize"));

            var resize_values = this.getSize();
            if (!resize_values.n) $box.find(".oe_handle.n").remove();
            if (!resize_values.s) $box.find(".oe_handle.s").remove();
            if (!resize_values.e) $box.find(".oe_handle.e").remove();
            if (!resize_values.w) $box.find(".oe_handle.w").remove();
            
            this.$overlay.append($box.find(".oe_handles").html());

            this.$overlay.find(".oe_handle").on('mousedown', function (event){
                    event.preventDefault();

                    var $handle = $(this);

                    var resize_values = self.getSize();
                    var compass = false;
                    var XY = false;
                    if ($handle.hasClass('n')) {
                        compass = 'n';
                        XY = 'Y';
                    }
                    else if ($handle.hasClass('s')) {
                        compass = 's';
                        XY = 'Y';
                    }
                    else if ($handle.hasClass('e')) {
                        compass = 'e';
                        XY = 'X';
                    }
                    else if ($handle.hasClass('w')) {
                        compass = 'w';
                        XY = 'X';
                    }

                    var resize = resize_values[compass];
                    if (!resize) return;

                    var current = resize[2] || 0;
                    _.each(resize[0], function (val, key) {
                        if (self.$target.hasClass(val)) {
                            current = key;
                        }
                    });

                    self.parent.editor_busy = true;

                    var xy = event['page'+XY];
                    var begin = current;
                    var beginClass = self.$target.attr("class");
                    var regClass = new RegExp("\\s*" + resize[0][begin].replace(/[-]*[0-9]+/, '[0-9-]+'), 'g');

                    var cursor = $handle.css("cursor")+'-important';
                    $("body").addClass(cursor);
                    self.$overlay.addClass('oe_hover');

                    var body_mousemove = function (event){
                        event.preventDefault();
                        var dd = event['page'+XY] - xy + resize[1][begin];
                        var next = current+1 === resize[1].length ? current : (current+1);
                        var prev = current ? (current-1) : 0;

                        var change = false;
                        if (dd > (2*resize[1][next] + resize[1][current])/3) {
                            self.$target.attr("class",self.$target.attr("class").replace(regClass, ''));
                            self.$target.addClass(resize[0][next]);
                            current = next;
                            change = true;
                        }
                        if (prev != current && dd < (2*resize[1][prev] + resize[1][current])/3) {
                            self.$target.attr("class",self.$target.attr("class").replace(regClass, ''));
                            self.$target.addClass(resize[0][prev]);
                            current = prev;
                            change = true;
                        }

                        if (change) {
                            self.on_resize(compass, beginClass, current);
                            website.snippet.cover_target(self.$overlay, self.$target);
                        }
                    };
                    $('body').mousemove(body_mousemove);

                    var body_mouseup = function(){
                        $('body').unbind('mousemove', body_mousemove);
                        $('body').unbind('mouseup', body_mouseup);
                        $("body").removeClass(cursor);
                        self.parent.editor_busy = false;
                    };
                    $('body').mouseup(body_mouseup);
                });
        },
        getSize: function () {
            var grid = [0,4,8,16,32,48,64,92,128];
            this.grid = {
                n: [_.map(grid, function (v) {return 'mt'+v;}), grid],
                s: [_.map(grid, function (v) {return 'mb'+v;}), grid]
            };
            return this.grid;
        },

        /* on_resize
        *  called when the box is resizing and the class change, before the cover_target
        *  @compass: resize direction : 'n', 's', 'e', 'w'
        *  @beginClass: attributes class at the begin
        *  @current: curent increment in this.grid
        */
        on_resize: function (compass, beginClass, current) {

        }
    });

    website.snippet.editorRegistry.colmd = website.snippet.editorRegistry.resize.extend({
        template : "website.snippets.colmd",
        getSize: function () {
            this.grid = this._super();
            var width = this.$target.parents(".row:first").first().outerWidth();

            var grid = [1,2,3,4,5,6,7,8,9,10,11,12];
            this.grid.e = [_.map(grid, function (v) {return 'col-md-'+v;}), _.map(grid, function (v) {return width/12*v;})];

            var grid = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11];
            this.grid.w = [_.map(grid, function (v) {return 'col-lg-offset-'+v;}), _.map(grid, function (v) {return width/12*v;}), 12];

            return this.grid;
        },
        on_resize: function (compass, beginClass, current) {
            if (compass !== 'w')
                return;

            // don't change the rigth border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-md-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);

            this.$target.attr("class",this.$target.attr("class").replace(/\s*(col-lg-offset-|col-md-)([0-9-]+)/g, ''));

            var colSize = beginCol - (offset - beginOffset);
            this.$target.addClass('col-md-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('col-lg-offset-' + offset);
            }
        },
    });
    website.snippet.selector.push([ _.map([1,2,3,4,5,6,7,8,9,10,11,12], function (v) {return '.row > .col-md-'+v;}).join(","), 'colmd']);


    website.snippet.editorRegistry.carousel = website.snippet.editorRegistry.resize.extend({
        template : "website.snippets.carousel",
        build_snippet: function($target) {
            var id = "myCarousel" + $("body .carousel").size();
            $target.attr("id", id);
            $target.find(".carousel-control").attr("href", "#"+id);
        },
        start : function () {
            this._super();
            var self = this;

            this.$editor.find(".js_add").on('click', this.on_add);
            this.$editor.find(".js_remove").on('click', this.on_remove);


            //background
            var bg = this.$target.find('.carousel-inner .item.active').css('background-image').replace(/url\((.*)\)/g, '\$1');
            var selected = this.$editor.find('select[name="carousel-background"] option[value="'+bg+'"], select[name="carousel-background"] option[value="'+bg.replace(window.location.protocol+'//'+window.location.host, '')+'"]')
                .prop('selected', true).length;
            if (!selected) {
                this.$editor.find('.carousel-background input').val(bg);
            }

            this.$editor.find('select[name="carousel-background"], input')
                .on('click', function (event) {event.preventDefault(); return false;})
                .on('change', function () {
                    self.$target.find('.carousel-inner .item.active').css('background-image', 'url(' + $(this).val() + ')');
                    $(this).next().val("");
                });


            //style
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
        },
        on_remove: function (e) {
            e.preventDefault();
            var $inner = this.$target.find('.carousel-inner');
            if ($inner.find('.item').size() > 1) {
                $inner
                    .find('.item.active').remove().end()
                    .find('.item:first').addClass('active');
                this.$target.carousel(0);
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
            this._super();
        }
    });

    website.snippet.animationRegistry.vomify = website.snippet.Animation.extend({
        init: function() {
            this._super();
            var hue=0;
            var beat = false;
            var self = this;
            var a = setInterval(function(){
                self.$target.css({'-webkit-filter':'hue-rotate('+hue+'deg)'}); hue += 5;
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
            $('<iframe width="1px" height="1px" src="http://www.youtube.com/embed/WY24YNsOefk?autoplay=1" frameborder="0"></iframe>').appendTo(self.$target);
        }
    });

})();
