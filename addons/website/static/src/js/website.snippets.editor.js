(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.snippets.xml');

    website.EditorBar.include({
        start: function () {
            var self = this;
            $("[data-oe-model]").on('click', function (event) {
                var $this = $(event.srcElement);
                var tag = $this[0] && $this[0].tagName.toLowerCase();
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

    // 'snippet-dropped' is triggered on '#oe_snippets' whith $target as attribute when a snippet is dropped
    // 'snippet-activated' is triggered on '#oe_snippets' (and on snippet) when a snippet is activated

    if (!website.snippet) website.snippet = {};
    website.snippet.styles = {};
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
            $("#wrapwrap").click(function () {
                self.$el.addClass("hidden");
            });

            this.fetch_snippet_templates();

            this.bind_snippet_click_editor();

            this.$el.addClass("hidden");

            $(document).on('click', '.dropdown-submenu a[tabindex]', function (e) {
                e.preventDefault();
            });

            this.getParent().on('change:height', this, function (editor) {
                self.$el.css('top', editor.get('height'));
            });
            self.$el.css('top', this.parent.get('height'));
        },
        _get_snippet_url: function () {
            return '/website/snippets';
        },
        fetch_snippet_templates: function () {
            var self = this;

            openerp.jsonRpc(this._get_snippet_url(), 'call', {})
                .then(function (html) {
                    var $html = $(html);

                    var $styles = $html.find("[data-snippet-style-id]");
                    $styles.each(function () {
                        var $style = $(this);
                        var style_id = $style.data('snippet-style-id');
                        website.snippet.styles[style_id] = {
                            'snippet-style-id' : style_id,
                            'selector': $style.data('selector'),
                            '$el': $style,
                        };
                    });
                    $styles.addClass("hidden");

                    self.$snippets = $html.find(".tab-content > div > div").addClass("oe_snippet");
                    self.$el.append($html);


                    var snippets = 0;
                    self.$snippets.each(function () {
                        if (self.snippet_have_dropzone($(this)))
                            snippets++;
                    });
                    if (!snippets) self.$button.css("display", "none");

                    self.make_snippet_draggable(self.$snippets);
                });
        },
        cover_target: function ($el, $target){
            var pos = $target.offset();
            var mt = parseInt($target.css("margin-top") || 0);
            var mb = parseInt($target.css("margin-bottom") || 0);
            $el.css({
                'width': $target.outerWidth(),
                'top': pos.top - mt - 5,
                'left': pos.left
            });
            $el.find(">.e,>.w").css({'height': $target.outerHeight() + mt + mb+1});
            $el.find(">.s").css({'top': $target.outerHeight() + mt + mb});
            $el.find(">.size").css({'top': $target.outerHeight() + mt});
            $el.find(">.s,>.n").css({'width': $target.outerWidth()-2});
        },
        show: function () {
            this.$el.removeClass("hidden");
        },
        hide: function () {
            this.$el.addClass("hidden");
        },

        snippet_have_dropzone: function ($snippet) {
            return (($snippet.data('selector-siblings') && this.dom_filter($snippet.data('selector-siblings')).size() > 0) ||
                    ($snippet.data('selector-children') && this.dom_filter($snippet.data('selector-children')).size() > 0) ||
                    ($snippet.data('selector-vertical-children') && this.dom_filter($snippet.data('selector-vertical-children')).size() > 0));
        },

        bind_snippet_click_editor: function () {
            var self = this;
            $("#wrapwrap").on('click', function (event) {
                var $target = $(event.srcElement || event.target);
                if (!$target.attr("data-snippet-id")) {
                    $target = $target.parents("[data-snippet-id]:first");
                }
                if (!$target.attr("data-oe-model") && !$target.parents("[data-oe-model]:first").length) {
                    $target = false;
                }
                if (self.$active_snipped_id && self.$active_snipped_id.is($target)) {
                    return;
                }
                self.make_active($target);
            });
        },
        snippet_blur: function ($snippet) {
            if ($snippet) {
                if ($snippet.data("snippet-editor")) {
                    $snippet.data("snippet-editor").onBlur();
                }
            }
        },
        snippet_focus: function ($snippet) {
            if ($snippet) {
                if ($snippet.data("snippet-editor")) {
                    $snippet.data("snippet-editor").onFocus();
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
        make_active: function ($snippet) {
            if ($snippet && this.$active_snipped_id && this.$active_snipped_id.get(0) === $snippet.get(0)) {
                return;
            }
            if (this.$active_snipped_id) {
                this.snippet_blur(this.$active_snipped_id);
                this.$active_snipped_id = false;
            }
            if ($snippet && $snippet.length) {
                if(_.indexOf(this.snippets, $snippet.get(0)) === -1) {
                    this.snippets.push($snippet.get(0));
                }
                this.$active_snipped_id = $snippet;
                this.create_overlay(this.$active_snipped_id);
                this.snippet_focus($snippet);
            }
            $("#oe_snippets").trigger('snippet-activated', $snippet);
            if ($snippet) {
                $snippet.trigger('snippet-activated', $snippet);
            }
        },
        create_overlay: function ($snippet) {
            if (typeof $snippet.data("snippet-editor") === 'undefined') {
                var $targets = this.activate_overlay_zones($snippet);
                if (!$targets.length) return;
                var editor = website.snippet.editorRegistry[$snippet.data("snippet-id")] || website.snippet.editorRegistry.resize;
                $snippet.data("snippet-editor", new editor(this, $snippet));
            }
            this.cover_target($snippet.data('overlay'), $snippet);
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
                        $toInsert.data('src-snippet-id', snipped_id);
                        if (!$toInsert.data('snippet-id')) {
                            $toInsert.attr('data-snippet-id', snipped_id);
                        } else {
                            snipped_id = $toInsert.data('snippet-id');
                        }

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
                            var prev = $toInsert.prev();
                            if( action === 'insert' && this === prev[0]){
                                dropped = false;
                                $toInsert.detach();
                            }
                        }
                    });
                },
                stop: function(ev, ui){
                    if (action === 'insert' && ! dropped && $('.oe_drop_zone') && ui.position.top > 3) {
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

                            self.create_overlay($target);
                            if ($target.data("snippet-editor")) {
                                $target.data("snippet-editor").drop_and_build_snippet($target);
                            }

                            $target.find("[data-snippet-id]").each(function () {
                                var $snippet = $(this);
                                var snippet_id = $snippet.data("data-snippet-id");
                                self.create_overlay($snippet);
                                if ($snippet.data("snippet-editor")) {
                                    $snippet.data("snippet-editor").drop_and_build_snippet($snippet);
                                }
                            });

                        } else {
                            $target = $(this).data('target');

                            self.create_overlay($target);
                            if (website.snippet.editorRegistry[snipped_id]) {
                                var snippet = new website.snippet.editorRegistry[snipped_id](self, $target);
                                snippet.drop_and_build_snippet($target);
                            }
                        }
                        setTimeout(function () {
                            $("#oe_snippets").trigger('snippet-dropped', $target);

                            // reset snippet for rte
                            $target.removeData("snippet-editor");
                            if ($target.data("overlay")) {
                                $target.data("overlay").remove();
                                $target.removeData("overlay");
                            }
                            $target.find("[data-snippet-id]").each(function () {
                                var $snippet = $(this);
                                $snippet.removeData("snippet-editor");
                                if ($snippet.data("overlay")) {
                                    $snippet.data("overlay").remove();
                                    $snippet.removeData("overlay");
                                }
                            });
                            // end

                            self.create_overlay($target);
                            self.make_active($target);
                        },0);
                    } else {
                        $toInsert.remove();
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

                    // fix for pointer-events: none with ie9
                    if (document.body && document.body.addEventListener) {
                        $zone.on("click mousedown mousedown", function passThrough(event) {
                            event.preventDefault();
                            $target.each(function() {
                               // check if clicked point (taken from event) is inside element
                                event.srcElement = this;
                                $(this).trigger(event.type);
                            });
                            return false;
                        });
                    }

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


    website.snippet.styleRegistry = {};
    website.snippet.StyleEditor = openerp.Class.extend({
        // initialisation (don't overwrite)
        init: function (parent, $target, snippet_id) {
            this.parent = parent;
            this.$target = $target;
            var styles = this.$target.data("snippet-style-ids") || {};
            styles[snippet_id] = this;
            this.$target.data("snippet-style-ids", styles);
            this.$overlay = this.$target.data('overlay');
            this['snippet-style-id'] = snippet_id;
            this.$el = website.snippet.styles[snippet_id].$el.find(">li").clone();

            this.required = this.$el.data("required");

            this.set_active();
            this.$el.find('li[data-class] a').on('mouseover mouseout click', _.bind(this._mouse, this));
            this.$target.on('snippet-style-reset', _.bind(this.set_active, this));

            this.start();
        },
        _mouse: function (event) {
            var self = this;

            if (event.type === 'mouseout') {
                if (!this.over) return;
                this.over = false;
            } else if (event.type === 'click') {
                this.over = false;
            }else {
                this.over = true;
            }

            var $prev, $next;
            if (event.type === 'mouseout') {
                $prev = $(event.currentTarget).parent();
                $next = this.$el.find("li[data-class].active");
            } else {
                $prev = this.$el.find("li[data-class].active");
                $next = $(event.currentTarget).parent();
            }
            if (!$prev.length) {
                $prev = false;
            }
            if ($prev && $prev[0] === $next[0]) {
                $next = false;
                if (this.required) {
                    return;
                }
            }

            var np = {'$next': $next, '$prev': $prev};

            if (event.type === 'click') {
                setTimeout(function () {
                    self.set_active();
                    self.$target.trigger("snippet-style-change", [self, np]);
                },0);
                this.select(event, {'$next': $next, '$prev': $prev});
            } else {
                setTimeout(function () {
                    self.$target.trigger("snippet-style-preview", [self, np]);
                },0);
                this.preview(event, np);
            }
        },
        // start is call just after the init
        start: function () {
        },
        /* select
        *  called when a user select an item
        *  variables: np = {$next, $prev}
        *       $next is false if they are no next item selected
        *       $prev is false if they are no previous item selected
        */
        select: function (event, np) {
            var self = this;
            // add or remove html class
            if (np.$prev) {
                this.$target.removeClass(np.$prev.data('class' || ""));
            }
            if (np.$next) {
                this.$target.addClass(np.$next.data('class') || "");
            }
        },
        /* preview
        *  called when a user is on mouse over or mouse out of an item
        *  variables: np = {$next, $prev}
        *       $next is false if they are no next item selected
        *       $prev is false if they are no previous item selected
        */
        preview: function (event, np) {
            var self = this;

            // add or remove html class
            if (np.$prev) {
                this.$target.removeClass(np.$prev.data('class') || "");
            }
            if (np.$next) {
                this.$target.addClass(np.$next.data('class') || "");
            }
        },
        /* set_active
        *  select and set item active or not (add highlight item and his parents)
        *  called before start
        */
        set_active: function () {
            var self = this;
            this.$el.find('li').removeClass("active");
            var $active = this.$el.find('li[data-class]')
                .filter(function () {
                    var $li = $(this);
                    return  ($li.data('class') && self.$target.hasClass($li.data('class')));
                })
                .first()
                .addClass("active");
            this.$el.find('li:has(li[data-class].active)').addClass("active");
        }
    });


    website.snippet.styleRegistry.background = website.snippet.StyleEditor.extend({
        _get_bg: function () {
            return this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
        },
        _set_bg: function (src) {
            this.$target.css("background-image", src && src !== "" ? 'url(' + src + ')' : "");
        },
        start: function () {
            this._super();
            var src = this._get_bg();
            this.$el.find("li[data-class].active.oe_custom_bg").data("src", src);
        },
        select: function(event, np) {
            var self = this;
            this._super(event, np);
            if (np.$next) {
                if (np.$next.hasClass("oe_custom_bg")) {
                    var editor = new website.editor.ImageDialog();
                    editor.on('start', self, function (o) {o.url = np.$prev && np.$prev.data("src") || np.$next && np.$next.data("src") || "";});
                    editor.on('save', self, function (o) {
                        self._set_bg(o.url);
                        np.$next.data("src", o.url);
                        self.$target.trigger("snippet-style-change", [self, np]);
                    });
                    editor.on('cancel', self, function () {
                        if (!np.$prev || np.$prev.data("src") === "") {
                            self.$target.removeClass(np.$next.data("class"));
                            self.$target.trigger("snippet-style-change", [self, np]);
                        }
                    });
                    editor.appendTo($('body'));
                } else {
                    this._set_bg(np.$next.data("src"));
                }
            } else {
                this._set_bg(false);
                this.$target.removeClass(np.$prev.data("class"));
            }
        },
        preview: function (event, np) {
            this._super(event, np);
            if (np.$next) {
                this._set_bg(np.$next.data("src"));
            }
        },
        set_active: function () {
            var self = this;
            var bg = self.$target.css("background-image");
            this.$el.find('li').removeClass("active");
            this.$el.find('li').removeClass("btn-primary");
            var $active = this.$el.find('li[data-class]')
                .filter(function () {
                    var $li = $(this);
                    return  ($li.data('src') && bg.indexOf($li.data('src')) >= 0) ||
                            (!$li.data('src') && self.$target.hasClass($li.data('class')));
                })
                .first();
            if (!$active.length) {
                $active = this.$target.css("background-image") !== 'none' ?
                    this.$el.find('li[data-class].oe_custom_bg') :
                    this.$el.find('li[data-class=""]');
            }

            //don't set active on an OpenDialog link, else it not possible to click on it again after.
            // TODO in Saas-4 - Once bootstrap is in less
            //      - add a class active-style to get the same display but without the active behaviour used by bootstrap in JS.
            var classStr = _.string.contains($active[0].className, "oe_custom_bg") ? "btn-primary" : "active";
            $active.addClass(classStr);
            this.$el.find('li:has(li[data-class].active)').addClass(classStr);
        }
    });


    website.snippet.editorRegistry = {};
    website.snippet.Editor = openerp.Class.extend({
        init: function (parent, dom) {
            this.parent = parent;
            this.$target = $(dom);
            this.$overlay = this.$target.data('overlay');
            this.$overlay.find('a[data-toggle="dropdown"]').dropdown();
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

        load_style_options: function () {
            var self = this;
            var $styles = this.$overlay.find('.oe_options');
            var $ul = $styles.find('ul:first');
            _.each(website.snippet.styles, function (val) {
                if (!self.parent.dom_filter(val.selector).is(self.$target)) {
                    return;
                }
                var Editor = website.snippet.styleRegistry[val['snippet-style-id']] || website.snippet.StyleEditor;
                var editor = new Editor(self, self.$target, val['snippet-style-id']);
                $ul.prepend(editor.$el.addClass("snippet-style-" + val['snippet-style-id']));
            });

            if ($ul.find("li").length) {
                $styles.removeClass("hidden");
            }
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
            this.$overlay.on('click', '.oe_snippet_clone', _.bind(this.on_clone, this));
            this.$overlay.on('click', '.oe_snippet_remove', _.bind(this.on_remove, this));
            this._drag_and_drop();
        },

        on_clone: function () {
            var $clone = this.$target.clone(false);
            this.$target.after($clone);
            return false;
        },

        on_remove: function () {
            this.onBlur();
            var index = _.indexOf(this.parent.snippets, this.$target.get(0));
            delete this.parent.snippets[index];
            this.$target.remove();
            this.$overlay.remove();
            return false;
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
            this.$target.removeAttr('contentEditable')
                .find('*').removeAttr('contentEditable');
            this.$target.removeAttr('attributeEditable')
                .find('*').removeAttr('attributeEditable');
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
            if (!resize_values.size) $box.find(".oe_handle.size").remove();

            this.$overlay.append($box.find(".oe_handles").html());

            this.$overlay.find(".oe_handle:not(:has(.oe_handle_button)), .oe_handle .oe_handle_button").on('mousedown', function (event){
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
                else if ($handle.hasClass('size')) {
                    compass = 'size';
                    XY = 'Y';
                }

                var resize = resize_values[compass];
                if (!resize) return;


                if (compass === 'size') {
                    var offset = self.$target.offset().top;
                    if (self.$target.css("background").match(/rgba\(0, 0, 0, 0\)/)) {
                        self.$target.addClass("resize_editor_busy");
                    }
                } else {
                    var xy = event['page'+XY];
                    var current = resize[2] || 0;
                    _.each(resize[0], function (val, key) {
                        if (self.$target.hasClass(val)) {
                            current = key;
                        }
                    });
                    var begin = current;
                    var beginClass = self.$target.attr("class");
                    var regClass = new RegExp("\\s*" + resize[0][begin].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');
                }

                self.parent.editor_busy = true;

                var cursor = $handle.css("cursor")+'-important';
                var $body = $(document.body);
                $body.addClass(cursor);

                var body_mousemove = function (event){
                    event.preventDefault();
                    if (compass === 'size') {
                        var dy = event.pageY-offset;
                        dy = dy - dy%resize;
                        if (dy <= 0) dy = resize;
                        self.$target.css("height", dy+"px");
                        self.on_resize(compass, null, dy);
                        self.parent.cover_target(self.$overlay, self.$target);
                        return;
                    }
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
                    self.$target.removeClass("resize_editor_busy");
                };
                $body.mousemove(body_mousemove);
                $body.mouseup(body_mouseup);
            });
        },
        getSize: function () {
            var grid = [0,4,8,16,32,48,64,92,128];
            this.grid = {
                // list of class (Array), grid (Array), default value (INT)
                n: [_.map(grid, function (v) {return 'mt'+v;}), grid],
                s: [_.map(grid, function (v) {return 'mb'+v;}), grid],
                // INT if the user can resize the snippet (resizing per INT px)
                size: null
            };
            return this.grid;
        },

        onFocus : function () {
            this._super();
            this.change_cursor();
        },

        change_cursor : function () {
            var _class = this.$target.attr("class") || "";

            var col = _class.match(/col-md-([0-9-]+)/i);
            col = col ? +col[1] : 0;

            var offset = _class.match(/col-md-offset-([0-9-]+)/i);
            offset = offset ? +offset[1] : 0;

            var overlay_class = this.$overlay.attr("class").replace(/(^|\s+)block-[^\s]*/gi, '');
            if (col+offset >= 12) overlay_class+= " block-e-right";
            if (col === 1) overlay_class+= " block-w-right block-e-left";
            if (offset === 0) overlay_class+= " block-w-left";

            var mb = _class.match(/mb([0-9-]+)/i);
            mb = mb ? +mb[1] : 0;
            if (mb >= 128) overlay_class+= " block-s-bottom";
            else if (!mb) overlay_class+= " block-s-top";

            var mt = _class.match(/mt([0-9-]+)/i);
            mt = mt ? +mt[1] : 0;
            if (mt >= 128) overlay_class+= " block-n-top";
            else if (!mt) overlay_class+= " block-n-bottom";

            this.$overlay.attr("class", overlay_class);
        },
        
        /* on_resize
        *  called when the box is resizing and the class change, before the cover_target
        *  @compass: resize direction : 'n', 's', 'e', 'w'
        *  @beginClass: attributes class at the begin
        *  @current: curent increment in this.grid
        */
        on_resize: function (compass, beginClass, current) {
            this.change_cursor();
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
        hide_remove_button: function() {
            this.$overlay.find('.oe_snippet_remove').toggleClass("hidden",
                !this.$target.siblings().length && this.$target.parents("[data-snippet-id]:first").find("[data-snippet-id='colmd']").length > 1);
        },
        onFocus : function () {
            this._super();
            this.hide_remove_button();
        },
        on_clone: function () {
            var $clone = this.$target.clone(false);
            var _class = $clone.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-)([0-9-]+)/g, '');
            $clone.attr("class", _class);
            this.$target.after($clone);
            this.hide_remove_button();
            return false;
        },
        on_remove: function () {
            if (!this.$target.siblings().length) {
                var $parent = this.$target.parents("[data-snippet-id]:first");
                if($parent.find("[data-snippet-id='colmd']").length > 1) {
                    return false;
                } else {
                    if (!$parent.data("snippet-editor")) {
                        this.parent.create_overlay($parent);
                    }
                    $parent.data("snippet-editor").on_remove();
                }
            }
            this._super();
            this.hide_remove_button();
            return false;
        },
        on_resize: function (compass, beginClass, current) {
            if (compass === 'w') {
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
            }
            this._super(compass, beginClass, current);
        },
    });

    website.snippet.editorRegistry.slider = website.snippet.editorRegistry.resize.extend({
        getSize: function () {
            this.grid = this._super();
            this.grid.size = 8;
            return this.grid;
        },
        drop_and_build_snippet: function() {
            var id = $(".carousel").length;
            this.id = "myCarousel" + id;
            this.$target.attr("id", this.id);
            this.$target.find(".carousel-control").attr("href", "#myCarousel" + id);
            this.$target.find("[data-target]").attr("data-target", "#myCarousel" + id);

            this.rebind_event();
        },
        // rebind event to active carousel on edit mode
        rebind_event: function () {
            var self = this;
            this.$target.find('.carousel-indicators [data-target]').off('click').on('click', function () {
                self.$target.carousel(+$(this).data('slide-to')); });

            this.$target.attr('contentEditable', 'false');
            this.$target.find('.oe_structure, .content>.row').attr('contentEditable', 'true');
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".item").removeClass("next prev left right active");
            this.$indicators.find('li').removeClass('active');
            this.$indicators.find('li:first').addClass('active');
            if(!this.$target.find(".item.active").length) {
                this.$target.find(".item:first").addClass("active");
            }
        },
        start : function () {
            var self = this;
            this._super();
            this.$target.carousel({interval: false});
            this.id = this.$target.attr("id");
            this.$inner = this.$target.find('.carousel-inner');
            this.$indicators = this.$target.find('.carousel-indicators');

            this.$editor.find(".js_add").on('click', function () {self.on_add_slide(); return false;});
            this.$editor.find(".js_remove").on('click', function () {self.on_remove_slide(); return false;});

            this.rebind_event();
        },
        on_add_slide: function () {
            var self = this;
            var cycle = this.$inner.find('.item').length;
            var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
            var index = $active.index();
            this.$target.find('.carousel-control, .carousel-indicators').removeClass("hidden");
            this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');

            var $clone = this.$el.find(".item.active").clone();

            // insert
            $clone.removeClass('active').insertAfter($active);
            setTimeout(function() {
                self.$target.carousel().carousel(++index);
                self.rebind_event();
            },0);
            return $clone;
        },
        on_remove_slide: function () {
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
                        self.on_remove_slide(event);
                    }
                });
                setTimeout(function () {
                    self.$target.carousel( index > 0 ? --index : cycle );
                }, 500);
            } else {
                this.$target.find('.carousel-control, .carousel-indicators').addClass("hidden");
            }
        },
    });

    website.snippet.editorRegistry.carousel = website.snippet.editorRegistry.slider.extend({
        clean_for_save: function () {
            this._super();
            this.$target.css("background-image", "");
            this.$target.removeClass(this._class);
        },
        load_style_options : function () {
            this._super();
            $(".snippet-style-size li[data-class='']").remove();
        },
        start : function () {
            var self = this;
            this._super();

            // set background and prepare to clean for save
            var add_class = function (c){
                if (c) self._class = (self._class || "").replace(new RegExp("[ ]+" + c.replace(" ", "|[ ]+")), '') + ' ' + c;
                return self._class || "";
            };
            this.$target.on('snippet-style-change snippet-style-preview', function (event, style, np) {
                var $active = self.$target.find(".item.active");
                if (style['snippet-style-id'] === "size") return;
                if (style['snippet-style-id'] === "background") {
                    $active.css("background-image", self.$target.css("background-image"));
                }
                if (np.$prev) {
                    $active.removeClass(np.$prev.data("class"));
                }
                if (np.$next) {
                    $active.addClass(np.$next.data("class"));
                    add_class(np.$next.data("class"));
                }
            });
            this.$target.on('slid', function () { // slide.bs.carousel
                var $active = self.$target.find(".item.active");
                self.$target
                    .css("background-image", $active.css("background-image"))
                    .removeClass(add_class($active.attr("class")))
                    .addClass($active.attr("class"))
                    .trigger("snippet-style-reset");

                self.$target.carousel();
            });
            this.$target.trigger('slid');
        },
        on_add_slide: function () {
            var $clone = this._super();

            // choose an other background
            var $styles = this.$target.data("snippet-style-ids").background.$el.find("li[data-class]:not(.oe_custom_bg)");
            var styles_index = $styles.index($styles.filter(".active")[0]);
            var $select = $($styles[styles_index >= $styles.length-1 ? 0 : styles_index+1]);
            $clone.css("background-image", $select.data("src") ? "url('"+ $select.data("src") +"')" : "");
            $clone.addClass($select.data("class") || "");

            return $clone;
        },
        // rebind event to active carousel on edit mode
        rebind_event: function () {
            var self = this;
            this.$target.find('.carousel-control').off('click').on('click', function () {
                self.$target.carousel( $(this).data('slide')); });

            this.$target.find('.carousel-image, .carousel-inner .content > div').attr('contentEditable', 'true');
            this.$target.find('.carousel-image').attr('attributeEditable', 'true');
            this._super();
        },
    });

    website.snippet.editorRegistry.parallax = website.snippet.editorRegistry.resize.extend({
        getSize: function () {
            this.grid = this._super();
            this.grid.size = 8;
            return this.grid;
        },
        on_resize: function (compass, beginClass, current) {
            this.$target.data("snippet-view").set_values();
        },
        start : function () {
            var self = this;
            this._super();
            if (!self.$target.data("snippet-view")) {
                this.$target.data("snippet-view", new website.snippet.animationRegistry.parallax(this.$target));
            }
            this.scroll();
            this.$target.on('snippet-style-change snippet-style-preview', function () {
                self.$target.data("snippet-view").set_values();
            });
            this.$target.attr('contentEditable', 'false');

            this.$target.find('> div > .oe_structure').attr('contentEditable', 'true'); // saas-3 retro-compatibility

            this.$target.find('> div > div:not(.oe_structure) > .oe_structure').attr('contentEditable', 'true');
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
        }
    });

    /*
    * data-snippet-id automatically setted
    * Don't need to add data-snippet-id="..." into the views
    */

    website.snippet.selector.push([".row > [class*='col-md-']", 'colmd']);
    website.snippet.selector.push(['hr', 'hr']);
    website.snippet.selector.push(['blockquote', 'quote']);

})();
