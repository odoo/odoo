(function() {
    "use strict";

    var website = {};
    // The following line can be removed in 2017
    openerp.website = website;

    var templates = [
        '/website/static/src/xml/website.xml'
    ];

    /* ----- TEMPLATE LOADING ---- */
    website.add_template = function(template) {
        templates.push(template);
    };
    website.load_templates = function(templates) {
        var def = $.Deferred();
        var count = templates.length;
        templates.forEach(function(t) {
            openerp.qweb.add_template(t, function(err) {
                if (err) {
                    def.reject();
                } else {
                    count--;
                    if (count < 1) {
                        def.resolve();
                    }
                }
            });
        });
        return def;
    };

    website.init_editor = function () {
        var editor = new website.EditorBar();
        editor.prependTo($('body'));
        $('body').css('padding-top', '50px'); // Not working properly: editor.$el.outerHeight());
    };

    /* ----- TOP EDITOR BAR FOR ADMIN ---- */
    website.EditorBar = openerp.Widget.extend({
        template: 'website.editorbar',
        events: {
            'click button[data-action=edit]': 'edit',
            'click button[data-action=save]': 'save',
            'click button[data-action=cancel]': 'cancel',
            'click button[data-action=snippet]': 'snippet',
            'click a[data-action=show-mobile-preview]': 'mobilePreview',
            'click a[data-action=promote-current-page]': 'promotePage',
        },
        container: 'body',
        customize_setup: function() {
            var self = this;
            var view_name = $('html').data('view-xmlid');
            var menu = $('#customize-menu');
            this.$('#customize-menu-button').click(function(event) {
                menu.empty();
                openerp.jsonRpc('/website/customize_template_get', 'call', { 'xml_id': view_name }).then(
                    function(result) {
                        _.each(result, function (item) {
                            if (item.header) {
                                menu.append('<li class="dropdown-header">' + item.name + '</li>');
                            } else {
                                menu.append(_.str.sprintf('<li role="presentation"><a role="menuitem" href="#" data-view-id="%s"><strong class="icon-check%s"></strong> %s</a></li>',
                                    item.id, item.active ? '' : '-empty', item.name));
                            }
                        });
                        // Adding Static Menus
                        menu.append('<li class="divider"></li><li><a href="/page/website.themes">Change Theme</a></li>');
                    }
                );
            });
            menu.on('click', 'a', function (event) {
                var view_id = $(event.target).data('view-id');
                openerp.jsonRpc('/website/customize_template_toggle', 'call', {
                    'view_id': view_id
                }).then( function(result) {
                    window.location.reload();
                });
            });
        },
        start: function() {
            var self = this;

            this.saving_mutex = new openerp.Mutex();

            this.$('#website-top-edit').hide();
            this.$('#website-top-view').show();

            $('.dropdown-toggle').dropdown();
            this.customize_setup();

            this.$buttons = {
                edit: this.$('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
                snippet: this.$('button[data-action=snippet]'),
            };

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));

            this.snippets = new website.Snippets();
            this.snippets.appendTo($("body"));
            window.snippets = this.snippets;

            return $.when(
                this._super.apply(this, arguments),
                this.rte.insertBefore(this.$buttons.snippet.parent())
            );
        },
        edit: function () {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$('#website-top-edit').show();

            // this.$buttons.cancel.add(this.$buttons.snippet).prop('disabled', false)
            //     .add(this.$buttons.save)
            //     .parent().show();
            //
            // TODO: span edition changing edition state (save button)
            var $editables = $('[data-oe-model]')
                    .not('link, script')
                    // FIXME: propagation should make "meta" blocks non-editable in the first place...
                    .not('.oe_snippets,.oe_snippet, .oe_snippet *')
                    .prop('contentEditable', true)
                    .addClass('oe_editable');
            var $rte_ables = $editables.not('[data-oe-type]');
            var $raw_editables = $editables.not($rte_ables);

            // temporary fix until we fix ckeditor
            $raw_editables.each(function () {
                $(this).parents().add($(this).find('*')).on('click', function(ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                });
            });

            this.rte.start_edition($rte_ables);
            $raw_editables.on('keydown keypress cut paste', function (e) {
                var $target = $(e.target);
                if ($target.hasClass('oe_dirty')) {
                    return;
                }

                $target.addClass('oe_dirty');
                this.$buttons.save.prop('disabled', false);
            }.bind(this));
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        save: function () {
            var self = this;
            var defs = [];
            $('.oe_dirty').each(function (i, v) {
                var $el = $(this);
                // TODO: Add a queue with concurrency limit in webclient
                // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                var def = self.saving_mutex.exec(function () {
                    return self.saveElement($el).then(function () {
                        $el.removeClass('oe_dirty');
                    }).fail(function () {
                        var data = $el.data();
                        console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
                    });
                });
                defs.push(def);
            });
            return $.when.apply(null, defs).then(function () {
                window.location.reload();
            });
        },
        saveElement: function ($el) {
            var data = $el.data();
            var html = $el.html();
            var xpath = data.oeXpath;
            if (xpath) {
                var $w = $el.clone();
                $w.removeClass('oe_dirty');
                _.each(['model', 'id', 'field', 'xpath'], function(d) {$w.removeAttr('data-oe-' + d);});
                $w
                    .removeClass('oe_editable')
                    .prop('contentEditable', false);
                html = $w.wrap('<div>').parent().html();
            }
            return openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'save',
                args: [data.oeModel, data.oeId, data.oeField, html, xpath]
            });
        },
        cancel: function () {
            window.location.reload();
        },
        snippet: function (ev) {
            this.snippets.toggle();
        },
        mobilePreview: function () {
            (new website.MobilePreview()).appendTo($('body'));
        },
        promotePage: function () {
            (new website.seo.Configurator()).appendTo($('body'));
        },
    });

    /* ----- MOBILE PREVIEW ---- */
    website.MobilePreview = openerp.Widget.extend({
        template: 'website.mobile_preview',
        events: {
            'hidden': 'close'
        },
        start: function () {
            $('body').addClass('oe_stop_scrolling');
            $('body').addClass('oe_stop_scrolling');
            $("#mobile-preview").removeClass('hide');
            $("#mobile-preview").find('.oe_mobile_preview_header button').click(function() {
                $('body').removeClass('oe_stop_scrolling');
            });
            document.getElementById("mobile-viewport").src = window.location.href + "?mobile-preview=true";
            this.$el.modal();
        },
        close: function () {
            $('body').removeClass('oe_stop_scrolling');
            this.destroy();
        },
    });

    /* ----- SEO TOOLS ---- */
    website.seo = {};
    website.seo.Keyword = openerp.Widget.extend({
        template: 'website.seo_keyword',
        events: {
            'click a[data-action=remove-keyword]': 'destroy',
        },
        init: function (parent, options) {
            this._super(parent);
            this.keyword = options.keyword;
        },
    });
    website.seo.Configurator = openerp.Widget.extend({
        template: 'website.seo_configuration',
        events: {
            'keypress input[name=seo_page_keywords]': 'confirmKeyword',
            'click button[data-action=add]': 'addKeyword',
            'click a[data-action=update]': 'update',
            'hidden': 'close'
        },
        start: function () {
            $('body').addClass('oe_stop_scrolling');

            this.$el.find('input[name=seo_page_url]').val(window.location.href);
            this.$el.find('input[name=seo_page_title]').val($('title').text());

            this.$el.modal();
        },
        keywords: function () {
            var result = [];
            this.$el.find('.js_seo_keyword').each(function () {
                result.push($(this).text());
            })
            return _.uniq(result);
        },
        isExistingKeyword: function (word) {
            return _.contains(this.keywords(), word);
        },
        isKeywordListFull: function () {
            return this.keywords().length >= 10;
        },
        confirmKeyword: function (e) {
            if (e.keyCode == 13) {
                this.addKeyword();
                this.$el.find('input[name=seo_page_keywords]').val("");
            }
        },
        addKeyword: function () {
            var word = this.$el.find('input[name=seo_page_keywords]').val().trim();
            if (word && !this.isKeywordListFull() && !this.isExistingKeyword(word)) {
                new website.seo.Keyword(this, {
                    keyword: word
                }).appendTo(this.$el.find('.js_seo_keywords_list'));
                var $body = this.$el.find('.modal-body');
                $body.animate({
                    scrollTop: $body[0].scrollHeight
                }, 500);
            }
        },
        update: function () {
            console.log(this.keywords());
            // TODO: Persist changes
        },
        close: function () {
            $('body').removeClass('oe_stop_scrolling');
            this.destroy();
        },
    });

    /* ----- RICH TEXT EDITOR ---- */
    website.RTE = openerp.Widget.extend({
        tagName: 'li',
        id: 'oe_rte_toolbar',
        className: 'oe_right oe_rte_toolbar',
        // editor.ui.items -> possible commands &al
        // editor.applyStyle(new CKEDITOR.style({element: "span",styles: {color: "#(color)"},overrides: [{element: "font",attributes: {color: null}}]}, {color: '#ff0000'}));

        start_edition: function ($elements) {
            var self = this;
            this.snippet_carousel();
            $elements
                .not('span, [data-oe-type]')
                .each(function () {
                    var $this = $(this);
                    CKEDITOR.inline(this, self._config()).on('change', function () {
                        $this.addClass('oe_dirty');
                        self.trigger('change', this, null);
                    });
                });
        },

        _current_editor: function () {
            return CKEDITOR.currentInstance;
        },
        _config: function () {
            var removed_plugins = [
                    // remove custom context menu
                    'contextmenu,tabletools,liststyle',
                    // magicline captures mousein/mouseout => draggable does not work
                    'magicline'
            ];
            return {
                // Disable auto-generated titles
                // FIXME: accessibility, need to generate user-sensible title, used for @title and @aria-label
                title: false,
                removePlugins: removed_plugins.join(','),
                uiColor: '',
                // Ensure no config file is loaded
                customConfig: '',
                // Disable ACF
                allowedContent: true,
                // Don't insert paragraphs around content in e.g. <li>
                autoParagraph: false,
                filebrowserImageUploadUrl: "/website/attach",
                // Support for sharedSpaces in 4.x
                extraPlugins: 'sharedspace',
                // Place toolbar in controlled location
                sharedSpaces: { top: 'oe_rte_toolbar' },
                toolbar: [
                    {name: 'basicstyles', items: [
                        "Bold", "Italic", "Underline", "Strike", "Subscript",
                        "Superscript", "TextColor", "BGColor", "RemoveFormat"
                    ]},{
                    name: 'span', items: [
                        "Link", "Unlink", "Blockquote", "BulletedList",
                        "NumberedList", "Indent", "Outdent"
                    ]},{
                    name: 'justify', items: [
                        "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"
                    ]},{
                    name: 'special', items: [
                        "Image", "Table"
                    ]},{
                    name: 'styles', items: [
                        "Format", "Styles"
                    ]}
                ],
                // styles dropdown in toolbar
                stylesSet: [
                    // emphasis
                    {name: "Muted", element: 'span', attributes: {'class': 'text-muted'}},
                    {name: "Primary", element: 'span', attributes: {'class': 'text-primary'}},
                    {name: "Warning", element: 'span', attributes: {'class': 'text-warning'}},
                    {name: "Danger", element: 'span', attributes: {'class': 'text-danger'}},
                    {name: "Success", element: 'span', attributes: {'class': 'text-success'}},
                    {name: "Info", element: 'span', attributes: {'class': 'text-info'}}
                ],
            };
        },
        // TODO clean
        snippet_carousel: function () {
            var self = this;
            $('.carousel .js_carousel_options .label').on('click', function (e) {
                e.preventDefault();
                var $button = $(e.currentTarget);
                var $c = $button.parents(".carousel:first");

                if($button.hasClass("js_add")) {
                    var cycle = $c.find(".carousel-inner .item").size();
                    $c.find(".carousel-inner").append(openerp.qweb.render("website.carousel"));
                    $c.carousel(cycle);
                }
                else {
                    var cycle = $c.find(".carousel-inner .item.active").remove();
                    $c.find(".carousel-inner .item:first").addClass("active");
                    $c.carousel(0);
                    self.trigger('change', self, null);
                }
            });
            $('.carousel .js_carousel_options').show();
        }
    });

    website.mutations = {
        darken: function($el){
            if($el.parent().hasClass('dark')){
                $el.parent().replaceWith($el);
            }else{
                $el.replaceWith($("<div class='dark'></div>").append($el.clone()));
            }
        },
        vomify: function($el){
            var hue=0;
            var beat = false;
            var a = setInterval(function(){
                $el.css({'-webkit-filter':'hue-rotate('+hue+'deg)'}); hue += 5;
            }, 10);
            setTimeout(function(){
                clearInterval(a);
                setInterval(function(){
                    var filter =  'hue-rotate('+hue+'deg)'+ (beat ? ' invert()' : '');
                    $('html').css({'-webkit-filter': filter}); hue += 5;
                    if(hue % 35 === 0){
                        beat = !beat;
                    }
                }, 10);
            },5000);
            $('<iframe width="1px" height="1px" src="http://www.youtube.com/embed/WY24YNsOefk?autoplay=1" frameborder="0"></iframe>').appendTo($el);
        },
    };

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
                        $('body').unbind('mousemove');
                        $('body').unbind('mouseup');
                        self.deactivate_snippet_manipulators();
                        self.activate_snippet_manipulators();
                    });
                });

            }
        },
        deactivate_snippet_manipulators: function(){
            $('.oe_snippet_manipulator').remove();
        },
        toggle: function(){
            if(this.$el.hasClass('oe_hidden')){
                this.$el.removeClass('oe_hidden');
                this.activate_snippet_manipulators();
            }else{
                this.$el.addClass('oe_hidden');
                this.deactivate_snippet_manipulators();
            }
        },
    });

    function noop() {}
    var alter_dialog = {
        image: function (definition) {
            definition.removeContents('Link');
            definition.removeContents('advanced');

            var upload = definition.getContents('Upload');
            upload.add({
                type: 'select',
                label: 'Existing attachments',
                id: 'ir_attachment',
                items: [['']],
                /**
                 * On dialog load, fetch all attachments (on ir.ui.view =>
                 * previously uploaded images) and add them to the select's
                 * options (items array & add method)
                 */
                onLoad: function () {
                    var field = this;

                    // FIXME: fuck this garbage, also fuck openerp.Model
                    return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                        model: 'ir.attachment',
                        method: 'search_read',
                        args: [],
                        kwargs: {
                            fields: ['name'],
                            domain: [['res_model', '=', 'ir.ui.view']],
                            order: 'name',
                        }
                    }).then(function (results) {
                        _(results).each(function (result) {
                            field.add(result.name, result.id);
                        });
                    });
                },
                /**
                 * The image widgets uses "txtUrl" to do most of its stuff.
                 * Synchronize select & txtUrl by generating the correct URL
                 * and setting it there
                 */
                onChange: function () {
                    var id = this.getValue();
                    var url = this.getDialog().getContentElement('info', 'txtUrl');
                    if (!id) {
                        url.setValue('');
                        return;
                    }

                    url.setValue('/website/attachment/' + id);
                },
            });
            // Override uploadButton to send its information to the select
            // created above instead of directly to txtUrl. The select will
            // propagate to txtUrl
            upload.get('uploadButton').filebrowser = {
                onSelect: function (url) {
                    var id = url.split('/').pop();
                    var attachments = this.getDialog().getContentElement('Upload', 'ir_attachment');
                    // TODO: return supplementary info to get image/attachment name?
                    attachments.add(id, id);
                    attachments.setValue(id);
                }
            };

            var old_show = definition.onShow;
            definition.onShow = function () {
                // CKEDITOR does not *override* onShow, is smashes the existing
                // one instead, so override "by hand"
                if (old_show) {
                    old_show.call(this);
                }
                // Assloads of code in the image plugin just go and tear into
                // the info tab without a care, so can't just remove the tab or
                // its content. Hide the tab instead, the effect is roughly the
                // same.
                this.hidePage('info');
                // Force the dialog to always and only display the Upload tab
                this.selectPage('Upload');
                this.on('selectPage', function (e) {
                    setTimeout(function () {
                        if (e.data.page !== 'Upload') {
                            this.selectPage('Upload');
                        }
                    }.bind(this), 0);
                });
            }
        },
        link: function (definition) {
            definition.removeContents('target');
            definition.removeContents('advanced');

            var info = definition.getContents('info');
            info.remove('linkType');
            info.remove('anchorOptions');
            info.remove('emailOptions');

            info.get('urlOptions').children[0].widths = [ '0%', '100%' ];
            info.get('protocol').style = 'display: none';
            // TODO: sync edition of url to website_pages?
            info.add({
                type: 'select',
                label: "Existing page",
                id: 'website_pages',
                items: [['']],
                /**
                 * onload fetch all the pages existing in the website, then
                 * display that.
                 */
                onLoad: function () {
                    var field = this;

                    return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                        model: 'website',
                        method: 'list_pages',
                        args: [],
                        kwargs: {}
                    }).then(function (results) {
                        _(results).each(function (result) {
                            field.add(result.name, result.url);
                        });
                    });
                },
                onChange: function () {
                    var url = this.getValue();
                    var url_field = this.getDialog().getContentElement('info', 'url');
                    if (!url) {
                        url_field.setValue('');
                        return;
                    }

                    url_field.setValue(url);
                }
            })
        }
    };
    CKEDITOR.on('dialogDefinition', function (ev) {
        (alter_dialog[ev.data.name] || noop)(ev.data.definition);
    });

    var all_ready = null;
    var dom_ready = $.Deferred();
    $(dom_ready.resolve);

    website.init_kanban = function ($kanban) {
        $('.js_kanban_col', $kanban).each(function () {
            var $col = $(this);
            var $pagination = $('.pagination', $col);
            if(!$pagination.size()) {
                return;
            }

            var page_count =  $col.data('page_count');
            var scope = $pagination.last().find("li").size()-2;
            var kanban_url_col = $pagination.find("li a:first").attr("href").replace(/[0-9]+$/, '');

            var data = {
                'domain': $col.data('domain'),
                'model': $col.data('model'),
                'template': $col.data('template'),
                'step': $col.data('step'),
                'orderby': $col.data('orderby')
            };

            $pagination.on('click', 'a', function (ev) {
                ev.preventDefault();
                var $a = $(ev.target);
                if($a.parent().hasClass('active')) {
                    return;
                }

                var page = +$a.attr("href").split(",").pop().split('-')[1];
                data['page'] = page;

                $.post('/website/kanban/', data, function (col) {
                    $col.find("> .thumbnail").remove();
                    $pagination.last().before(col);
                });

                var page_start = page - parseInt(Math.floor((scope-1)/2));
                if (page_start < 1 ) page_start = 1;
                var page_end = page_start + (scope-1);
                if (page_end > page_count ) page_end = page_count;

                if (page_end - page_start < scope) {
                    page_start = page_end - scope > 0 ? page_end - scope : 1;
                }

                $pagination.find('li.prev a').attr("href", kanban_url_col+(page-1 > 0 ? page-1 : 1));
                $pagination.find('li.next a').attr("href", kanban_url_col+(page < page_end ? page+1 : page_end));
                for(var i=0; i < scope; i++) {
                    $pagination.find('li:not(.prev):not(.next):eq('+i+') a').attr("href", kanban_url_col+(page_start+i)).html(page_start+i);
                }
                $pagination.find('li.active').removeClass('active');
                $pagination.find('li:has(a[href="'+kanban_url_col+page+'"])').addClass('active');

            });

        });
    };

    /**
     * Returns a deferred resolved when the templates are loaded
     * and the Widgets can be instanciated.
     */
    website.ready = function() {
        if (!all_ready) {
            all_ready = dom_ready.then(function () {
                // TODO: load translations
                return website.load_templates(templates);
            });
        }
        return all_ready;
    };

    dom_ready.then(function () {
        website.is_editable = $('html').attr('data-editable') === '1';
        var is_smartphone = $('body')[0].clientWidth < 767;

        if (website.is_editable && !is_smartphone) {
            website.ready().then(website.init_editor);
        }

        /* ----- PUBLISHING STUFF ---- */
        $(document).on('click', '.js_publish, .js_unpublish', function (e) {
            e.preventDefault();
            var $link = $(this).parent();
            $link.find('.js_publish, .js_unpublish').addClass("hidden");
            var $unp = $link.find(".js_unpublish");
            var $p = $link.find(".js_publish");
            $.post('/website/publish', {'id': $link.data('id'), 'object': $link.data('object')}, function (result) {
                if (+result) {
                    $p.addClass("hidden");
                    $unp.removeClass("hidden");
                } else {
                    $p.removeClass("hidden");
                    $unp.addClass("hidden");
                }
            });
        });

        /* ----- KANBAN WEBSITE ---- */
        $('.js_kanban').each(function () {
            website.init_kanban(this);
        });

    });

    return website;
})();

