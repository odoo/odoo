(function () {
    'use strict';

    var dummy = function () {};

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
            $("[data-oe-model] *, [data-oe-type=html] *").off('click');
            window.snippets = this.snippets = new website.snippet.BuildingBlock(this);
            this.snippets.appendTo(this.$el);
            website.snippet.stop_animation();
            this.on('rte:ready', this, function () {
                self.snippets.$button.removeClass("hidden");
                website.snippet.start_animation();
                $("#wrapwrap *").off('mousedown mouseup click');
            });

            return this._super.apply(this, arguments);
        },
        save: function () {
            this.snippets.clean_for_save();
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
    });

    $.extend($.expr[':'],{
        checkData: function(node,i,m){
            var dataName = m[3];
            while (node) {
                if (node.dataset && node.dataset[dataName]) {
                    return true;
                } else {
                    node = node.parentNode;
                }
            }
            return false;
        },
        hasData: function(node,i,m){
            return !!_.toArray(node.dataset).length;
        },
    });

    if (!website.snippet) website.snippet = {};
    website.snippet.templateOptions = [];
    website.snippet.globalSelector = "";
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
            this.snippets = [];

            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
        },
        start: function() {
            var self = this;

            this.$button = $(openerp.qweb.render('website.snippets_button'))
                .prependTo(this.parent.$("#website-top-edit ul"))
                .find("button");

            this.$button.click(_.bind(this.show_blocks, this));

            this.$snippet = $("#oe_snippets");
            this.$wrapwrap = $("#wrapwrap");
            this.$wrapwrap.click(function () {
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
            this.$el.css('top', this.parent.get('height'));
        },
        show_blocks: function () {
            var self = this;
            this.make_active(false);
            this.$el.toggleClass("hidden");
            if (this.$el.hasClass("hidden")) {
                return;
            }

            //this.enable_snippets( this.$snippet.find(".tab-pane.active") );
            var categories = this.$snippet.find(".tab-pane.active")
                .add(this.$snippet.find(".tab-pane:not(.active)"))
                .get().reverse();
            function enable() {
                self.enable_snippets( $(categories.pop()) );
                if (categories.length) {
                    setTimeout(enable,10);
                }
            }
            setTimeout(enable,0);
        },
        enable_snippets: function ($category) {
            var self = this;
            $category.find(".oe_snippet_body").each(function () {
                var $snippet = $(this);

                if (!$snippet.data('selectors')) {
                    var selectors = [];
                    for (var k in website.snippet.templateOptions) {
                        var option = website.snippet.templateOptions[k];
                        if ($snippet.is(option.base_selector)) {

                            var dropzone = [];
                            if (option['drop-near']) dropzone.push(option['drop-near']);
                            if (option['drop-in']) dropzone.push(option['drop-in']);
                            if (option['drop-in-vertical']) dropzone.push(option['drop-in-vertical']);
                            selectors = selectors.concat(dropzone);
                        }
                    }
                    $snippet.data('selectors', selectors.length ? selectors.join(":first, ") + ":first" : "");
                }

                if ($snippet.data('selectors').length && self.$wrapwrap.find($snippet.data('selectors')).size()) {
                    $snippet.closest(".oe_snippet").removeClass("disable");
                } else {
                    $snippet.closest(".oe_snippet").addClass("disable");
                }
            });
            $('#oe_snippets .scroll a[data-toggle="tab"][href="#' + $category.attr("id") + '"]')
                .toggle(!!$category.find(".oe_snippet:not(.disable)").size());
        },
        _get_snippet_url: function () {
            return '/website/snippets';
        },
        _add_check_selector : function (selector, no_check) {
            var data = selector.split(",");
            var selectors = [];
            for (var k in data) {
                selectors.push(data[k].replace(/^\s+|\s+$/g, '') + (no_check ? "" : ":checkData(oeModel)"));
            }
            return selectors.join(", ");
        },
        fetch_snippet_templates: function () {
            var self = this;

            openerp.jsonRpc(this._get_snippet_url(), 'call', {})
                .then(function (html) {
                    var $html = $(html);

                    var selector = [];
                    var $styles = $html.find("[data-js], [data-selector]");
                    $styles.each(function () {
                        var $style = $(this);
                        var no_check = $style.data('no-check');
                        var option_id = $style.data('js');
                        var option = {
                            'option' : option_id,
                            'base_selector': $style.data('selector'),
                            'selector': self._add_check_selector($style.data('selector'), no_check),
                            '$el': $style,
                            'drop-near': $style.data('drop-near') && self._add_check_selector($style.data('drop-near'), no_check),
                            'drop-in': $style.data('drop-in') && self._add_check_selector($style.data('drop-in'), no_check),
                            'data': $style.data()
                        };
                        website.snippet.templateOptions.push(option);
                        selector.push(option.selector);
                    });
                    $styles.addClass("hidden");
                    website.snippet.globalSelector = selector.join(",");

                    self.$snippets = $html.find(".tab-content > div > div")
                        .addClass("oe_snippet")
                        .each(function () {
                            if (!$('.oe_snippet_thumbnail', this).size()) {
                                var $div = $(
                                    '<div class="oe_snippet_thumbnail">'+
                                        '<div class="oe_snippet_thumbnail_img"/>'+
                                        '<span class="oe_snippet_thumbnail_title"></span>'+
                                    '</div>');
                                $div.find('span').text($(this).attr("name"));
                                $(this).prepend($div);
                            }
                            $("> *:not(.oe_snippet_thumbnail)", this).addClass('oe_snippet_body');
                        });

                    self.$el.append($html);

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
            $el.find(".oe_handle.e,.oe_handle.w").css({'height': $target.outerHeight() + mt + mb+1});
            $el.find(".oe_handle.s").css({'top': $target.outerHeight() + mt + mb});
            $el.find(".oe_handle.size").css({'top': $target.outerHeight() + mt});
            $el.find(".oe_handle.s,.oe_handle.n").css({'width': $target.outerWidth()-2});
        },
        show: function () {
            this.$el.removeClass("hidden");
        },
        hide: function () {
            this.$el.addClass("hidden");
        },
        bind_snippet_click_editor: function () {
            var self = this;
            var snipped_event_flag;
            self.$wrapwrap.on('click', function (event) {
                var srcElement = event.srcElement || (event.originalEvent && (event.originalEvent.originalTarget || event.originalEvent.target));
                if (snipped_event_flag || !srcElement) {
                    return;
                }
                snipped_event_flag = true;

                setTimeout(function () {snipped_event_flag = false;}, 0);
                var $target = $(srcElement);

                if ($target.parents(".oe_overlay").length) {
                    return;
                }

                if (!$target.is(website.snippet.globalSelector)) {
                    $target = $target.parents(website.snippet.globalSelector).first();
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
                    $snippet.data("snippet-editor").on_blur();
                }
            }
        },
        snippet_focus: function ($snippet) {
            if ($snippet) {
                if ($snippet.data("snippet-editor")) {
                    $snippet.data("snippet-editor").on_focus();
                }
            }
        },
        clean_for_save: function () {
            var self = this;
            var options = website.snippet.options;
            var template = website.snippet.templateOptions;
            for (var k in template) {
                var Option = options[template[k]['option']];
                if (Option && Option.prototype.clean_for_save !== dummy) {
                    self.$wrapwrap.find(template[k].selector).each(function () {
                        new Option(self, null, $(this), k).clean_for_save();
                    });
                }
            }
            self.$wrapwrap.find("*[contentEditable], *[attributeEditable]")
                .removeAttr('contentEditable')
                .removeAttr('attributeEditable');
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
            this.$snippet.trigger('snippet-activated', $snippet);
            if ($snippet) {
                $snippet.trigger('snippet-activated', $snippet);
            }
        },
        create_overlay: function ($snippet) {
            if (typeof $snippet.data("snippet-editor") === 'undefined') {
                var $targets = this.activate_overlay_zones($snippet);
                if (!$targets.length) return;
                $snippet.data("snippet-editor", new website.snippet.Editor(this, $snippet));
            }
            this.cover_target($snippet.data('overlay'), $snippet);
        },

        // activate drag and drop for the snippets in the snippet toolbar
        make_snippet_draggable: function($snippets){
            var self = this;
            var $tumb = $snippets.find(".oe_snippet_thumbnail_img:first");
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
                    // snippet_selectors => to get drop-near, drop-in
                    $snippet = $(this);
                    var $base_body = $snippet.find('.oe_snippet_body');
                    var selector = [];
                    var selector_siblings = [];
                    var selector_children = [];
                    var vertical = false;
                    var temp = website.snippet.templateOptions;
                    for (var k in temp) {
                        if ($base_body.is(temp[k].base_selector)) {
                            selector.push(temp[k].base_selector);
                            if (temp[k]['drop-near'])
                                selector_siblings.push(temp[k]['drop-near']);
                            if (temp[k]['drop-in'])
                                selector_children.push(temp[k]['drop-in']);
                        }
                    }

                    $toInsert = $base_body.clone();
                    action = $snippet.find('.oe_snippet_body').size() ? 'insert' : 'mutate';

                    if( action === 'insert'){
                        if (!selector_siblings.length && !selector_children.length) {
                            console.debug($snippet.find(".oe_snippet_thumbnail_title").text() + " have not insert action: data-drop-near or data-drop-in");
                            return;
                        }
                        self.activate_insertion_zones({
                            siblings: selector_siblings.join(","),
                            children: selector_children.join(","),
                        });

                    } else if( action === 'mutate' ){
                        if (!$snippet.data('selector')) {
                            console.debug($snippet.data("option") + " have not oe_snippet_body class and have not data-selector tag");
                            return;
                        }
                        var $targets = self.activate_overlay_zones(selector_children.join(","));
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
                    $toInsert.removeClass('oe_snippet_body');
                    
                    if (action === 'insert' && ! dropped && self.$wrapwrap.find('.oe_drop_zone') && ui.position.top > 3) {
                        var el = self.$wrapwrap.find('.oe_drop_zone').nearest({x: ui.position.left, y: ui.position.top}).first();
                        if (el.length) {
                            el.after($toInsert);
                            dropped = true;
                        }
                    }

                    self.$wrapwrap.find('.oe_drop_zone').droppable('destroy').remove();
                    
                    if (dropped) {
                        var $target = false;
                        $target = $toInsert;

                        setTimeout(function () {
                            self.$snippet.trigger('snippet-dropped', $target);

                            website.snippet.start_animation(true, $target);

                            // reset snippet for rte
                            $target.removeData("snippet-editor");
                            if ($target.data("overlay")) {
                                $target.data("overlay").remove();
                                $target.removeData("overlay");
                            }
                            $target.find(website.snippet.globalSelector).each(function () {
                                var $snippet = $(this);
                                $snippet.removeData("snippet-editor");
                                if ($snippet.data("overlay")) {
                                    $snippet.data("overlay").remove();
                                    $snippet.removeData("overlay");
                                }
                            });
                            // end

                            // drop_and_build_snippet
                            self.create_overlay($target);
                            if ($target.data("snippet-editor")) {
                                $target.data("snippet-editor").drop_and_build_snippet();
                            }
                            for (var k in website.snippet.templateOptions) {
                                $target.find(website.snippet.templateOptions[k].selector).each(function () {
                                    var $snippet = $(this);
                                    self.create_overlay($snippet);
                                    if ($snippet.data("snippet-editor")) {
                                        $snippet.data("snippet-editor").drop_and_build_snippet();
                                    }
                                });
                            }
                            // end

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
                    return $(this).data('option') === id;
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

            var zone_template = $("<div class='oe_drop_zone oe_insert'></div>");

            if(child_selector){
                self.$wrapwrap.find(child_selector).each(function (){
                    var $zone = $(this);
                    var vertical;
                    var float = window.getComputedStyle(this).float;
                    if (float === "left" || float === "right") {
                        vertical = $zone.parent().outerHeight()+'px';
                    }
                    var $drop = zone_template.clone();
                    if (vertical) {
                        $drop.addClass("oe_vertical").css('height', vertical);
                    }
                    $zone.find('> *:not(.oe_drop_zone):visible').after($drop);
                    $zone.prepend($drop.clone());
                });
            }

            if(sibling_selector){
                self.$wrapwrap.find(sibling_selector, true).each(function (){
                    var $zone = $(this);
                    var $drop, vertical;
                    var float = window.getComputedStyle(this).float;
                    if (float === "left" || float === "right") {
                        vertical = $zone.parent().outerHeight()+'px';
                    }

                    if($zone.prev('.oe_drop_zone:visible').length === 0){
                        $drop = zone_template.clone();
                        if (vertical) {
                            $drop.addClass("oe_vertical").css('height', vertical);
                        }
                        $zone.before($drop);
                    }
                    if($zone.next('.oe_drop_zone:visible').length === 0){
                        $drop = zone_template.clone();
                        if (vertical) {
                            $drop.addClass("oe_vertical").css('height', vertical);
                        }
                        $zone.after($drop);
                    }
                });
            }

            var count;
            do {
                count = 0;
                // var $zones = $('.oe_drop_zone + .oe_drop_zone');    // no two consecutive zones
                // count += $zones.length;
                // $zones.remove();

                $zones = self.$wrapwrap.find('.oe_drop_zone > .oe_drop_zone:not(.oe_vertical)').remove();   // no recursive zones
                count += $zones.length;
                $zones.remove();
            } while (count > 0);

            // Cleaning consecutive zone and up zones placed between floating or inline elements. We do not like these kind of zones.
            var $zones = self.$wrapwrap.find('.oe_drop_zone:not(.oe_vertical)');
            $zones.each(function (){
                var zone = $(this);
                var prev = zone.prev();
                var next = zone.next();
                // remove consecutive zone
                if (!zone.hasClass('.oe_vertical') && (prev.is('.oe_drop_zone:not(.oe_vertical)') || next.is('.oe_drop_zone:not(.oe_vertical)'))) {
                    zone.remove();
                    return;
                }
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
            var $targets = typeof selector === "string" ? this.$wrapwrap.find(selector) : selector;
            var self = this;

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
                    var resize = function () {
                        if ($zone.parent().length) {
                            self.cover_target($zone, $target);
                        } else {
                            $('body').off("resize", resize);
                        }
                    };
                    $('body').on("resize", resize);
                }
                self.cover_target($target.data('overlay'), $target);
            });
            return $targets;
        }
    });


    website.snippet.options = {};
    website.snippet.Option = openerp.Class.extend({
        // initialisation (don't overwrite)
        init: function (BuildingBlock, editor, $target, option_id) {
            this.BuildingBlock = BuildingBlock;
            this.editor = editor;
            this.$target = $target;
            var option = website.snippet.templateOptions[option_id];
            var styles = this.$target.data("snippet-option-ids") || {};
            styles[option_id] = this;
            this.$target.data("snippet-option-ids", styles);
            this.$overlay = this.$target.data('overlay') || $('<div>');
            this.option= option_id;
            this.$el = option.$el.find(">li").clone();
            this.data = option.$el.data();

            this.set_active();
            this.$target.on('snippet-option-reset', _.bind(this.set_active, this));
            this._bind_li_menu();

            this.start();
        },

        _bind_li_menu: function () {
            this.$el.filter("li:hasData").find('a:first')
                .off('mouseenter click')
                .on('mouseenter click', _.bind(this._mouse, this));

            this.$el
                .off('mouseenter click', "li:hasData a")
                .on('mouseenter click', "li:hasData a", _.bind(this._mouse, this));

            this.$el.closest("ul").add(this.$el)
                .off('mouseleave')
                .on('mouseleave', _.bind(this.reset, this));

            this.$el
                .off('mouseleave', "ul")
                .on('mouseleave', "ul", _.bind(this.reset, this));

            this.reset_methods = [];
            this.reset_time = null;
        },

        /**
         * this method handles mouse:over and mouse:leave on the snippet editor menu
         */
         _time_mouseleave: null,
        _mouse: function (event) {
            var $next = $(event.currentTarget).parent();

            // triggers preview or apply methods if a menu item has been clicked
            this.select(event.type === "click" ? "click" : "over", $next);
            if (event.type === 'click') {
                this.set_active();
                this.$target.trigger("snippet-option-change", [this]);
            } else {
                this.$target.trigger("snippet-option-preview", [this]);
            }
        },
        /* 
        *  select and set item active or not (add highlight item and his parents)
        *  called before start
        */
        set_active: function () {
            var classes = _.uniq((this.$target.attr("class") || '').split(/\s+/));
            this.$el.find('[data-toggle_class], [data-select_class]')
                .add(this.$el)
                .filter('[data-toggle_class], [data-select_class]')
                .removeClass("active")
                .filter('[data-toggle_class="' + classes.join('"], [data-toggle_class="') + '"] ,'+
                    '[data-select_class="' + classes.join('"], [data-select_class="') + '"]')
                .addClass("active");
        },

        start: function () {
        },

        on_focus : function () {
            this._bind_li_menu();
        },

        on_blur : function () {
        },

        on_clone: function ($clone) {
        },

        on_remove: function () {
        },

        drop_and_build_snippet: function () {
        },

        reset: function (event) {
            var self = this;
            var lis = self.$el.add(self.$el.find('li')).filter('.active').get();
            lis.reverse();
            _.each(lis, function (li) {
                var $li = $(li);
                for (var k in self.reset_methods) {
                    var method = self.reset_methods[k];
                    if ($li.is('[data-'+method+']') || $li.closest('[data-'+method+']').size()) {
                        delete self.reset_methods[k];
                    }
                }
                self.select("reset", $li);
            });

            for (var k in self.reset_methods) {
                var method = self.reset_methods[k];
                if (method) {
                    self[method]("reset", null);
                }
            }
            self.reset_methods = [];
            self.$target.trigger("snippet-option-reset", [this]);
        },

        // call data-method args as method
        select: function (type, $li) {
            var self = this,
                $methods = [],
                el = $li[0],
                $el;
            clearTimeout(this.reset_time);

            function filter (k) { return k !== 'oeId' && k !== 'oeModel' && k !== 'oeField' && k !== 'oeXpath' && k !== 'oeSourceId';}
            function hasData(el) {
                for (var k in el.dataset) {
                    if (filter (k)) {
                        return true;
                    }
                }
                return false;
            }
            function method(el) {
                var data = {};
                for (var k in el.dataset) {
                    if (filter (k)) {
                        data[k] = el.dataset[k];
                    }
                }
                return data;
            }

            while (el && this.$el.is(el) || _.some(this.$el.map(function () {return $.contains(this, el);}).get()) ) {
                if (hasData(el)) {
                    $methods.push(el);
                }
                el = el.parentNode;
            }

            $methods.reverse();

            _.each($methods, function (el) {
                var $el = $(el);
                var methods = method(el);

                for (var k in methods) {
                    if (self[k]) {
                        if (type !== "reset" && self.reset_methods.indexOf(k) === -1) {
                            self.reset_methods.push(k);
                        }
                        self[k](type, methods[k], $el);
                    } else {
                        console.error("'"+self.option+"' snippet have not method '"+k+"'");
                    }
                }
            });
        },

        // default method for snippet
        toggle_class: function (type, value, $li) {
            var $lis = this.$el.find('[data-toggle_class]').add(this.$el).filter('[data-toggle_class]');

            function map ($lis) {
                return $lis.map(function () {return $(this).data("toggle_class");}).get().join(" ");
            }
            var classes = map($lis);
            var active_classes = map($lis.filter('.active, :has(.active)'));

            this.$target.removeClass(classes);
            this.$target.addClass(active_classes);

            if (type !== 'reset') {
                this.$target.toggleClass(value);
            }
        },
        select_class: function (type, value, $li) {
            var $lis = this.$el.find('[data-select_class]').add(this.$el).filter('[data-select_class]');

            var classes = $lis.map(function () {return $(this).data('select_class');}).get();

            this.$target.removeClass(classes.join(" "));
            if(value) this.$target.addClass(value);
        },
        eval: function (type, value, $li) {
            var fn = new Function("node", "type", "value", "$li", value);
            fn.call(this, this, type, value, $li);
        },

        clean_for_save: dummy
    });
    website.snippet.options.background = website.snippet.Option.extend({
        start: function () {
            this._super();
            var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            if (this.$target.hasClass('oe_custom_bg')) {
                this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
            }
        },
        background: function(type, value, $li) {
            if (value && value.length) {
                this.$target.css("background-image", 'url(' + value + ')');
                this.$target.addClass("oe_img_bg");
            } else {
                this.$target.css("background-image", "");
                this.$target.removeClass("oe_img_bg").removeClass("oe_custom_bg");
            }
        },
        choose_image: function(type, value, $li) {
            if(type !== "click") return;

            var self = this;
            var $image = $('<img class="hidden"/>');
            $image.attr("src", value);
            $image.appendTo(self.$target);

            self.element = new CKEDITOR.dom.element($image[0]);
            var editor = new website.editor.MediaDialog(self, self.element);
            editor.appendTo(document.body);
            editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');

            $image.on('saved', self, function (o) {
                var value = $image.attr("src");
                self.$target.css("background-image", 'url(' + value + ')');
                self.$el.find('li[data-choose_image]').data("background", value).attr("data-background", value);
                self.$target.trigger("snippet-option-change", [self]);
                $image.remove();
                self.$target.addClass('oe_custom_bg oe_img_bg');
                self.set_active();
            });
            editor.on('cancel', self, function () {
                self.$target.trigger("snippet-option-change", [self]);
                $image.remove();
            });
        },
        set_active: function () {
            var self = this;
            var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            this._super();

            this.$el.find('li[data-background]:not([data-background=""])')
                .removeClass("active")
                .each(function () {
                    var background = $(this).data("background") || $(this).attr("data-background");
                    if ((src.length && background.length && src.indexOf(background) !== -1) || (!src.length && !background.length)) {
                        $(this).addClass("active");
                    }
                });

            if (!this.$el.find('li[data-background].active').size()) {
                this.$el.find('li[data-background=""]:not([data-choose_image])').addClass("active");
            } else {
                this.$el.find('li[data-background=""]:not([data-choose_image])').removeClass("active");
            }
        }
    });

    website.snippet.options.colorpicker = website.snippet.Option.extend({
        start: function () {
            var self = this;
            var res = this._super();

            this.$el.find('li').append( openerp.qweb.render('website.colorpicker') );

            var classes = [];
            this.$el.find("table.colorpicker td > *").map(function () {
                var $color = $(this);
                var color = $color.attr("class");
                if (self.$target.hasClass(color)) {
                    self.color = color;
                    $color.parent().addClass("selected");
                }
                classes.push(color);
            });
            this.classes = classes.join(" ");

            this.bind_events();
            return res;
        },
        bind_events: function () {
            var self = this;
            var $td = this.$el.find("table.colorpicker td");
            var $colors = $td.children();
            $colors
                .mouseenter(function () {
                    self.$target.removeClass(self.classes).addClass($(this).attr("class"));
                })
                .mouseleave(function () {
                    self.$target.removeClass(self.classes)
                        .addClass($td.filter(".selected").children().attr("class"));
                })
                .click(function () {
                    $td.removeClass("selected");
                    $(this).parent().addClass("selected");
                });
        }
    });

    website.snippet.options.slider = website.snippet.Option.extend({
        unique_id: function () {
            var id = 0;
            $(".carousel").each(function () {
                var cid = 1 + parseInt($(this).attr("id").replace(/[^0123456789]/g, ''),10);
                if (id < cid) id = cid;
            });
            return "myCarousel" + id;
        },
        drop_and_build_snippet: function() {
            this.id = this.unique_id();
            this.$target.attr("id", this.id);
            this.$target.find("[data-slide]").attr("data-cke-saved-href", "#" + this.id);
            this.$target.find("[data-target]").attr("data-target", "#" + this.id);
            this.rebind_event();
        },
        on_clone: function ($clone) {
            var id = this.unique_id();
            $clone.attr("id", id);
            $clone.find("[data-slide]").attr("href", "#" + id);
            $clone.find("[data-slide-to]").attr("data-target", "#" + id);
        },
        // rebind event to active carousel on edit mode
        rebind_event: function () {
            var self = this;
            this.$target.find('.carousel-indicators [data-slide-to]').off('click').on('click', function () {
                self.$target.carousel(+$(this).data('slide-to')); });

            this.$target.attr('contentEditable', 'false');
            this.$target.find('.oe_structure, .content.row, [data-slide]').attr('contentEditable', 'true');
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".item").removeClass("next prev left right active")
                .first().addClass("active");
            this.$indicators.find('li').removeClass('active')
                .first().addClass("active");
        },
        start : function () {
            var self = this;
            this._super();
            this.$target.carousel({interval: false});
            this.id = this.$target.attr("id");
            this.$inner = this.$target.find('.carousel-inner');
            this.$indicators = this.$target.find('.carousel-indicators');
            this.$target.carousel('pause');
            this.rebind_event();
        },
        add_slide: function (type, value) {
            if(type !== "click") return;

            var self = this;
            var cycle = this.$inner.find('.item').length;
            var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
            var index = $active.index();
            this.$target.find('.carousel-control, .carousel-indicators').removeClass("hidden");
            this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');

            // clone the best candidate from template to use new features
            var $snippets = this.BuildingBlock.$snippets.find('.oe_snippet_body.carousel');
            var point = 0;
            var selection;
            var className = _.compact(this.$target.attr("class").split(" "));
            $snippets.each(function () {
                var len = _.intersection(_.compact(this.className.split(" ")), className).length;
                if (len > point) {
                    point = len;
                    selection = this;
                }
            });
            var $clone = $(selection).find('.item:first').clone();

            // insert
            $clone.removeClass('active').insertAfter($active);
            setTimeout(function() {
                self.$target.carousel().carousel(++index);
                self.rebind_event();
            },0);
            return $clone;
        },
        remove_slide: function (type, value) {
            if(type !== "click") return;

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
        interval : function(type, value) {
            this.$target.attr("data-interval", value);
        },
        set_active: function () {
            this.$el.find('li[data-interval]').removeClass("active")
                .filter('li[data-interval='+this.$target.attr("data-interval")+']').addClass("active");
        },
    });
    website.snippet.options.carousel = website.snippet.options.slider.extend({
        getSize: function () {
            this.grid = this._super();
            this.grid.size = 8;
            return this.grid;
        },
        clean_for_save: function () {
            this._super();
            this.$target.removeClass('oe_img_bg ' + this._class).css("background-image", "");
        },
        load_style_options : function () {
            this._super();
            $(".snippet-option-size li[data-value='']").remove();
        },
        start : function () {
            var self = this;
            this._super();

            // set background and prepare to clean for save
            var add_class = function (c){
                if (c) self._class = (self._class || "").replace(new RegExp("[ ]+" + c.replace(" ", "|[ ]+")), '') + ' ' + c;
                return self._class || "";
            };
            this.$target.on('slid.bs.carousel', function () {
                if(self.editor && self.editor.styles.background) {
                    self.editor.styles.background.$target = self.$target.find(".item.active");
                    self.editor.styles.background.set_active();
                }
                self.$target.carousel("pause");
            });
            this.$target.trigger('slid.bs.carousel');
        },
        add_slide: function (type, data) {
            if(type !== "click") return;

            var $clone = this._super(type, data);
            // choose an other background
            var bg = this.$target.data("snippet-option-ids").background;
            if (!bg) return $clone;

            var $styles = bg.$el.find("li[data-background]");
            var $select = $styles.filter(".active").removeClass("active").next("li[data-background]");
            if (!$select.length) {
                $select = $styles.first();
            }
            $select.addClass("active");
            $clone.css("background-image", $select.data("background") ? "url('"+ $select.data("background") +"')" : "");

            return $clone;
        },
        // rebind event to active carousel on edit mode
        rebind_event: function () {
            var self = this;
            this.$target.find('.carousel-control').off('click').on('click', function () {
                self.$target.carousel( $(this).data('slide')); });
            this._super();

            /* Fix: backward compatibility saas-3 */
            this.$target.find('.item.text_image, .item.image_text, .item.text_only').find('.container > .carousel-caption > div, .container > img.carousel-image').attr('contentEditable', 'true');
        },
    });
    website.snippet.options.marginAndResize = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this._super();

            var resize_values = this.getSize();
            if (resize_values.n) this.$overlay.find(".oe_handle.n").removeClass("readonly");
            if (resize_values.s) this.$overlay.find(".oe_handle.s").removeClass("readonly");
            if (resize_values.e) this.$overlay.find(".oe_handle.e").removeClass("readonly");
            if (resize_values.w) this.$overlay.find(".oe_handle.w").removeClass("readonly");
            if (resize_values.size) this.$overlay.find(".oe_handle.size").removeClass("readonly");

            this.$overlay.find(".oe_handle:not(.size), .oe_handle.size .size").on('mousedown', function (event){
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

                self.BuildingBlock.editor_busy = true;

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
                        self.$target.css("overflow", "hidden");
                        self.on_resize(compass, null, dy);
                        self.BuildingBlock.cover_target(self.$overlay, self.$target);
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
                        self.BuildingBlock.cover_target(self.$overlay, self.$target);
                    }
                };

                var body_mouseup = function(){
                    $body.unbind('mousemove', body_mousemove);
                    $body.unbind('mouseup', body_mouseup);
                    $body.removeClass(cursor);
                    self.BuildingBlock.editor_busy = false;
                    self.$target.removeClass("resize_editor_busy");
                };
                $body.mousemove(body_mousemove);
                $body.mouseup(body_mouseup);
            });
            this.$overlay.find(".oe_handle.size .auto_size").on('click', function (event){
                self.$target.css("height", "");
                self.$target.css("overflow", "");
                self.BuildingBlock.cover_target(self.$overlay, self.$target);
                return false;
            });
        },
        getSize: function () {
            this.grid = {};
            return this.grid;
        },

        on_focus : function () {
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
    website.snippet.options["margin-y"] = website.snippet.options.marginAndResize.extend({
        getSize: function () {
            this.grid = this._super();
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
    });
    website.snippet.options["margin-x"] = website.snippet.options.marginAndResize.extend({
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
            this.$overlay.find('.oe_snippet_remove').toggleClass("hidden", !this.$target.siblings().length);
        },
        on_focus : function () {
            this._super();
            this.hide_remove_button();
        },
        on_clone: function ($clone) {
            var _class = $clone.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-)([0-9-]+)/g, '');
            $clone.attr("class", _class);
            this.hide_remove_button();
            return false;
        },
        on_remove: function () {
            this._super();
            this.hide_remove_button();
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

    website.snippet.options.resize = website.snippet.options.marginAndResize.extend({
        getSize: function () {
            this.grid = this._super();
            this.grid.size = 8;
            return this.grid;
        },
    });

    website.snippet.options.parallax = website.snippet.Option.extend({
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
            this.$target.on('snippet-option-change snippet-option-preview', function () {
                self.$target.data("snippet-view").set_values();
            });
            this.$target.attr('contentEditable', 'false');

            this.$target.find('> div > .oe_structure').attr('contentEditable', 'true'); // saas-3 retro-compatibility

            this.$target.find('> div > div:not(.oe_structure) > .oe_structure').attr('contentEditable', 'true');
        },
        scroll: function (type, value) {
            this.$target.attr('data-scroll-background-ratio', value);
            this.$target.data("snippet-view").set_values();
        },
        set_active: function () {
            var value = this.$target.attr('data-scroll-background-ratio') || 0;
            this.$el.find('[data-scroll]').removeClass("active")
                .filter('[data-scroll="' + (this.$target.attr('data-scroll-background-ratio') || 0) + '"]').addClass("active");
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".parallax")
                .css("background-position", '')
                .removeAttr("data-scroll-background-offset");
        }
    });

    website.snippet.options.transform = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this._super();
            this.$overlay.find('.oe_snippet_clone, .oe_handles').addClass('hidden');
            this.$overlay.find('[data-toggle="dropdown"]')
                .on("mousedown", function () {
                    self.$target.transfo("hide");
                });
        },
        style: function (type, value) {
            if (type !== 'click') return;
            var settings = this.$target.data("transfo").settings;
            this.$target.transfo({ hide: (settings.hide = !settings.hide) });
        },
        clear_style: function (type, value) {
            if (type !== 'click') return;
            this.$target.removeClass("fa-spin").attr("style", "");
            this.resetTransfo();
        },
        resetTransfo: function () {
            var self = this;
            this.$target.transfo("destroy");
            this.$target.transfo({
                hide: true,
                callback: function () {
                    var center = $(this).data("transfo").$markup.find('.transfo-scaler-mc').offset();
                    var $option = self.$overlay.find('.btn-group:first');
                    self.$overlay.css({
                        'top': center.top - $option.height()/2,
                        'left': center.left,
                        'position': 'absolute',
                    });
                    self.$overlay.find(".oe_overlay_options").attr("style", "width:0; left:0!important; top:0;");
                    self.$overlay.find(".oe_overlay_options > .btn-group").attr("style", "width:160px; left:-80px;");
                }});
            this.$target.data('transfo').$markup
                .on("mouseover", function () {
                    self.$target.trigger("mouseover");
                })
                .mouseover();
        },
        on_focus : function () {
            this.resetTransfo();
        },
        on_blur : function () {
            this.$target.transfo("hide");
        },
    });

    website.snippet.options.media = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this._super();

            website.snippet.start_animation(true, this.$target);

            $(document.body).on("media-saved", self, function (event, prev , item) {
                self.editor.on_blur();
                self.BuildingBlock.make_active(false);
                if (self.$target.parent().data("oe-field") !== "image") {
                    self.BuildingBlock.make_active($(item));
                }
            });
        },
        edition: function (type, value) {
            if(type !== "click") return;
            this.element = new CKEDITOR.dom.element(this.$target[0]);
            new website.editor.MediaDialog(this, this.element).appendTo(document.body);
        },
        on_focus : function () {
            var self = this;
            if (this.$target.parent().data("oe-field") === "image") {
                this.$overlay.addClass("hidden");
                self.element = new CKEDITOR.dom.element(self.$target[0]);
                new website.editor.MediaDialog(self, self.element).appendTo(document.body);
                self.BuildingBlock.make_active(false);
            }
            setTimeout(function () {
                self.$target.find(".css_editable_mode_display").removeAttr("_moz_abspos");
            },0);
        },
    });

    website.snippet.Editor = openerp.Class.extend({
        init: function (BuildingBlock, dom) {
            this.BuildingBlock = BuildingBlock;
            this.$target = $(dom);
            this.$overlay = this.$target.data('overlay');
            this.load_style_options();
            this.get_parent_block();
            this.start();
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
            self.BuildingBlock.hide();
            self.BuildingBlock.editor_busy = true;
            self.size = {
                width: self.$target.width(),
                height: self.$target.height()
            };
            self.$target.after("<div class='oe_drop_clone' style='display: none;'/>");
            self.$target.detach();
            self.$overlay.addClass("hidden");

            self.BuildingBlock.activate_insertion_zones({
                siblings: self.selector_siblings,
                children: self.selector_children,
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
            self.BuildingBlock.editor_busy = false;
            self.get_parent_block();
            setTimeout(function () {self.BuildingBlock.create_overlay(self.$target);},0);
        },

        load_style_options: function () {
            var self = this;
            var $styles = this.$overlay.find('.oe_options');
            var $ul = $styles.find('ul:first');
            this.styles = {};
            this.selector_siblings = [];
            this.selector_children = [];
            _.each(website.snippet.templateOptions, function (val, option_id) {
                if (!self.$target.is(val.selector)) {
                    return;
                }
                if (val['drop-near']) self.selector_siblings.push(val['drop-near']);
                if (val['drop-in']) self.selector_children.push(val['drop-in']);

                var option = val['option'];
                var Editor = website.snippet.options[option] || website.snippet.Option;
                var editor = self.styles[option] = new Editor(self.BuildingBlock, self, self.$target, option_id);
                $ul.append(editor.$el.addClass("snippet-option-" + option));
            });
            this.selector_siblings = this.selector_siblings.join(",");
            if (this.selector_siblings === "")
                this.selector_siblings = false;
            this.selector_children = this.selector_children.join(",");
            if (this.selector_children === "")
                this.selector_children = false;

            if (!this.selector_siblings && !this.selector_children) {
                this.$overlay.find(".oe_snippet_move, .oe_snippet_clone, .oe_snippet_remove").addClass('hidden');
            }


            if ($ul.find("li").length) {
                $styles.removeClass("hidden");
            }
            this.$overlay.find('[data-toggle="dropdown"]').dropdown();
        },

        get_parent_block: function () {
            var self = this;
            var $button = this.$overlay.find('.oe_snippet_parent');
            var $parent = this.$target.parents(website.snippet.globalSelector).first();
            if ($parent.length) {
                $button.removeClass("hidden");
                $button.off("click").on('click', function (event) {
                    event.preventDefault();
                    setTimeout(function () {
                        self.BuildingBlock.make_active($parent);
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
            for (var i in this.styles){
                this.styles[i].on_clone($clone);
            }
            return false;
        },

        on_remove: function () {
            this.on_blur();
            var index = _.indexOf(this.BuildingBlock.snippets, this.$target.get(0));
            for (var i in this.styles){
                this.styles[i].on_remove();
            }
            delete this.BuildingBlock.snippets[index];

            // remove node and his empty
            var parent,
                node = this.$target.parent()[0];

            this.$target.remove();
            function check(node) {
                if ($(node).outerHeight() > 8) {
                    return false;
                }
                for (var k=0; k<node.children.length; k++) {
                    if (node.children[k].tagName || node.children[k].textContent.match(/[^\s]/)) {
                        return false;
                    }
                }
                return true;
            }
            while (check(node)) {
                parent = node.parentNode;
                parent.removeChild(node);
                node = parent;
            }

            this.$overlay.remove();
            return false;
        },

        /*
        *  drop_and_build_snippet
        *  This method is called just after that a thumbnail is drag and dropped into a drop zone
        *  (after the insertion of this.$body, if this.$body exists)
        */
        drop_and_build_snippet: function () {
            for (var i in this.styles){
                this.styles[i].drop_and_build_snippet();
            }
        },

        /* on_focus
        *  This method is called when the user click inside the snippet in the dom
        */
        on_focus : function () {
            this.$overlay.addClass('oe_active');
            for (var i in this.styles){
                this.styles[i].on_focus();
            }
        },

        /* on_focus
        *  This method is called when the user click outside the snippet in the dom, after a focus
        */
        on_blur : function () {
            for (var i in this.styles){
                this.styles[i].on_blur();
            }
            this.$overlay.removeClass('oe_active');
        },
    });

})();
