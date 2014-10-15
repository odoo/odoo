(function () {
    'use strict';
    var website = openerp.website;

    website.if_dom_contains('#email_designer', function () {

        // extract characcter(content) of FontAwesome from the cheatsheet
        function getFACharacter(fa_class) {
            var sheets = document.styleSheets;
            for (var i = 0; i < sheets.length; i++) {
                var rules = sheets[i].rules || sheets[i].cssRules;
                if (rules) {
                    for (var r = 0; r < rules.length; r++) {
                        if (rules[r].cssText.indexOf(fa_class) > -1){
                            return rules[r].cssText.replace(/[a-zA-Z{}"'-.:;]/g,"").trim();
                        }
                    }
                }
            }
        }

        //Get selected image in summernote
        function getImgTarget () {
            return $(".note-control-selection").data('target');
        }

        //To Remove Table handler classes as we do not want summernote table handlers here.
        var current_theme = false;
        var fn_popover_update = $.summernote.eventHandler.popover.update;
        $.summernote.eventHandler.popover.update = function ($popover, oStyle, isAirMode) {
            fn_popover_update.call(this, $popover, oStyle, isAirMode);
            $("span.o_table_handler, div.note-table").remove()
        };

        //To load snippets based on selected mail theme
        website.snippet.BuildingBlock.include({
            _get_snippet_url: function () {
                var url_data = website.parseQS(window.location.search.substring(1));
                if ( url_data.theme_id && url_data.theme_id != 'basic_theme') {
                    current_theme = url_data.theme_id;
                    load_qweb([current_theme + "_colors"]);
                    return '/website_mail/snippets/' + url_data.theme_id;
                }
                return '/website_mail/snippets';
            },
            fetch_snippet_templates:function(){
                this._super().then(function(){
                    $(document).off("mouseup", ".o_default_snippet_text");
                });
            },
        });

        //To load custom color palette based on theme
        var fn_createPalette = $.summernote.renderer.createPalette;
        $.summernote.renderer.createPalette = function ($container, options) {
            fn_createPalette.call(this, $container, options);
            var color_pallette = current_theme + '_colors';
            if (!openerp.qweb.has_template(color_pallette)) {
                return;
            }

            var $color = $container.find('.note-color');
            $container.find('.colorpicker').remove();
            var html = openerp.qweb.render(color_pallette);
            $color.find('.note-color-palette').append(html);
            var $bg = $color.find('.mail-colorpicker:first button');
            var $fore = $color.find('.mail-colorpicker:last button');

            $bg.each(function () { $(this).attr('data-event', 'backColor'); });
            $fore.each(function () { $(this).attr('data-event', 'foreColor'); });
        };

        // To apply inline background color and background of font image
        var range = $.summernote.core.range;
        var dom = $.summernote.core.dom;
        var range = $.summernote.core.range;
        $.summernote.pluginEvents.backColor = function (event, editor, layoutInfo, backColor) {
            var $editable = layoutInfo.editable();
            $editable.data('NoteHistory').recordUndo();
            var r = range.create();
            if($(r.sc).find('img').length != 0){
                var $target = $(getImgTarget());
                var src = $target.attr('src');
                if(src && src.indexOf("fa_to_img") != -1){
                    $target.css('background-color', backColor);
                }
                return;
            }
            if (r.isCollapsed() && r.isOnCell()) {
                var cell = dom.ancestor(r.sc, dom.isCell);
                if(! $(cell).hasClass("color_picker")){
                    var $div = $(cell).parents('.bg-color');
                    if($div.length != 0){
                        cell = $div[0];
                    }
                }
                cell.style.backgroundColor = backColor;
                return;
            }
            $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, null, backColor, null);
            editor.afterCommand($editable);
        };

        // To apply inline foreground color and color of font image
        $.summernote.pluginEvents.foreColor = function (event, editor, layoutInfo, foreColor) {
            var $editable = layoutInfo.editable();
            $editable.data('NoteHistory').recordUndo();
            var r = range.create();
            if($(r.sc).find('img').length != 0){
                var $target = $(getImgTarget());
                var src = $target.attr('src');
                if(src && src.indexOf("fa_to_img") != -1){
                    var match = src.match(/fa_to_img\/[^/]*\/([^/]*)\//); 
                    $target.attr('src', src.replace(match[1], encodeURIComponent(foreColor).replace(/ /g, '')));
                }
                return;
            }
            $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, foreColor, null, null);
            editor.afterCommand($editable);
        };

        // To apply inline float on image
        $.summernote.eventHandler.editor.floatMe = function ($editable, sValue) {
            var $target = $(getImgTarget());
            $editable.data('NoteHistory').recordUndo();
            switch (sValue) {
                case 'center': $target.toggleClass('center-block').removeClass('pull-right pull-left');
                    $target.css('float','');
                    break;
                case 'left': $target.toggleClass('pull-left').removeClass('pull-right center-block');
                    $target.css('float','left');
                    break;
                case 'right': $target.toggleClass('pull-right').removeClass('pull-left center-block');
                    $target.css('float','right');
                    break;
            }
        };

        // To apply inline thumnail, round, shadow, circle effect on image
        $.summernote.eventHandler.editor.imageShape = function ($editable, sValue) {
            var $target = $(getImgTarget());
            $editable.data('NoteHistory').recordUndo();
            $target.toggleClass(sValue);
            var width = $target.css('width');
            var bg_color = $target.css('background-color');
            $target.attr('style',"");
            $target.css({
                'width':width,
                'background-color':bg_color,
                'max-width':'600px',
                'height':'auto'});
            if($target.hasClass('img-rounded')){
                $target.css('border-radius','6px');
            }
            if($target.hasClass('img-thumbnail')){
                $target.css({
                    'display':'inline-block',
                    'padding':'4px',
                    'border':'3px solid #FFF',
                    'border-radius':'6px'
                });
            }
            if($target.hasClass('shadow')){
                $target.css({
                    '-moz-box-shadow':'0px 3px 8px rgba(0, 0, 0, 0.2)',
                    '-webkit-box-shadow':'0px 3px 8px rgba(0, 0, 0, 0.2)',
                    'box-shadow':'0px 3px 8px rgba(0, 0, 0, 0.2)'});
            }
            if($target.hasClass('img-circle')){
                $target.css({'border-radius':'50%'});
            }
        };

        // For Converting Selected Font Awesome Pictograms to PNG images
        website.editor.FontIconsDialog.include({
            save: function () {
                this.media.className = "";
                var fa_char = getFACharacter(this.$('#fa-icon').val());
                var color;
                if (/fa_to_img/.test(this.media.src)){
                    color = this.media.src.match(/fa_to_img\/[^/]*\/([^/]*)\//)[1];
                }
                else{
                    color = $(this.parent.media).css('color');
                }
                if (fa_char){
                    var url = _.str.sprintf('/fa_to_img/%s/%s/500', fa_char, color);
                    $(this.media).attr('src', url);
                }
            },
        });

        // For Converting Bootstrap Button CSS To Inline Button CSS
        website.editor.LinkDialog.include({
            class_to_inline: function (element, attrs) {
                _.each(attrs, function (attr) {
                    var val = element.css(attr);
                    element.css(attr, val);
                });
            },
            save: function () {
                var $anchor, self = this, selection = document.getSelection();
                this._super();
                if ($(selection.anchorNode).is("a")) {
                    $anchor = $(selection.anchorNode);
                }
                else {
                    $anchor = $(selection.anchorNode.parentElement);
                }
                $anchor.attr('style', '-webkit-user-select: none;-moz-user-select: none;-ms-user-select: none;user-select: none; cursor: pointer');
                self.class_to_inline($anchor, ['padding', 'font-size', 'line-height', 'border-radius', 'color', 'background-color', 'border-color', 'text-decoration', 'display', 'margin-bottom', 'font-weight', 'text-align', 'vertical-align', 'background-image', 'border', 'white-space', 'border-top-left-radius', 'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius']);
            }
        });
    });

    var load_qweb = function load_template(templates) {
        return openerp.jsonRpc('/website_mail/load_qweb_templates', 'call', {'templates': templates})
            .then(function (data) {
                _.each(data, function (template) {
                    openerp.qweb.add_template(template);
                });
            });
    }

    load_qweb(['website_mail.mass_mail_theme_list', 'website_mail.dialog_email_template_theme']);

    // Snippet option for resizing  image and column width inline like excel
    website.snippet.options["width-x"] = website.snippet.Option.extend({
        start: function () {
            this.container_width = 600;
            var parent = this.$target.closest('[data-max-width]');
            if( parent.length ){
                this.container_width = parseInt(parent.attr('data-max-width'));
            } 
            var self = this;
            var offset, sib_offset, target_width, sib_width;
            this.is_image = false;
            this._super();

            this.$overlay.find(".oe_handle.e, .oe_handle.w").removeClass("readonly");
            if( this.$target.is('img')){
                this.$overlay.find(".oe_handle.w").addClass("readonly");
                this.$overlay.find(".oe_snippet_remove, .oe_snippet_move, .oe_snippet_clone").addClass("hidden");
                this.is_image=true;
            }

            this.$overlay.find(".oe_handle").on('mousedown', function (event){
                event.preventDefault();
                var $handle = $(this);
                var compass = false;

                _.each(['n', 's', 'e', 'w' ], function(handler) {
                    if ($handle.hasClass(handler)) { compass = handler; }
                });
                if(self.is_image){ compass = "image"; }
                self.BuildingBlock.editor_busy = true;

                var $body = $(document.body);

                var body_mousemove = function (event){
                    event.preventDefault();
                    offset = self.$target.offset().left;
                    target_width = self.get_max_width(self.$target);
                    if (compass === 'e' && self.$target.next().offset()) {
                        sib_width = self.get_max_width(self.$target.next());
                        sib_offset = self.$target.next().offset().left;
                        self.change_width(event, self.$target, target_width, offset ,'plus');
                        self.change_width(event, self.$target.next(), sib_width, sib_offset ,'minus');
                    }
                    if (compass === 'w' && self.$target.prev().offset()) {
                        sib_width = self.get_max_width(self.$target.prev());
                        sib_offset = self.$target.prev().offset().left;
                        self.change_width(event, self.$target, target_width, offset ,'minus');
                        self.change_width(event, self.$target.prev(), sib_width, sib_offset, 'plus');
                    }
                    if (compass === 'image'){
                        self.change_width(event, self.$target, target_width, offset ,'plus');
                    }
                }
                var body_mouseup = function(){
                    $body.unbind('mousemove', body_mousemove);
                    $body.unbind('mouseup', body_mouseup);
                    self.BuildingBlock.editor_busy = false;
                    self.$target.removeClass("resize_editor_busy");
                };
                $body.mousemove(body_mousemove);
                $body.mouseup(body_mouseup);
            });
        },
        change_width:function(event, target ,target_width, offset, type){
            var self = this;
            if(type == 'plus'){
                var width = event.pageX-offset;
            }else{
                var width = offset + target_width - event.pageX;
            }
            target.css("width", width + "px");
            self.BuildingBlock.cover_target(self.$overlay, self.$target);
            return;
        },
        get_int_width: function ($el) {
            var el_width = $el.css('width');
            return parseInt(el_width);
        },
        get_max_width: function ($el) {
            var max_width = 0;
            var self = this;
            _.each($el.siblings(),function(sib){
                max_width +=  self.get_int_width($(sib));
            })
            return this.container_width - max_width;
        },
        on_clone: function ($clone) {
            var clone_index = $(this.$target).index();
            var $table = this.$target.parents('table[data-max-width]');
            if($table.length == 1){
                _.each($table.find('tbody>tr'),function(row){
                    var clone_selector = 'td:eq(' + clone_index + ')';
                    var $col_to_clone = $(row).find(clone_selector);
                    if($col_to_clone.length != 0){
                        $col_to_clone.after($col_to_clone.clone());
                    }
                });
            }
            this._super($clone);
            this.BuildingBlock.cover_target(this.$overlay, this.$target);
        },
        on_remove: function () {
            var remove_index = $(this.$target).index();
            var $table = this.$target.parents('table[data-max-width]');
            if($table.length == 1){
                _.each($table.find('tbody>tr'),function(row){
                    var remove_selector = 'td:eq(' + remove_index + ')';
                    $(row).find(remove_selector).remove();
                });
            }
            this._super();
            this.BuildingBlock.cover_target(this.$overlay, this.$target);
        },
    })

    website.snippet.options.media = website.snippet.options.media.extend({
        on_focus : function () {
            this._super();
            var src = this.$target.attr('src');
            if(src && src.indexOf("fa_to_img") != -1){
                $('.note-image-popover').find('.note-color').css('display', 'inline-block');
            }else{
                $('.note-image-popover').find('.note-color').css('display', 'none');
            }
        }
    });

    // Copy the template to the body of the email
    $(document).ready(function () {
       $('.js_template_set').off('click').click(function(ev) {
            $('#email_designer').show();
            $('#email_template').hide();
            $(".js_content", $(this).parent().parent()).children().clone().appendTo('#email_body');
            $(".js_content", $(this).parent().parent()).children().clone().appendTo('#email_body_html');
            $('#email_body, #email_body_html' ).addClass('o_dirty');
            var snippet_xml_id = $(this).attr('data-snippet-xmlid');
            if (snippet_xml_id){
                window.location.hash = "theme_id=" + snippet_xml_id;
            }
            openerp.website.editor_bar.edit();
            ev.preventDefault();
        });
    });

    //Email Theme Selector Dialog
    openerp.website.EmailTemplateTheme = openerp.Widget.extend({
        template: 'website_mail.dialog_email_template_theme',
        events: {
            'click .close': 'close',
            'click .theme_thumbnail div .btn': 'select_template',
        },
        start: function () {
            var self = this;
            setTimeout(function () {self.$el.addClass('in');}, 0);
        },
        select_template: function(e) {
            var url_data = website.parseQS(window.location.search.substring(1));
            url_data['theme_id'] = $(e.target).attr('data-snippet-xmlid');
            openerp.jsonRpc('/website_mail/set_template_theme', 'call', url_data)
                .then(function (res) {
                    window.location.href = _.str.sprintf("%s?model=%s&res_id=%s&action=%s&theme_id=%s&enable_editor=1", window.location.pathname, url_data.model, url_data.res_id, url_data.action, url_data.theme_id);
                 })
        },
        close: function () {
            var self = this;
            this.$el.removeClass('in');
            this.$el.addClass('out');
            setTimeout(function () {self.destroy();}, 500);
        }
    });

    openerp.website.ready().done(function() {
        function theme_customize() {
            var dialog = new openerp.website.EmailTemplateTheme();
            dialog.appendTo($(document.body));
        }
        $('.info_popover').popover({
            placement: "bottom",
            animation: true,
            html: true,
        });
        $('.theme_thumbnail div .btn').click(function(e){new openerp.website.EmailTemplateTheme().select_template(e)});
        $(document).on('click', "a.email_template_theme_select", theme_customize);
    });

})();
