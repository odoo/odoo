(function () {
    'use strict';

/*  Building block / Snippet Editor
 
    The building blocks appear in the edit bar website. These prebuilt html block
    allowing the designer to easily generate content on a page (drag and drop).
    Options allow snippets to add customizations part html code according to their
    selector (jQuery) and javascript object.
    
    How to create content?

    Designers can add their own html block in the "snippets" (/website/views/snippets.xml).
    The block must be added in one of four menus (structure, content, feature or effect).
    Structure:
        <div>
            <div class="oe_snippet_thumbnail">
                <img class="oe_snippet_thumbnail_img" src="...image src..."/>
                <span class="oe_snippet_thumbnail_title">...Block Name...</span>
            </div>
            <div class="oe_snippet_body">
                ...
                <!-- 
                    The block with class 'oe_snippet_body' is inserted in the page.
                    This class is removed when the block is dropped.
                    The block can be made of any html tag and content. -->
            </div>
        </div>

    How to create options?

    Designers can add their own html block in the "snippet_options" (/website/views/snippets.xml).
    Structure:

        <div data-snippet-option-id='...'           <!-- Required: javascript object id (but javascript
                                                        for this option object is not required) -->
            data-selector="..."                     <!-- Required: jQuery selector.
                                                        Apply options on all The part of html who 
                                                        match with this jQuery selector.
                                                        E.g.: If the selector is div, all div will be selected
                                                        and can be highlighted and assigned an editor.  -->
            data-selector-siblings="..."            <!-- Optional: jQuery selector.
                                                        The html part can be insert or move beside
                                                        the selected html block -->
            data-selector-children="..."            <!-- Optional: jQuery selector.
                                                        The html part can be insert or move inside
                                                        the selected html block -->
            data-selector-vertical-children='...'>  <!-- Optional: jQuery selector.
                                                        The html part can be insert or move inside
                                                        the selected html block. The drop zone is
                                                        displayed vertically -->
                ...
                <li><a href="#">...</a></li>        <!-- Optional: html li list.
                                                        List of menu items displayed in customize
                                                        menu. If the li tag have 'data-class', the
                                                        class is automaticcally added or removed to
                                                        the html content when the user select this item. -->
                ...
                <li class="dropdown-submenu"                <!-- Optional: html li list exemple. !-->
                    data-required="true">                   <!-- Optional: if only one item can be selected
                                                                and can't be unselect. !-->
                    <a tabindex="-1" href="#">...</a>       <!-- bootstrap dropdown button !-->
                    <ul class="dropdown-menu">
                        <li data-value="text_only"><a>...</a></li>      <!-- by default data-value is apply
                                                                            like a class to html block !-->
                    </ul>
                </li>
        </div>

        How to create a javascript object for an options?

        openerp.website.snippet.options["...option-id..."] = website.snippet.Option.extend({
            // start is called when the user click into a block or when the user drop a block 
            // into the page (just after the init method).
            // start is usually used to bind event.
            //
            // this.$target: block html inserted inside the page
            // this.$el: html li list of this options
            // this.$overlay: html editor overlay who content resize bar, customize menu...
            start: function () {},


            // onFocus is called when the user click inside the block inserted in page
            // and when the user drop on block into the page
            onFocus : function () {},


            // onBlur is called when the user click outside the block inserted in page, if
            // the block is focused
            onBlur : function () {},


            // on_clone is called when the snippet is duplicate
            // @variables: $clone is allready inserted is the page
            on_clone: function ($clone) {},


            // on_remove is called when the snippet is removed (dom is removing after this tigger)
            on_remove: function () {},


            // drop_and_build_snippet is called just after that a thumbnail is drag and dropped
            // into a drop zone. The content is already inserted in the page.
            drop_and_build_snippet: function () {},

            // select is called when a user select an item in the li list of options
            // By default, if the li item have a data-value attribute, the data-vlue it's apply
            // like a class to the html block (this.$target)
            // @variables: next_previous = {$next, $prev}
            //      $next = next item selected or false
            //      $prev = previous item selected or false
            select: function (event, next_previous) {}

            // preview is called when a user is on mouse over or mouse out of an item
            // variables: next_previous = {$next, $prev}
            //      $next = next item selected or false
            //      $prev = previous item selected or false
            preview: function (event, next_previous) {}

            // clean_for_save
            // clean_for_save is called just before to save the vue
            // Sometime it's important to remove or add some datas (contentEditable, added 
            // classes to a running animation...)
            clean_for_save: function () {}
        });


    // 'snippet-dropped' is triggered on '#oe_snippets' whith $target as attribute when a snippet is dropped
    // 'snippet-activated' is triggered on '#oe_snippets' (and on snippet) when a snippet is activated

*/

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

    if (!website.snippet) website.snippet = {};
    website.snippet.templateOptions = {};
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

                    var selector = [];
                    var $styles = $html.find("[data-snippet-option-id]");
                    $styles.each(function () {
                        var $style = $(this);
                        var style_id = $style.data('snippet-option-id');
                        website.snippet.templateOptions[style_id] = {
                            'snippet-option-id' : style_id,
                            'selector': $style.data('selector'),
                            '$el': $style,
                            'selector-siblings': $style.data('selector-siblings'),
                            'selector-children': $style.data('selector-children'),
                            'selector-vertical-children': $style.data('selector-vertical-children'),
                            'data': $style.data()
                        };
                        selector.push($style.data('selector'));
                    });
                    $styles.addClass("hidden");
                    website.snippet.globalSelector = selector.join(",");

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

        snippet_have_dropzone: function ($snippet) {
            return (($snippet.data('selector-siblings') && this.dom_filter($snippet.data('selector-siblings')).size() > 0) ||
                    ($snippet.data('selector-children') && this.dom_filter($snippet.data('selector-children')).size() > 0) ||
                    ($snippet.data('selector-vertical-children') && this.dom_filter($snippet.data('selector-vertical-children')).size() > 0));
        },

        bind_snippet_click_editor: function () {
            var self = this;
            var snipped_event_flag;
            $("#wrapwrap").on('click', function (event) {
                if (snipped_event_flag || !event.srcElement) {
                    return;
                }
                snipped_event_flag = true;

                setTimeout(function () {snipped_event_flag = false;}, 0);
                var $target = $(event.srcElement);

                if ($target.parents(".oe_overlay").length) {
                    return;
                }

                if (!$target.is(website.snippet.globalSelector)) {
                    $target = $target.parents(website.snippet.globalSelector).first();
                }

                if (!self.dom_filter($target).length) {
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
            var self = this;
            var options = website.snippet.options;
            var template = website.snippet.templateOptions;
            for (var k in options) {
                if (template[k] && options[k].prototype.clean_for_save !== dummy) {
                    var $snippet = this.dom_filter(template[k].selector);
                    $snippet.each(function () {
                        new options[k](self, null, $(this), k).clean_for_save();
                    });
                }
            }
            $("*[contentEditable], *[attributeEditable]")
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
            $("#oe_snippets").trigger('snippet-activated', $snippet);
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
                    // snippet_selectors => to get selector-siblings, selector-children, selector-vertical-children
                    $snippet = $(this);
                    $toInsert = $snippet.find('.oe_snippet_body').clone();

                    var selector = [];
                    var selector_siblings = [];
                    var selector_children = [];
                    var selector_vertical_children = [];
                    for (var k in website.snippet.templateOptions) {
                        if ($toInsert.is(website.snippet.templateOptions[k].selector)) {
                            selector.push(website.snippet.templateOptions[k].selector);
                            if (website.snippet.templateOptions[k]['selector-siblings'])
                                selector_siblings.push(website.snippet.templateOptions[k]['selector-siblings']);
                            if (website.snippet.templateOptions[k]['selector-children'])
                                selector_children.push(website.snippet.templateOptions[k]['selector-children']);
                            if (website.snippet.templateOptions[k]['selector-vertical-children'])
                                selector_vertical_children.push(website.snippet.templateOptions[k]['selector-vertical-children']);
                        }
                    }

                    action = $snippet.find('.oe_snippet_body').size() ? 'insert' : 'mutate';

                    if( action === 'insert'){
                        if (!selector_siblings.length && !selector_children.length && !selector_vertical_children.length) {
                            console.debug($snippet.data("snippet-id") + " have oe_snippet_body class and have not for insert action"+
                                "data-selector-siblings, data-selector-children or data-selector-vertical-children tag for mutate action");
                            return;
                        }
                        self.activate_insertion_zones({
                            siblings: selector_siblings.join(","),
                            children: selector_children.join(","),
                            vertical_children: selector_vertical_children.join(","),
                        });

                    } else if( action === 'mutate' ){
                        if (!$snippet.data('selector')) {
                            console.debug($snippet.data("snippet-id") + " have not oe_snippet_body class and have not data-selector tag");
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
                        $target = $toInsert;

                        setTimeout(function () {
                            $("#oe_snippets").trigger('snippet-dropped', $target);

                            website.snippet.start_animation(true, $target);
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
                            self.create_overlay($target);
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
            var $targets = this.dom_filter(selector);
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


    website.snippet.options = {};
    website.snippet.Option = openerp.Class.extend({
        // initialisation (don't overwrite)
        init: function (BuildingBlock, editor, $target, snippet_id) {
            this.BuildingBlock = BuildingBlock;
            this.editor = editor;
            this.$target = $target;
            var styles = this.$target.data("snippet-option-ids") || {};
            styles[snippet_id] = this;
            this.$target.data("snippet-option-ids", styles);
            this.$overlay = this.$target.data('overlay');
            this['snippet-option-id'] = snippet_id;
            var $option = website.snippet.templateOptions[snippet_id].$el;
            this.$el = $option.find(">li").clone();
            this.data = $option.data();

            this.required = this.$el.data("required");

            this.set_active();
            this.$el.find('li[data-value] a').on('mouseenter mouseleave click', _.bind(this._mouse, this));
            this.$el.not(':not([data-value])').find("a").on('mouseenter mouseleave click', _.bind(this._mouse, this));
            this.$target.on('snippet-style-reset', _.bind(this.set_active, this));

            this.start();
        },
        _mouse: function (event) {
            var self = this;

            if (event.type === 'mouseleave') {
                if (!this.over) return;
                this.over = false;
            } else if (event.type === 'click') {
                this.over = false;
            }else {
                this.over = true;
            }

            var $prev, $next;
            if (event.type === 'mouseleave') {
                $prev = $(event.currentTarget).parent();
                $next = this.$el.find("li[data-value].active");
            } else {
                $prev = this.$el.find("li[data-value].active");
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
                this.select({'$next': $next, '$prev': $prev});
            } else {
                setTimeout(function () {
                    self.$target.trigger("snippet-style-preview", [self, np]);
                },0);
                this.preview(np);
            }
        },
        /* set_active
        *  select and set item active or not (add highlight item and his parents)
        *  called before start
        */
        set_active: function () {
            var self = this;
            this.$el.find('li').removeClass("active");
            var $active = this.$el.find('li[data-value]')
                .filter(function () {
                    var $li = $(this);
                    return  ($li.data('value') && self.$target.hasClass($li.data('value')));
                })
                .first()
                .addClass("active");
            this.$el.find('li:has(li[data-value].active)').addClass("active");
        },

        start: function () {
        },

        onFocus : function () {
        },

        onBlur : function () {
        },

        on_clone: function ($clone) {
        },

        on_remove: function () {
        },

        drop_and_build_snippet: function () {
        },

        select: function (np) {
            var self = this;
            // add or remove html class
            if (np.$prev && this.required) {
                this.$target.removeClass(np.$prev.data('value' || ""));
            }
            if (np.$next) {
                this.$target.addClass(np.$next.data('value') || "");
            }
        },

        preview: function (np) {
            var self = this;

            // add or remove html class
            if (np.$prev) {
                this.$target.removeClass(np.$prev.data('value') || "");
            }
            if (np.$next) {
                this.$target.addClass(np.$next.data('value') || "");
            }
        },

        clean_for_save: dummy
    });

    website.snippet.options.background = website.snippet.Option.extend({
        _get_bg: function () {
            return this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
        },
        _set_bg: function (src) {
            this.$target.css("background-image", src && src !== "" ? 'url(' + src + ')' : "");
        },
        start: function () {
            this._super();
            var src = this._get_bg();
            this.$el.find("li[data-value].active.oe_custom_bg").data("src", src);
        },
        select: function(np) {
            var self = this;
            this._super(np);
            if (np.$next) {
                if (np.$next.hasClass("oe_custom_bg")) {
                    var $image = $('<img class="hidden"/>');
                    $image.attr("src", np.$prev ? np.$prev.data("src") : '');
                    $image.appendTo(self.$target);

                    self.element = new CKEDITOR.dom.element($image[0]);
                    var editor = new website.editor.MediaDialog(self, self.element);
                    editor.appendTo(document.body);
                    editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');

                    $image.on('saved', self, function (o) {
                        var src = $image.attr("src");
                        self._set_bg(src);
                        np.$next.data("src", src);
                        self.$target.trigger("snippet-style-change", [self, np]);
                        $image.remove();
                    });
                    editor.on('cancel', self, function () {
                        if (!np.$prev || np.$prev.data("src") === "") {
                            self.$target.removeClass(np.$next.data("value"));
                            self.$target.trigger("snippet-style-change", [self, np]);
                        }
                        $image.remove();
                    });
                } else {
                    this._set_bg(np.$next.data("src"));
                }
            } else {
                this._set_bg(false);
                this.$target.removeClass(np.$prev.data("value"));
            }
        },
        preview: function (np) {
            this._super(np);
            if (np.$next) {
                this._set_bg(np.$next.data("src"));
            }
        },
        set_active: function () {
            var self = this;
            var bg = self.$target.css("background-image");
            this.$el.find('li').removeClass("active");
            this.$el.find('li').removeClass("btn-primary");
            var $active = this.$el.find('li[data-value]')
                .filter(function () {
                    var $li = $(this);
                    return  ($li.data('src') && bg.indexOf($li.data('src')) >= 0) ||
                            (!$li.data('src') && self.$target.hasClass($li.data('value')));
                })
                .first();
            if (!$active.length) {
                $active = this.$target.css("background-image") !== 'none' ?
                    this.$el.find('li[data-value].oe_custom_bg') :
                    this.$el.find('li[data-value=""]');
            }

            //don't set active on an OpenDialog link, else it not possible to click on it again after.
            // TODO in Saas-4 - Once bootstrap is in less
            //      - add a class active-style to get the same display but without the active behaviour used by bootstrap in JS.
            var classStr = _.string.contains($active[0].className, "oe_custom_bg") ? "btn-primary" : "active";
            $active.addClass(classStr);
            this.$el.find('li:has(li[data-value].active)').addClass(classStr);
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
            this.$target.find('.oe_structure, .content>.row, [data-slide]').attr('contentEditable', 'true');
        },
        clean_for_save: function () {
            this._super();
            $(".carousel").find(".item").removeClass("next prev left right active");
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

            this.$el.find(".js_add").on('click', function () {self.on_add_slide(); return false;});
            this.$el.find(".js_remove").on('click', function () {self.on_remove_slide(); return false;});

            this.$target.carousel('pause');
            this.rebind_event();
        },
        on_add_slide: function () {
            var self = this;
            var cycle = this.$inner.find('.item').length;
            var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
            var index = $active.index();
            this.$target.find('.carousel-control, .carousel-indicators').removeClass("hidden");
            this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');

            var $clone = this.$target.find(".item.active").clone();

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
    website.snippet.options.carousel = website.snippet.options.slider.extend({
        getSize: function () {
            this.grid = this._super();
            this.grid.size = 8;
            return this.grid;
        },
        clean_for_save: function () {
            this._super();
            this.$target.css("background-image", "");
            this.$target.removeClass(this._class);
        },
        load_style_options : function () {
            this._super();
            $(".snippet-style-size li[data-value='']").remove();
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
                if (style['snippet-option-id'] === "size") return;
                if (style['snippet-option-id'] === "background") {
                    $active.css("background-image", self.$target.css("background-image"));
                }
                if (np.$prev) {
                    $active.removeClass(np.$prev.data("value"));
                }
                if (np.$next) {
                    $active.addClass(np.$next.data("value"));
                    add_class(np.$next.data("value"));
                }
            });
            this.$target.on('slid', function () { // slide.bs.carousel
                var $active = self.$target.find(".item.active");
                self.$target
                    .css("background-image", $active.css("background-image"))
                    .removeClass(add_class($active.attr("class")))
                    .addClass($active.attr("class"))
                    .trigger("snippet-style-reset");

                self.$target.carousel("pause");
            });
            this.$target.trigger('slid');
        },
        on_add_slide: function () {
            var $clone = this._super();

            // choose an other background
            var bg = this.$target.data("snippet-option-ids").background;
            if (!bg) return $clone;

            var $styles = bg.$el.find("li[data-value]:not(.oe_custom_bg)");
            var styles_index = $styles.index($styles.filter(".active")[0]);
            $styles.removeClass("active");
            var $select = $($styles[styles_index >= $styles.length-1 ? 0 : styles_index+1]);
            $select.addClass("active");
            $clone.css("background-image", $select.data("src") ? "url('"+ $select.data("src") +"')" : "");
            $clone.addClass($select.data("value") || "");

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
        onFocus : function () {
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
            if (!this.$target.siblings().length) {
                var $parent = this.$target.parents(".row:first");
                if($parent.find("[class*='col-md']").length > 1) {
                    return false;
                } else {
                    if (!$parent.data("snippet-editor")) {
                        this.BuildingBlock.create_overlay($parent);
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

    website.snippet.options["resize"] = website.snippet.options.marginAndResize.extend({
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
            this.$target.on('snippet-style-change snippet-style-preview', function () {
                self.$target.data("snippet-view").set_values();
            });
            this.$target.attr('contentEditable', 'false');

            this.$target.find('> div > .oe_structure').attr('contentEditable', 'true'); // saas-3 retro-compatibility

            this.$target.find('> div > div:not(.oe_structure) > .oe_structure').attr('contentEditable', 'true');
        },
        scroll: function () {
            var self = this;
            var $ul = this.$el.find('ul[name="parallax-scroll"]');
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

    website.snippet.options.transform = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this._super();

            this.$el.find(".clear-style").click(function (event) {
                self.$target.removeClass("fa-spin").attr("style", "");
                self.resetTransfo();
            });

            this.$el.find(".style").click(function (event) {
                var settings = self.$target.data("transfo").settings;
                self.$target.transfo({ hide: (settings.hide = !settings.hide) });
            });

            this.$overlay.find('.oe_snippet_clone, .oe_handles').addClass('hidden');

            this.$overlay.find('[data-toggle="dropdown"]')
                .on("mousedown", function () {
                    self.$target.transfo("hide");
                });
        },
        resetTransfo: function () {
            var self = this;
            this.$target.transfo("destroy");
            this.$target.transfo({
                hide: true,
                callback: function () {
                    var pos = $(this).data("transfo").$center.offset();
                    self.$overlay.css({
                        'top': pos.top,
                        'left': pos.left,
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
        onFocus : function () {
            this.resetTransfo();
        },
        onBlur : function () {
            this.$target.transfo("hide");
        },
    });

    website.snippet.options.media = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this._super();

            website.snippet.start_animation(true, this.$target);

            $(document.body).on("media-saved", self, function (event, prev , item) {
                self.editor.onBlur();
                self.BuildingBlock.make_active(false);
                if (self.$target.parent().data("oe-field") !== "image") {
                    self.BuildingBlock.make_active($(item));
                }
            });

            this.$el.find(".edition").click(function (event) {
                event.preventDefault();
                event.stopPropagation();
                self.element = new CKEDITOR.dom.element(self.$target[0]);
                new website.editor.MediaDialog(self, self.element).appendTo(document.body);
            });
        },
        onFocus : function () {
            var self = this;
            if (this.$target.parent().data("oe-field") === "image") {
                this.$overlay.addClass("hidden");
                self.element = new CKEDITOR.dom.element(self.$target[0]);
                new website.editor.MediaDialog(self, self.element).appendTo(document.body);
                self.BuildingBlock.make_active(false);
            }
        },
    });


    website.snippet.Editor = openerp.Class.extend({
        init: function (BuildingBlock, dom) {
            this.BuildingBlock = BuildingBlock;
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
        */
        _readXMLData: function() {
            var self = this;
            if(this && this.BuildingBlock && this.BuildingBlock.$snippets) {
                this.$el = this.BuildingBlock.$snippets.filter(function () { return $(this).data("snippet-id") == self.snippet_id; }).clone();
            }
            var $options = this.$overlay.find(".oe_overlay_options");
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
                vertical_children: self.selector_vertical_children,
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
            this.selector_vertical_children = [];
            _.each(website.snippet.templateOptions, function (val) {
                if (!self.$target.is(val.selector)) {
                    return;
                }
                if (val['selector-siblings']) self.selector_siblings.push(val['selector-siblings']);
                if (val['selector-children']) self.selector_children.push(val['selector-children']);
                if (val['selector-vertical-children']) self.selector_vertical_children.push(val['selector-vertical-children']);

                var style = val['snippet-option-id'];
                var Editor = website.snippet.options[style] || website.snippet.Option;
                var editor = self.styles[style] = new Editor(self.BuildingBlock, self, self.$target, style);
                $ul.append(editor.$el.addClass("snippet-style-" + style));
            });
            this.selector_siblings = this.selector_siblings.join(",");
            if (this.selector_siblings === "")
                this.selector_siblings = false;
            this.selector_children = this.selector_children.join(",");
            if (this.selector_children === "")
                this.selector_children = false;
            this.selector_vertical_children = this.selector_vertical_children.join(",");
            if (this.selector_vertical_children === "")
                this.selector_vertical_children = false;

            if (!this.selector_siblings && !this.selector_children && !this.selector_vertical_children) {
                this.$overlay.find(".oe_snippet_move").addClass('hidden');
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
            this.onBlur();
            var index = _.indexOf(this.BuildingBlock.snippets, this.$target.get(0));
            for (var i in this.styles){
                this.styles[i].on_remove();
            }
            delete this.BuildingBlock.snippets[index];
            this.$target.remove();
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

        /* onFocus
        *  This method is called when the user click inside the snippet in the dom
        */
        onFocus : function () {
            this.$overlay.addClass('oe_active');
            for (var i in this.styles){
                this.styles[i].onFocus();
            }
        },

        /* onFocus
        *  This method is called when the user click outside the snippet in the dom, after a focus
        */
        onBlur : function () {
            for (var i in this.styles){
                this.styles[i].onBlur();
            }
            this.$overlay.removeClass('oe_active');
        },
    });

})();
