(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.snippets.xml');

    website.EditorBar.include({
        start: function () {
            var self = this;
            $("[data-oe-model]").on('click', function (event) {
                var $this = $(event.srcElement);
                var tag = $this[0].tagName.toLowerCase();
                if (!(tag === 'a' || tag === "button") && !$this.parents("a, button").length) {
                    self.$('[data-action="edit"]').parent().effect('bounce', {distance: 18, times: 5}, 250);
                }
            });
            return this._super();
        },
        edit: function () {
            var self = this;
            $("body").off('click');
            window.snippets = this.snippets = new website.snippet.BuildingBlock(this);
            this.snippets.appendTo(this.$el);

            this.on('rte:ready', this, function () {
                self.snippets.$button.removeClass("hidden");
                website.snippet.stop_animation();
                website.snippet.start_animation();
                self.trigger('tour:editor_bar_loaded');
            });

            return this._super.apply(this, arguments);
        },
        save: function () {
            this.snippets.make_active(false);

            // FIXME: call clean_for_save on all snippets of the page, not only modified ones
            // important for banner of parallax that changes data automatically.
            this.snippets.clean_for_save();
            remove_added_snippet_id();
            this._super();
        },
    });

    /* ----- SNIPPET SELECTOR ---- */

    var observer = new website.Observer(function (mutations) {
        if (!_(mutations).find(function (m) {
                    return m.type === 'childList' && m.addedNodes.length > 0;
                })) {
            return;
        }
        hack_to_add_snippet_id()
    });

    // puts $el at the same absolute position as $target
    function hack_to_add_snippet_id () {
        _.each(website.snippet.selector, function (val) {
            $(val[0]).each(function() {
                if (!$(this).is("[data-snippet-id]") && $(this).parents("[data-oe-model]").length) {
                    $(this).attr("data-snippet-id", val[1]);
                }
            });
        });
    }
    function remove_added_snippet_id () {
        _.each(website.snippet.selector, function (val) {
            $(val[0]).each(function() {
                if ($(this).data("snippet-id") === val[1]) {
                    $(this).removeAttr("data-snippet-id");
                }
            });
        });
    }

    $(document).ready(function() {
        hack_to_add_snippet_id();
    });

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
            hack_to_add_snippet_id();
            this.snippets = [];

            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
        },
        dom_filter: function (dom, sibling) {
            if (typeof dom === "string") {
                var include = "[data-oe-model]";
                var sdom = dom.split(',');
                dom = "";
                _.each(sdom, function (val) {
                    val = val.replace(/^\s+|\s+$/g, '');
                    dom += include + " " + val + ", ";
                    if (!sibling) {
                        val = val.split(" ");
                        dom += val.shift() + include + val.join(" ") + ", ";
                    }
                });
                dom = dom.replace(/,\s*$/g, '');
                return $(dom);
            } else {
                return (!sibling && $(dom).is("[data-oe-model]")) || $(dom).parents("[data-oe-model]").length ? $(dom) : $("");
            }
        },
        start: function() {
            var self = this;

            this.$button = $(openerp.qweb.render('website.snippets_button'))
                .prependTo(this.parent.$("#website-top-edit ul"))
                .find("button");

            this.$button.click(function () {
                self.make_active(false);
                self.$el.toggleClass("hidden");
            });

            this.fetch_snippet_templates();

            this.bind_snippet_click_editor();

            this.$el.addClass("hidden");

            this.$modal = $(openerp.qweb.render('website.snippets_modal'));
            this.$modal.appendTo("body");
        },
        fetch_snippet_templates: function () {
            var self = this;
            this.style_templates = {};

            openerp.jsonRpc("/website/snippets", 'call', {})
                .then(function (html) {
                    var $html = $(html);

                    var $styles = $html.find("#snippet_styles");
                    $styles.find("> [data-snippet-id]").each(function () {
                        var $style = $(this);
                        var snipped_id = $style.data('snippet-id');
                        self.style_templates[snipped_id] = {
                            'snipped-id' : snipped_id,
                            'selector': $style.data('selector'),
                            'class': $style.find(".oe_snippet_class").text(),
                            'label': $style.find(".oe_snippet_label").text()
                        };
                    });
                    $styles.remove();

                    self.$snippets = $html.find(".tab-content > div > div").addClass("oe_snippet");
                    self.$el.append($html);

                    self.make_snippet_draggable(self.$snippets);
                });
        },
        cover_target: function ($el, $target){
            var pos = $target.offset();
            var mt = parseInt($target.css("margin-top") || 0);
            var mb = parseInt($target.css("margin-bottom") || 0);
            $el.css({
                'position': 'absolute',
                'width': $target.outerWidth(),
                'height': $target.outerHeight() + mt + mb,
                'top': pos.top - mt,
                'left': pos.left
            });
        },
        show: function () {
            this.$el.removeClass("hidden");
        },
        hide: function () {
            this.$el.addClass("hidden");
        },

        bind_snippet_click_editor: function () {
            var self = this;
            var snipped_event_flag = false;
            $("body").on('click', "[data-oe-model] [data-snippet-id], [data-oe-model][data-snippet-id]", function (event) {
                    if (snipped_event_flag) {
                        return;
                    }
                    snipped_event_flag = true;
                    setTimeout(function () {snipped_event_flag = false;}, 0);
                    var $target = $(event.currentTarget);
                    if (self.$active_snipped_id && self.$active_snipped_id.is($target)) {
                        return;
                    }
                    self.make_active($target);
                });
            $("[data-oe-model]").on('click', function () {
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
            }
        },
        snippet_focus: function ($snipped_id) {
            if ($snipped_id) {
                if ($snipped_id.data("snippet-editor")) {
                    $snipped_id.data("snippet-editor").onFocus();
                }
            }
        },
        clean_for_save: function () {
            for (var k in this.snippets) {
                if (!this.snippets.hasOwnProperty(k)) { continue; }
                var editor = $(this.snippets[k]).data("snippet-editor");
                if (editor) {
                    editor.clean_for_save();
                }
            }
        },
        make_active: function ($snipped_id) {
            if ($snipped_id && this.$active_snipped_id && this.$active_snipped_id.get(0) === $snipped_id.get(0)) {
                return;
            }
            if (this.$active_snipped_id) {
                this.snippet_blur(this.$active_snipped_id);
                this.$active_snipped_id = false;
            }
            if ($snipped_id) {
                if(_.indexOf(this.snippets, $snipped_id.get(0)) === -1) {
                    this.snippets.push($snipped_id.get(0));
                }
                this.$active_snipped_id = $snipped_id;
                this.create_overlay(this.$active_snipped_id);
                this.snippet_focus($snipped_id);
            }
        },
        create_overlay: function ($snipped_id) {
            if (typeof $snipped_id.data("snippet-editor") === 'undefined') {
                var $targets = this.activate_overlay_zones($snipped_id);
                if (!$targets.length) return;
                var editor = website.snippet.editorRegistry[$snipped_id.data("snippet-id")] || website.snippet.editorRegistry.resize;
                $snipped_id.data("snippet-editor", new editor(this, $snipped_id));
            }
            this.cover_target($snipped_id.data('overlay'), $snipped_id);
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
        make_snippet_draggable: function($snippets){
            var self = this;
            var $tumb = $snippets.find(".oe_snippet_thumbnail:first");
            var left = $tumb.outerWidth()/2;
            var top = $tumb.outerHeight()/2;
            var $toInsert, dropped, $snippet, action, snipped_id;

            $snippets.draggable({
                greedy: true,
                helper: 'clone',
                zIndex: '1000',
                appendTo: 'body',
                cursor: "move",
                handle: ".oe_snippet_thumbnail",
                cursorAt: {
                    'left': left,
                    'top': top
                },
                start: function(){
                    self.hide();
                    dropped = false;
                    $snippet = $(this);
                    snipped_id = $snippet.data('snippet-id');
                    action = $snippet.find('.oe_snippet_body').size() ? 'insert' : 'mutate';
                    if( action === 'insert'){
                        if (!$snippet.data('selector-siblings') && !$snippet.data('selector-children') && !$snippet.data('selector-vertical-children')) {
                            console.debug($snippet.data("snippet-id") + " have oe_snippet_body class and have not for insert action"+
                                "data-selector-siblings, data-selector-children or data-selector-vertical-children tag for mutate action");
                            return;
                        }
                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            children:   $snippet.data('selector-children'),
                            vertical_children:   $snippet.data('selector-vertical-children')
                        });

                        $toInsert = $snippet.find('.oe_snippet_body').clone();
                        $toInsert.removeClass('oe_snippet_body');
                        $toInsert.attr('data-snippet-id', snipped_id);

                    } else if( action === 'mutate' ){
                        if (!$snippet.data('selector')) {
                            console.debug($snippet.data("snippet-id") + " have not oe_snippet_body class and have not data-selector tag");
                            return;
                        }
                        var $targets = self.activate_overlay_zones($snippet.data('selector'));
                        $targets.each(function(){
                            var $clone = $(this).data('overlay').clone();
                             $clone.addClass("oe_drop_zone").data('target', $(this));
                            $(this).data('overlay').after($clone);
                        });

                    }

                    $('.oe_drop_zone').droppable({
                        over:   function(){
                            if( action === 'insert'){
                                dropped = true;
                                $(this).first().after($toInsert);
                            }
                        },
                        out:    function(){
                            if( action === 'insert'){
                                dropped = false;
                                $toInsert.detach();
                            }
                        },
                        drop:   function(){
                            dropped = true;
                        },
                    });
                },
                stop: function(ev, ui){
                    if (action === 'insert' && ! dropped && $('.oe_drop_zone')) {
                        var el = $('.oe_drop_zone').nearest({x: ui.position.left, y: ui.position.top}).first();
                        if (el.length) {
                            el.after($toInsert);
                            dropped = true;
                        }
                    }

                    $('.oe_drop_zone').droppable('destroy').remove();
                    if (dropped) {
                        var $target = false;
                        if(action === 'insert'){
                            $target = $toInsert;

                            website.snippet.start_animation();

                            self.create_overlay($target);
                            $target.data("snippet-editor").drop_and_build_snippet($target);

                        } else {
                            $target = $(this).data('target');

                            self.create_overlay($target);
                            if (website.snippet.editorRegistry[snipped_id]) {
                                var snippet = new website.snippet.editorRegistry[snipped_id](self, $target);
                                snippet.drop_and_build_snippet($target);
                            }
                        }
                        setTimeout(function () {self.make_active($target);},0);
                    } else {
                        $toInsert.remove();
                        if (self.$modal.find('input:not(:checked)').length) {
                            self.$modal.modal('toggle');
                        }
                    }
                },
            });
        },

        // return the original snippet in the editor bar from a snippet id (string)
        get_snippet_from_id: function(id){
            return $('.oe_snippet').filter(function(){
                    return $(this).data('snippet-id') === id;
                }).first();
        },

        // Create element insertion drop zones. two css selectors can be provided
        // selector.children -> will insert drop zones as direct child of the selected elements
        //   in case the selected elements have children themselves, dropzones will be interleaved
        //   with them.
        // selector.siblings -> will insert drop zones after and before selected elements
        activate_insertion_zones: function(selector){
            var self = this;
            var child_selector = selector.children;
            var sibling_selector = selector.siblings;
            var vertical_child_selector   =  selector.vertical_children;

            var zone_template = "<div class='oe_drop_zone oe_insert'></div>";

            if(child_selector){
                self.dom_filter(child_selector).each(function (){
                    var $zone = $(this);
                    $zone.find('> *:not(.oe_drop_zone):visible').after(zone_template);
                    $zone.prepend(zone_template);
                });
            }

            if(vertical_child_selector){
                self.dom_filter(vertical_child_selector).each(function (){
                    var $zone = $(this);
                    var $template = $(zone_template).addClass("oe_vertical");
                    var nb = 0;
                    var $lastinsert = false;
                    var left = 0;
                    var temp_left = 0;
                    $zone.find('> *:not(.oe_drop_zone):visible').each(function () {
                        var $col = $(this);
                        $template.css('height', ($col.outerHeight() + parseInt($col.css("margin-top")) + parseInt($col.css("margin-bottom")))+'px');
                        $lastinsert = $template.clone();
                        $(this).after($lastinsert);

                        temp_left = $col.position().left;
                        if (left === temp_left) {
                            $col.prev(".oe_drop_zone.oe_vertical").remove();
                            $col.before($template.clone().css("clear", "left"));
                        }
                        else if (!nb) {
                            $col.before($template.clone());
                        }
                        left = temp_left;
                        nb ++;
                    });
                    if (!nb) {
                        $zone.prepend($template.css('height', $zone.outerHeight()+'px'));
                    }
                });
            }

            if(sibling_selector){
                self.dom_filter(sibling_selector, true).each(function (){
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
                // var $zones = $('.oe_drop_zone + .oe_drop_zone');    // no two consecutive zones
                // count += $zones.length;
                // $zones.remove();

                $zones = $('.oe_drop_zone > .oe_drop_zone:not(.oe_vertical)').remove();   // no recursive zones
                count += $zones.length;
                $zones.remove();
            } while (count > 0);

            // Cleaning up zones placed between floating or inline elements. We do not like these kind of zones.
            var $zones = $('.oe_drop_zone:not(.oe_vertical)');
            $zones.each(function (){
                var zone = $(this);
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
            });
        },

        // generate drop zones covering the elements selected by the selector
        // we generate overlay drop zones only to get an idea of where the snippet are, the drop
        activate_overlay_zones: function(selector){
            var $targets = this.dom_filter(selector || '[data-snippet-id]');
            var self = this;

            if (typeof selector !== 'string' && !$targets.length) {
                console.debug( "A good node must have a [data-oe-model] attribute or must have at least one parent with [data-oe-model] attribute.");
                console.debug( "Wrong node(s): ", selector);
            }

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
                        self.cover_target($zone, $target);
                    });
                    $('body').on("resize", function () {
                        self.cover_target($zone, $target);
                    });
                }
                self.cover_target($target.data('overlay'), $target);
            });
            return $targets;
        }
    });


    website.snippet.editorRegistry = {};
    website.snippet.Editor = openerp.Class.extend({
        init: function (parent, dom) {
            this.parent = parent;
            this.$target = $(dom);
            this.$overlay = this.$target.data('overlay');
            this.snippet_id = this.$target.data("snippet-id");
            this._readXMLData();
            this.load_style_options();
            this.get_parent_block();
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
        */
        _readXMLData: function() {
            var self = this;
            this.$el = this.parent.$snippets.filter(function () { return $(this).data("snippet-id") == self.snippet_id; }).clone();
            this.$editor = this.$el.find(".oe_snippet_options");
            var $options = this.$overlay.find(".oe_overlay_options");
            this.$editor.prependTo($options.find(".oe_options ul"));
            if ($options.find(".oe_options ul li").length) {
                $options.find(".oe_options").removeClass("hidden");
            }
        },


        // activate drag and drop for the snippets in the snippet toolbar
        _drag_and_drop: function(){
            var self = this;
            this.dropped = false;
            this.$overlay.draggable({
                greedy: true,
                appendTo: 'body',
                cursor: "move",
                handle: ".oe_snippet_move",
                cursorAt: {
                    left: 18,
                    top: 14
                },
                helper: function() {
                    var $clone = $(this).clone().css({width: "24px", height: "24px", border: 0});
                    $clone.find(".oe_overlay_options >:not(:contains(.oe_snippet_move)), .oe_handle").remove();
                    $clone.find(":not(.glyphicon)").css({position: 'absolute', top: 0, left: 0});
                    $clone.appendTo("body").removeClass("hidden");
                    return $clone;
                },
                start: _.bind(self._drag_and_drop_start, self),
                stop: _.bind(self._drag_and_drop_stop, self)
            });
        },
        _drag_and_drop_after_insert_dropzone: function (){},
        _drag_and_drop_active_drop_zone: function ($zones){
            var self = this;
            $zones.droppable({
                over:   function(){
                    $(".oe_drop_zone.hide").removeClass("hide");
                    $(this).addClass("hide").first().after(self.$target);
                    self.dropped = true;
                },
                out:    function(){
                    $(this).removeClass("hide");
                    self.$target.detach();
                    self.dropped = false;
                },
            });
        },
        _drag_and_drop_start: function (){
            var self = this;
            self.parent.hide();
            self.parent.editor_busy = true;
            self.size = {
                width: self.$target.width(),
                height: self.$target.height()
            };
            self.$target.after("<div class='oe_drop_clone' style='display: none;'/>");
            self.$target.detach();
            self.$overlay.addClass("hidden");

            self.parent.activate_insertion_zones({
                siblings: self.$el ? self.$el.data('selector-siblings') : false,
                children:   self.$el ? self.$el.data('selector-children') : false,
                vertical_children: self.$el ? self.$el.data('selector-vertical-children') : false,
            });

            $("body").addClass('move-important');

            self._drag_and_drop_after_insert_dropzone();
            self._drag_and_drop_active_drop_zone($('.oe_drop_zone'));
        },
        _drag_and_drop_stop: function (){
            var self = this;
            if (!self.dropped) {
                $(".oe_drop_clone").after(self.$target);
            }
            self.$overlay.removeClass("hidden");
            $("body").removeClass('move-important');
            $('.oe_drop_zone').droppable('destroy').remove();
            $(".oe_drop_clone, .oe_drop_to_remove").remove();
            self.parent.editor_busy = false;
            self.get_parent_block();
            setTimeout(function () {self.parent.create_overlay(self.$target);},0);
        },

        _clone: function () {
            var self = this;
            this.$overlay.on('click', '.oe_snippet_clone', function () {
                var $clone = self.$target.clone(false);
                self.$target.after($clone);
                return false;
            });
        },

        load_style_options: function () {
            var self = this;
            var $styles = this.$overlay.find('.oe_options');
            var $ul = $styles.find('ul:first');
            _.each(this.parent.style_templates, function (val) {
                if (!self.parent.dom_filter(val.selector).is(self.$target)) {
                    return;
                }
                var $li = $("<li class='oe_style'/>").data(val);
                $li.append($('<a/>').text(val.label));
                $ul.append($li);
                if (self.$target.hasClass( "oe_snippet_" + $li.data("snipped-id") )) {
                    $li.addClass("active");
                }
                $styles.removeClass("hidden");
            });
            $styles.on('click', 'li.oe_style a', _.bind(this.change_style, this));
        },
        change_style: function (event) {
            var $li = $(event.currentTarget).parent();
            var snipped_id = $li.data("snipped-id");
            var active = $li.hasClass("active");

            if (website.snippet.editorRegistry[snipped_id]) {
                var snippet = new website.snippet.editorRegistry[snipped_id](this, this.$target);
                snippet.drop_and_build_snippet(this.$target);
            }
            var _class = "oe_snippet_" + snipped_id + " " + ($li.data("class") || "");
            if (active) {
                this.$target.removeClass(_class);
            } else {
                this.$target.addClass(_class);
            }
            $li.toggleClass("active");
        },

        get_parent_block: function () {
            var self = this;
            var $button = this.$overlay.find('.oe_snippet_parent');
            var $parent = this.$target.parents("[data-snippet-id]:first");
            if ($parent.length) {
                $button.removeClass("hidden");
                $button.off("click").on('click', function (event) {
                    event.preventDefault();
                    setTimeout(function () {
                        self.parent.make_active($parent);
                    }, 0);
                });
            } else {
                $button.addClass("hidden");
            }
        },

        /*
        *  start
        *  This method is called after init and _readXMLData
        */
        start: function () {
            var self = this;
            this.$overlay.on('click', '.oe_snippet_remove', function () {
                self.onBlur();
                var index = _.indexOf(self.parent.snippets, self.$target.get(0));
                delete self.parent.snippets[index];
                self.$target.remove();
                self.$overlay.remove();
                return false;
            });
            this._drag_and_drop();
            this._clone();
        },

        /*
        *  drop_and_build_snippet
        *  This method is called just after that a thumbnail is drag and dropped into a drop zone
        *  (after the insertion of this.$body, if this.$body exists)
        */
        drop_and_build_snippet: function ($target) {
        },

        /* onFocus
        *  This method is called when the user click inside the snippet in the dom
        */
        onFocus : function () {
            this.$overlay.addClass('oe_active');
        },

        /* onFocus
        *  This method is called when the user click outside the snippet in the dom, after a focus
        */
        onBlur : function () {
            this.$overlay.removeClass('oe_active');
        },

        /* clean_for_save
        *  function called just before save vue
        */
        clean_for_save: function () {

        },

        change_background: function (bg, ul_options, callback) {
            var self = this;
            this.set_options_background(bg, ul_options);
            var $ul = this.$editor.find(ul_options);
            var bg_value = (typeof bg === 'string' ? this.$target.find(bg) : $(bg)).css("background-image").replace(/url\(['"]*|['"]*\)/g, "");

            // bind event on options
            var $li = $ul.find("li");
            $li.on('click', function (event) {
                    if ($(this).data("value")) {
                        $li.removeClass("active");
                        $(this).addClass("active");
                        self.$editor.find('input').val("");
                    } else {
                        var editor = new website.editor.ImageDialog();
                        editor.on('start', self, function (o) {o.url = bg_value;});
                        editor.on('save', self, function (o) {
                            var $bg = typeof bg === 'string' ? self.$target.find(bg) : $(bg);
                            $bg.css("background-image", "url(" + o.url + ")");
                        });
                        editor.appendTo($('body'));
                    }
                    if (callback) {
                        callback();
                    }
                })
                .on('mouseover', function (event) {
                    if ($(this).data("value")) {
                        var src = $(this).data("value");
                        var $bg = typeof bg === 'string' ? self.$target.find(bg) : $(bg);
                        $bg.css("background-image", "url(" + src + ")");
                    }
                })
                .on('mouseout', function (event) {
                    var src = $ul.find('li.active').data("value");
                    var $bg = typeof bg === 'string' ? self.$target.find(bg) : $(bg);
                    $bg.css("background-image", "url(" + src + ")");
                });
        },

        set_options_background: function (bg, ul_options) {
            var $ul = this.$editor.find(ul_options);
            var bg_value = (typeof bg === 'string' ? this.$target.find(bg) : $(bg)).css("background-image").replace(/url\(['"]*|['"]*\)/g, "");

            // select in ul options
            $ul.find("li").removeClass("active");
            var selected = $ul.find('[data-value="' + bg_value + '"], [data-value="' + bg_value.replace(/.*:\/\/[^\/]+/, '') + '"]');
            selected.addClass('active');
            if (!selected.length) {
                $ul.find('.oe_custom_bg b').html(bg_value);
            }
        },
    });


    website.snippet.editorRegistry.resize = website.snippet.Editor.extend({
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
                    var regClass = new RegExp("\\s*" + resize[0][begin].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');

                    var cursor = $handle.css("cursor")+'-important';
                    var $body = $(document.body);
                    $body.addClass(cursor);

                    var body_mousemove = function (event){
                        event.preventDefault();
                        var dd = event['page'+XY] - xy + resize[1][begin];
                        var next = current+1 === resize[1].length ? current : (current+1);
                        var prev = current ? (current-1) : 0;

                        var change = false;
                        if (dd > (2*resize[1][next] + resize[1][current])/3) {
                            self.$target.attr("class", (self.$target.attr("class")||'').replace(regClass, ''));
                            self.$target.addClass(resize[0][next]);
                            current = next;
                            change = true;
                        }
                        if (prev != current && dd < (2*resize[1][prev] + resize[1][current])/3) {
                            self.$target.attr("class", (self.$target.attr("class")||'').replace(regClass, ''));
                            self.$target.addClass(resize[0][prev]);
                            current = prev;
                            change = true;
                        }

                        if (change) {
                            self.on_resize(compass, beginClass, current);
                            self.parent.cover_target(self.$overlay, self.$target);
                        }
                    };

                    var body_mouseup = function(){
                        $body.unbind('mousemove', body_mousemove);
                        $body.unbind('mouseup', body_mouseup);
                        $body.removeClass(cursor);
                        self.parent.editor_busy = false;
                    };
                    $body.mousemove(body_mousemove);
                    $body.mouseup(body_mouseup);
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
        getSize: function () {
            this.grid = this._super();
            var width = this.$target.parents(".row:first").first().outerWidth();

            var grid = [1,2,3,4,5,6,7,8,9,10,11,12];
            this.grid.e = [_.map(grid, function (v) {return 'col-md-'+v;}), _.map(grid, function (v) {return width/12*v;})];

            var grid = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11];
            this.grid.w = [_.map(grid, function (v) {return 'col-md-offset-'+v;}), _.map(grid, function (v) {return width/12*v;}), 12];

            return this.grid;
        },

        _drag_and_drop_after_insert_dropzone: function(){
            var self = this;
            var $zones = $(".row:has(> .oe_drop_zone)").each(function () {
                var $row = $(this);
                var width = $row.innerWidth();
                var pos = 0;
                while (width > pos + self.size.width) {
                    var $last = $row.find("> .oe_drop_zone:last");
                    $last.each(function () {
                        pos = $(this).position().left;
                    });
                    if (width > pos + self.size.width) {
                        $row.append("<div class='col-md-1 oe_drop_to_remove'/>");
                        var $add_drop = $last.clone();
                        $row.append($add_drop);
                        self._drag_and_drop_active_drop_zone($add_drop);
                    }
                }
            });
        },
        _drag_and_drop_start: function () {
            this._super();
            this.$target.attr("class",this.$target.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-)([0-9-]+)/g, ''));
        },
        _drag_and_drop_stop: function () {
            this.$target.addClass("col-md-offset-" + this.$target.prevAll(".oe_drop_to_remove").length);
            this._super();
        },

        on_resize: function (compass, beginClass, current) {
            if (compass !== 'w')
                return;

            // don't change the right border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-md-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/col-md-offset-([0-9-]+)|$/)[1] || beginClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/col-md-offset-([0-9-]+)|$/)[1] || 0);
            if (offset < 0) {
                offset = 0;
            }
            var colSize = beginCol - (offset - beginOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = beginOffset + beginCol - 1;
            }
            this.$target.attr("class",this.$target.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-|col-md-)([0-9-]+)/g, ''));

            this.$target.addClass('col-md-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('col-md-offset-' + offset);
            }
        },
    });

    website.snippet.editorRegistry.carousel = website.snippet.editorRegistry.resize.extend({
        drop_and_build_snippet: function() {
            var id = 0;
            $("body .carousel").each(function () {
                var _id = +$(this).attr("id").replace(/^myCarousel/, '');
                if (id <= _id) {
                    id = _id + 1;
                }
            });
            this.$target.attr("id", "myCarousel" + id);
            this.$target.find(".carousel-control").attr("href", "#myCarousel" + id);
            this.$target.find("[data-target='#myCarousel']").attr("data-target", "#myCarousel" + id);

            this.rebind_event();
        },
        onFocus: function () {
            this._super();
            this.$target.carousel('pause');
        },
        onBlur: function () {
            this._super();
            this.$target.carousel('cycle');
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".item").removeClass("next prev left right");
            if(!this.$target.find(".item.active").length) {
                this.$target.find(".item:first").addClass("active");
            }
            this.$target.removeAttr('contentEditable')
                .find('.content, .carousel-image img')
                    .removeAttr('contentEditable');
        },
        start : function () {
            this._super();

            this.id = this.$target.attr("id");

            this.$inner = this.$target.find('.carousel-inner');
            this.$indicators = this.$target.find('.carousel-indicators');

            this.$editor.find(".js_add").on('click', _.bind(this.on_add, this));
            this.$editor.find(".js_remove").on('click', _.bind(this.on_remove, this));

            this.change_background(".item.active", 'ul[name="carousel-background"]');
            this.change_style();
            this.change_size();
            this.set_options_style();
            this.$target.carousel();

            var self = this;
            this.$target.on('slide.bs.carousel', function () {
                self.set_options_style();
                self.set_options_background(".item.active", 'ul[name="carousel-background"]');
                self.$target.carousel();
            });

            this.rebind_event();
        },
        // rebind event to active carousel on edit mode
        rebind_event: function () {
            var self = this;
            this.$target.off('click').on('click', '.carousel-control', function () {
                self.$target.carousel($(this).data('slide')); });
            this.$target.off('click').on('click', '.carousel-indicators [data-target]', function () {
                self.$target.carousel(+$(this).data('slide-to')); });

            this.$target.attr('contentEditable', 'false')
                .find('.content, .carousel-image img')
                    .attr('contentEditable', 'true');
        },
        on_add: function (e) {
            e.preventDefault();
            var cycle = this.$inner.find('.item').length;
            var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
            var index = $active.index();
            this.$target.find('.carousel-control, .carousel-indicators').removeClass("hidden");
            this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');

            var $clone = this.$el.find(".item.active").clone();
            var avtive_bg = $active.css("background-image").replace(/.*:\/\/[^\/]+|\)$/g, '');
            var bg = this.$editor.find('ul[name="carousel-background"] li:not([data-value="'+ avtive_bg +'"]):first').data("value");
            $clone.css("background-image", "url('"+ bg +"')");
            $clone.removeClass('active').insertAfter($active);
            this.$target.carousel().carousel(++index);
            this.rebind_event();
        },
        on_remove: function (e) {
            e.preventDefault();
            if (this.remove_process) {
                return;
            }
            var self = this;
            var new_index = 0;
            var cycle = this.$inner.find('.item').length - 1;
            var index = this.$inner.find('.item.active').index();
            
            if (cycle > 0) {
                this.remove_process = true;
                var $el = this.$inner.find('.item.active');
                self.$target.on('slid.bs.carousel', function (event) {
                    $el.remove();
                    self.$indicators.find("li:last").remove();
                    self.$target.off('slid.bs.carousel');
                    self.rebind_event();
                    self.remove_process = false;
                    if (cycle == 1) {
                        self.on_remove(e);
                    }
                });
                setTimeout(function () {
                    self.$target.carousel( index > 0 ? --index : cycle );
                }, 500);
            } else {
                this.$target.find('.carousel-control, .carousel-indicators').addClass("hidden");
            }
        },
        set_options_style: function () {
            var style = false;
            var $el = this.$inner.find('.item.active');
            var $ul = this.$editor.find('ul[name="carousel-style"]');

            if ($el.hasClass('text_only'))
                style = 'text_only';
            if ($el.hasClass('image_text'))
                style = 'image_text';
            if ($el.hasClass('text_image'))
                style = 'text_image';

            $ul.find('[data-value="' + style + '"]').addClass('active');
        },
        change_style: function () {
            var self = this;
            var $ul = this.$editor.find('ul[name="carousel-style"]');
            var $li = $ul.find("li");

            $li.on('click', function (event) {
                    $li.removeClass("active");
                    $(this).addClass("active");
                })
                .on('mouseover', function (event) {
                    var $el = self.$inner.find('.item.active');
                    $el.removeClass('image_text text_image text_only');
                    $el.addClass($(event.currentTarget).data("value"));
                })
                .on('mouseout', function (event) {
                    var $el = self.$inner.find('.item.active');
                    $el.removeClass('image_text text_image text_only');
                    $el.addClass($ul.find('li.active').data("value"));
                });
        },
        change_size: function () {
            var $el = this.$target;

            var size = 'oe_big';
            if (this.$target.hasClass('oe_small'))
                size = 'oe_small';
            else if (this.$target.hasClass('oe_medium'))
                size = 'oe_medium';

            var $ul = this.$editor.find('ul[name="carousel-size"]');
            var $li = $ul.find("li");

            $ul.find('[data-value="' + size + '"]').addClass('active');

            $li.on('click', function (event) {
                    $li.removeClass("active");
                    $(this).addClass("active");
                })
                .on('mouseover', function (event) {
                    $el.removeClass('oe_big oe_small oe_medium');
                    $el.addClass($(event.currentTarget).data("value"));
                })
                .on('mouseout', function (event) {
                    $el.removeClass('oe_big oe_small oe_medium');
                    $el.addClass($ul.find('li.active').data("value"));
                });
        }
    });

    website.snippet.editorRegistry.parallax = website.snippet.editorRegistry.resize.extend({
        start : function () {
            var self = this;
            this._super();
            this.change_background(this.$target, 'ul[name="parallax-background"]', function () {
                self.$target.data("snippet-view").set_values();
            });
            this.scroll();
            this.change_size();
        },
        scroll: function () {
            var self = this;
            var $ul = this.$editor.find('ul[name="parallax-scroll"]');
            var $li = $ul.find("li");
            var speed = this.$target.data('scroll-background-ratio') || 0.6 ;
            $ul.find('[data-value="' + speed + '"]').addClass('active');
            $li.on('click', function (event) {
                $li.removeClass("active");
                $(this).addClass("active");
                var speed =  $(this).data('value');
                self.$target.attr('data-scroll-background-ratio', speed);
                self.$target.data("snippet-view").set_values();
                return false;
            });
            this.$target.data("snippet-view").set_values();
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".parallax")
                .css("background-position", '')
                .removeAttr("data-scroll-background-offset");
        },
        change_size: function () {
            var self = this;

            var size = 'oe_big';
            if (this.$target.hasClass('oe_small'))
                size = 'oe_small';
            else if (this.$target.hasClass('oe_medium'))
                size = 'oe_medium';
            var $ul = this.$editor.find('ul[name="parallax-size"]');
            var $li = $ul.find("li");

            $ul.find('[data-value="' + size + '"]').addClass('active');

            $li.on('click', function (event) {
                    $li.removeClass("active");
                    $(this).addClass("active");
                    self.$target.data("snippet-view").set_values();
                    return false;
                })
                .on('mouseover', function (event) {
                    self.$target.removeClass('oe_big oe_small oe_medium');
                    self.$target.addClass($(event.currentTarget).data("value"));
                })
                .on('mouseout', function (event) {
                    self.$target.removeClass('oe_big oe_small oe_medium');
                    self.$target.addClass($ul.find('li.active').data("value"));
                });
        }
    });

    /*
    * data-snippet-id automatically setted
    * Don't need to add data-snippet-id="..." into the views
    */

    website.snippet.selector.push([".row > div[class*='col-md-']", 'colmd']);
    website.snippet.selector.push(['hr', 'hr']);

})();
