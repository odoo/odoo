(function () {
    'use strict';

    var website = openerp.website;
    var session = new openerp.Session();

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
    });


    var fn_popover_update = $.summernote.eventHandler.popover.update;
    $.summernote.eventHandler.popover.update = function ($popover, oStyle, isAirMode) {
        fn_popover_update.call(this, $popover, oStyle, isAirMode);
        $("span.o_table_handler, div.note-table").remove();
    };
    
    website.EditorBar.include({
        start: function () {
            var self = this;
            if (location.search.indexOf("enable_editor") !== -1) {
                this.on('rte:ready', this, function () {
                    $("#choose_template").off("click").on("click", _.bind(self.on_choose_template, self));
                    $(".theme_thumbnail [data-snippet-theme]").off("click").on("click", _.bind(self.on_set_snippet_theme, self));
                    $("#wrapwrap").on('click', function (event) {
                        if ($(event.target).is("#wrapwrap")) {
                            setTimeout(function () {
                                var node = $("#wrapwrap .o_editable:first *")
                                    .filter(function () { return this.textContent.match(/\S|\u00A0/); })
                                    .add($("#wrapwrap .o_editable:first"))
                                    .last()[0];
                                $.summernote.core.range.create(node, $.summernote.core.dom.nodeLength(node)).select();
                            },0);
                        }
                    });
                });
                this.on("snippets:ready", this, _.bind(self.display_theme_from_html, self));
            }
            return this._super.apply(this, arguments);
        },
        display_theme_from_html: function () {
            var theme = $("#wrapwrap .o_editable:first [data-snippet-theme]").data("snippet-theme");
            if (theme) {
                $("#choose_template").show();
                this.set_snippet_theme(theme);
            } else {
                $("#choose_template").hide();
                this.on_choose_template();
            }
            var mailing_model = JSON.parse($.deparam(location.search).datarecord).mailing_model;
            if (mailing_model) {
                this.get_snippet_template( mailing_model );
            }
        },

        on_choose_template: function (event) {
            if (event) {
                $("#choose_template").show();
            }
            var $editable = $("#wrapwrap .o_editable:first");
            $(".o_table_handler").remove();
            $editable.parent().add("#oe_snippets, #templates, .note-popover").toggleClass("hidden");
            $("#choose_template").children().toggleClass("hidden");
            $("body").trigger("resize");
            $(window.top).trigger('resize');
        },
        on_set_snippet_template: function (event) {
            var $editable = $("#wrapwrap .o_editable:first");
            this.rte.historyRecordUndo($editable);
            $editable.html( $(event.target).closest(".theme_thumbnail").find(".js_content").html() );
            $editable.parent().add("#oe_snippets, #templates, .note-popover").toggleClass("hidden");
            $("#choose_template").children().toggleClass("hidden");
            setTimeout(function () {
                $("body").trigger("resize");
                $("body")[0].scrollTop = 0;
            },0);
            event.preventDefault();
        },
        on_set_snippet_theme: function (event) {
            this.set_snippet_theme($(event.target).data("snippet-theme"));
            this.on_choose_template(event);
            event.preventDefault();
        },
        set_snippet_theme: function (theme) {
            $("#o_left_bar .o_panel_body > div").addClass("hidden");
            $("#o_left_bar .o_panel_body > div."+theme).removeClass("hidden");
        },
        get_snippet_template: function (mailing_model) {
            var self = this;
            var domain = [['model', '=', mailing_model]];
            session.model('mail.template').call('search_read', [domain]).then(function (datas) {
                var $template = $("#templates > div:last").addClass("hidden");
                var $tclone = $template.find("> div > div:first");
                $tclone.siblings().remove();
                _.each(datas, function (data) {
                    if (!data.body_html) {
                        return;
                    }
                    $template.removeClass("hidden");
                    var $clone = $tclone.clone().removeClass("hidden");
                    $clone.find("p:first").html(data.name);
                    $clone.find(".template_preview").html(data.body_html);
                    $tclone.after($clone);
                });

                $(".js_template_set").off("click").on("click", _.bind(self.on_set_snippet_template, self));
            });
        }
    });

    var cache = {};
    var rulesCache = [];
    website.getMatchedCSSRules = function getMatchedCSSRules(a) {
        if(cache[a.tagName + "." +a.className]) {
            return cache[a.tagName + "." +a.className];
        }
        if (!rulesCache.length) {
            var sheets = document.styleSheets;
            for(var i = 0; i < sheets.length; i++) {
                var rules = sheets[i].rules || sheets[i].cssRules;
                if (rules) {
                    for(var r = 0; r < rules.length; r++) {
                        var selectorText = rules[r].selectorText;
                        if (selectorText &&
                                rules[r].cssText &&
                                selectorText.indexOf(".") !== -1 &&
                                selectorText.indexOf(":hover") === -1 &&
                                selectorText.indexOf(":before") === -1 &&
                                selectorText.indexOf(":after") === -1 &&
                                selectorText.indexOf(":active") === -1 &&
                                selectorText.indexOf(":link") === -1 &&
                                selectorText.indexOf("::") === -1 &&
                                selectorText.indexOf("\"") === -1 &&
                                selectorText.indexOf("'") === -1) {
                            var st = selectorText.split(/\s*,\s*/);
                            for (var k=0; k<st.length; k++) {
                                rulesCache.push({
                                    'selector': st[k],
                                    'style': rules[r].style,
                                    'point': st[k].split(/\s+/).length
                                });
                            }
                        }
                    }
                }
            }

            rulesCache.sort(function (a,b) {
                return a.point-b.point;
            });
        }

        var css = [];
        a.matches = a.matches || a.webkitMatchesSelector || a.mozMatchesSelector || a.msMatchesSelector || a.oMatchesSelector;
        for(var r = 0; r < rulesCache.length; r++) {
            if (a.matches(rulesCache[r].selector)) {
                var style = rulesCache[r].style;
                if (style.parentRule) {
                    var style_obj = {};
                    for (var k=0, len=style.length; k<len; k++) {
                        style_obj[style[k]] = style[style[k]];
                    }
                    rulesCache[r].style = style = style_obj;
                }
                css.push(style);
            }
        }

        var style = {};
        _.each(css, function (v,k) {
            _.each(v, function (v,k) {
                if (!style[k] || style[k].indexOf('important') === -1 || v.indexOf('important') !== -1) {
                    style[k] = v;
                }
            });
        });
        
        return cache[a.tagName + "." +a.className] = style;
    };

    $.fn.bindFirst = function(name, fn) {
        this.bind(name, fn);
        var handlers = $._data($(this).get(0), 'events')[name.split('.')[0]];
        var handler = handlers.pop();
        handlers.splice(0, 0, handler);
    };

    website.snippet.BuildingBlock.include({
        start: function () {
            var self = this;
            this._super();
            setTimeout(function () {
                self.img_to_font();
                self.style_to_class();
            });
        },

        _get_snippet_url: function () {
            return snippets_url;
        },
        clean_for_save: function () {
            this._super();
            this.class_to_style();
            this.font_to_img();
            var $editable = $("#wrapwrap .o_editable:first");
            var theme = ($("#o_left_bar .o_panel_body > div:not(.hidden)").attr("class") || "").replace(/^\s*|\s*o_mail_block[^\s]+\s*|\s*oe_snippet\s*|\s*ui-draggable\s*|\s*$/g, '');
            var $theme = $("#wrapwrap .o_editable:first [data-snippet-theme]").removeAttr("data-snippet-theme").removeData("snippet-theme");
            $editable.children().first().attr("data-snippet-theme", theme);
            $editable.find(":hidden").remove();
        },
        // convert font awsome into image
        font_to_img: function () {
            $("#wrapwrap .fa").each(function () {
                var $font = $(this);
                var content;
                _.find(website.editor.fontIcons, function (font) {
                    return _.find(website.editor.getCssSelectors(font.parser), function (css) {
                        if ($font.is(css[2])) {
                            content = css[1].match(/content:\s*['"](.)['"]/)[1];
                            return true;
                        }
                    });
                });
                if (content) {
                    var size = parseInt(parseFloat($font.css("font-size"))/parseFloat($font.parent().css("font-size")),10);
                    var src = _.str.sprintf('/website_mail/font_to_img/%s/%s/'+$font.width(), window.encodeURI(content), window.encodeURI($font.css("color")));
                    var $img = $("<img/>").attr("src", src)
                        .attr("data-class", $font.attr("class"))
                        .attr("style", $font.attr("style"))
                        .css({"height": size+"em"}).css("font-size", "");
                    $font.replaceWith($img);
                } else {
                    $font.remove();
                }
            });
        },
        // convert image into font awsome
        img_to_font: function () {
            $("#wrapwrap img[src*='/website_mail/font_to_img/']").each(function () {
                var $img = $(this);
                var $font = $("<span/>").attr("class", $img.data("class")).attr("style", $img.attr("style")).css("height", "");
                $img.replaceWith($font);
            });
        },

        class_to_style: function () {
            var $editable = $("#wrapwrap .o_editable:first");
            var selector = _.map(rulesCache, function (a) { return a.selector;}).join(",");
            $editable.find(selector).each(function () {
                var $target = $(this);
                var css = website.getMatchedCSSRules(this);
                var style = $target.attr("style") || "";
                _.each(css, function (v,k) {
                    if (style.indexOf(k) === -1) {
                        style = k+":"+v+";"+style;
                    }
                });
                $target.attr("style", style);
            });
        },

        style_to_class: function () {
            var cache = {};
            var $editable = $("#wrapwrap .o_editable:first");
            website.getMatchedCSSRules($editable[0]);
            var selector = _.map(rulesCache, function (a) { return a.selector;}).join(",");
            var $c = $('<span/>').appendTo("body");
            $editable.find(selector).each(function () {
                var $target = $(this);
                var css = website.getMatchedCSSRules(this);
                var style = "";
                _.each(css, function (v,k) {
                    if (style.indexOf(k) === -1) {
                        style = k+":"+v+";"+style;
                    }
                });
                css = $c.attr("style", style).attr("style").split(/\s*;\s*/);
                style = $target.attr("style") || "";
                _.each(css, function (v) {
                    style = style.replace(v, '');
                });
                $target.attr("style", style.replace(/;+(\s;)*/g, ';').replace(/^;/g, ''));
            });
            $c.remove();
        }
    });

    window.top.openerp[callback+"_set_value"] = function (value, fields_values, field_name) {
        var $editable = $("#wrapwrap .o_editable:first");
        var editor_enable = $('body').hasClass('editor_enable');
        var _val = $editable.prop("innerHTML");
        value = value || "";

        if(value !== _val) {
            if (editor_enable) {
                if (value !== fields_values[field_name]) {
                    openerp.website.editor_bar.rte.historyRecordUndo($editable, true);
                }
                openerp.website.editor_bar.snippets.make_active(false);
            }
            
            if (value.indexOf('on_change_model_and_list') === -1) {

                $editable.html(value);

                if (editor_enable) {
                    openerp.website.editor_bar.snippets.img_to_font();
                    openerp.website.editor_bar.snippets.style_to_class();
                    if (fields_values.mailing_model) {
                        openerp.website.editor_bar.display_theme_from_html();
                    }

                    if (value !== fields_values[field_name]) {
                        $editable.trigger("content_changed");
                    }
                }
            }
        }

        if (fields_values.mailing_model) {
            openerp.website.editor_bar.get_snippet_template(fields_values.mailing_model);
            if (value.indexOf('on_change_model_and_list') !== -1) {
                window.top.openerp[callback+"_downup"](_val);
            }
        }
    };

})();