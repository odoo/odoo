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
    website.snippet.is_empty_dom = function ($dom) {
        if ($.trim($dom.text()) !== '') return false;
        if ($dom.find('area, base, command, embed, hr, img, input, keygen').length) return false;
        return true;
    };

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
                if (self.editor_busy) {
                    if($selected_target){
                        $selected_target.data('overlay').removeClass('oe_selected');
                    }
                }
                var $target = $(event.srcElement).parents("[data-snippet-id]:first");
                if($target.length && $selected_target != $target){
                    if($selected_target){
                        $selected_target.data('overlay').removeClass('oe_selected');
                    }
                    $selected_target = $target;
                    self.create_overlay($target);
                    $target.data('overlay').addClass('oe_selected');
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
                    if( action === 'insert'){
                        self.activate_insertion_zones({
                            siblings: $snippet.data('selector-siblings'),
                            childs:   $snippet.data('selector-childs')
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
                                $(".oe_drop_zone.oe_hover").after($toInsert);
                                $target = $toInsert;
                            } else {
                                $target = $(".oe_drop_zone.oe_hover").data('target');
                            }

                            if (website.snippet.editorRegistry[snipped_id]) {
                                self.create_overlay($target);
                                var snippet = new website.snippet.editorRegistry[snipped_id](self, $target);
                                snippet.build_snippet($target);
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
                helper:   'clone',
                zIndex:   '1000',
                appendTo: 'body',
                start: function(){
                    var action = $snippet.data('action');
                    if(action === 'insert'){

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
            var child_selector   =  selector.childs   ?  this.parent_of_editable_box + (selector.childs).split(",").join(this.parent_of_editable_box) : false;
            var sibling_selector =  selector.siblings ?  this.parent_of_editable_box + (selector.siblings).split(",").join(this.parent_of_editable_box)  : false;
            var zone_template = "<div class='oe_drop_zone oe_insert'></div>";

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
                    var $zone = $(
                        '<div class="oe_overlay">'+
                        '    <div class="oe_overlay_options">'+
                        '        <ul class="oe_option n w"></ul>'+
                        '        <ul class="oe_option n"></ul>'+
                        '        <ul class="oe_option n e"></ul>'+
                        '    </div>'+
                        '</div>');
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
            }
        },

        /*
        *  start
        *  This method is called after init and _readXMLData
        */
        start: function () {
            if(this.$editor) this.$editor.prependTo(this.$overlay.find(".oe_overlay_options .oe_option.n.w"));
        },

        /*
        *  build_snippet
        *  This method is called just after that a thumbnail is drag and droped into a drop zone
        *  (after the insertion of this.$body, if this.$body exists)
        */
        build_snippet: function ($target) {
            var self = this;
            setTimeout(function () {self.parent.make_active(self.$target);},0);
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

            var $editor = $box.find(".oe_snippet_options");
            $editor.prependTo(this.$overlay.find(".oe_overlay_options .oe_option.n.w"));

            $editor.on('click', '.js_box_remove', function () {
                self.$target.detach();
                self.onBlur();
                self.$target.remove();
            });


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
                            if (current)
                                self.$target.removeClass(val);
                            else
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
        getSize: function () {
            this.grid = this._super();
            var width = this.$target.parents(".row:first").first().outerWidth();

            var grid = [0,1,2,3,4,5,6,7,8,9,10,11,12];
            this.grid.e = [_.map(grid, function (v) {return 'col-md-'+v;}), _.map(grid, function (v) {return width/12*v;})];

            var grid = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11];
            this.grid.w = [_.map(grid, function (v) {return 'col-lg-offset-'+v;}), _.map(grid, function (v) {return width/12*v;}), 12];

            return this.grid;
        },
        resizeHeight: function () {
            var height = 0;
            var $parent = this.$target.parent();
            var $cols = $parent.find('>');
            $cols.css('height', '');
            if ($cols.length <= 1) {
                $parent.css('height', '');
                return;
            }
            var both = '<div class="oe_remove_me" style="overflow: hidden; height: 0;">.</div>';
            $parent.append(both).prepend(both);
            $cols.each(function () {
                if (height < $(this).outerHeight()) {
                    height = $(this).outerHeight();
                }
            });
            $parent.css('height', height + 'px');
            $parent.find('.oe_remove_me').remove();
            $cols.css('height', '99%');
        },
        on_resize: function (compass, beginClass, current) {
            if (compass !== 'e' && compass !== 'w' )
                return;

            var self = this;
            var currentClass = this.grid[compass][0][current];
            var beginSize = Number(beginClass.match(/col-md-([0-9]+)|$/)[1] || 0) + Number(beginClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);

            // don't change the rigth border position when we change the offset (replace col size)
            var colsize = compass === 'w' ?
                    beginSize - Number(currentClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0) :
                    Number(currentClass.match(/col-md-([0-9-]+)|$/)[1] || 0);
            if (colsize > 12) colsize = 12;
            if (colsize < 1) {
                colsize = website.snippet.is_empty_dom(self.$target) ? 0 : 1;
            }
            this.$target.attr("class",
                this.$target.attr("class").replace(/\s*(col-lg-offset-|col-md-)([0-9-]+)/g, '') + ' col-md-' + colsize
            );

            // calculate col size (0 < size <= 12)
            var size = 0;
            var $parent = this.$target.parent();
            _.each(this.grid.e[0], function (val) {
                size += $parent.find('.' + val).length * Number(val.replace(/[^0-9]+/, ''));
            });
            _.each(this.grid.w[0], function (val) {
                size += $parent.find('.' + val).length * Number(val.replace(/[^0-9]+/, ''));
            });

            function change_empty_col ($col) {
                var _size = Number($col.attr("class").match(/col-md-([0-9-]+)|$/)[1] || 0);
                if (12 - (size - _size) > 0) {
                    size -= _size;
                    $col.attr("class", $col.attr("class").replace(/\s*col-md-([0-9-]+)/g, '') + ' col-md-' + (12 - size));
                    size = 12;
                } else if(website.snippet.is_empty_dom($col)) {
                    size -= _size;
                    $col.remove();
                }
            }

            function insert_empty_col () {
                var cleanClass = beginClass.replace(/\s*(col-lg-offset-|col-md-)([0-9-]+)/g, '');
                var $insert = $('<div class="' + cleanClass + '" data-snippet-id="colmd"><p><br/></p></div>');
                $insert.addClass('col-md-'+(12-size));
                size = 12;
                return $insert;
            }

            // change previous or next col if empty
            if (compass === 'w') {
                var $prev = this.$target.prev();
                if ($prev.length) {
                    change_empty_col($prev);
                }
                if(size < 12 && size > 0) {
                    this.$target.before(insert_empty_col());
                }
            } else {
                var $next = this.$target.next();
                if ($next.length) {
                    change_empty_col($next);
                }
                if(size < 12 && size > 0) {
                    this.$target.after(insert_empty_col());
                }
            }
            if(size > 12 || size <= 0) {
                this.$target.attr("class",
                    this.$target.attr("class").replace(/\s*col-md-([0-9-]+)/g, '') + ' col-md-' + (size-12)
                );
            }

            // remove empty col
            if (this.$target.hasClass("col-md-0")) {
                $('body').mouseup();
                setTimeout(function () {
                    self.$overlay.remove();
                    var $div = self.$target.prev();
                    if (!$div.length) {
                        $div = self.$target.next();
                    }
                    self.$target.remove();
                    self.parent.make_active($div);
                },0);
            }

            setTimeout(function () {
                self.resizeHeight();
            },0);
        },
        start: function () {
            var self = this;
            this._super();
            this.resizeHeight();
            $("body").on("save", function () {
                self.$target.parent().css('height', '').find('>').css('height', '');
            });
        },
    });

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
            var $parent = $target.parent();
            if($parent.hasClass('dark')){
                $parent.replaceWith($target);
            }else{
                $parent = $("<div class='dark'></div>");
                $target.after($parent);
                $parent.append($target);
            }
            this._super();
        }
    });

    website.snippet.animationRegistry.vomify = website.snippet.Animation.extend({
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