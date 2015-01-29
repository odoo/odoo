(function () {
    'use strict';

    var dummy = function () {};

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.snippets.xml');

    website.EditorBar.include({
        start: function () {
            var self = this;
            $(document).on('click', '.o_editable', function (event) {
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
            website.snippet.stop_animation();
            this.on('rte:ready', this, function () {
                var $editable = $(".o_editable");
                window.snippets = this.snippets = new website.snippet.BuildingBlock(this, $editable);
                this.snippets.insertAfter(this.$el);
                website.snippet.start_animation(true);
                $editable.find("*").off('mousedown mouseup click');
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
        o_editable: function(node,i,m){
            while (node) {
                if (node.className) {
                    if (node.className.indexOf('o_not_editable')!==-1 ) {
                        return false;
                    }
                    if (node.className.indexOf('o_editable')!==-1 ) {
                        return true;
                    }
                }
                node = node.parentNode;
            }
            return false;
        },
        hasData: function(node,i,m){
            return !!_.toArray(node.dataset).length;
        },
        data: function(node,i,m){
            return $(node).data(m[3]);
        }
    });

    if (!website.snippet) website.snippet = {};
    website.snippet.templateOptions = [];
    website.snippet.globalSelector = {
        closest: function () { return $(); },
        all: function () { return $(); },
        is: function () { return false; },
    };
    website.snippet.selector = [];
    website.snippet.BuildingBlock = openerp.Widget.extend({
        template: 'website.snippets',
        activeSnippets: [],
        init: function (parent, $editable) {
            this.parent = parent;
            this.$editable = $editable;

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
            this.$snippet = $("#oe_snippets");

            this.$el
                .on("mouseenter", function () { self.show(); })
                .on("mouseleave", function (event) { if (event.clientX>0 && event.clientY>0) self.hide(); });

            $(window).resize(function () {
                setTimeout('$(document).click()',0);
            });

            this.fetch_snippet_templates();
            this.bind_snippet_click_editor();

            $(document).on('click', '.dropdown-submenu a[tabindex]', function (e) {
                e.preventDefault();
            });

            var _isNotBreakable = $.summernote.core.dom.isNotBreakable;
            $.summernote.core.dom.isNotBreakable = function (node, sc, so, ec, eo) {
                return _isNotBreakable(node, sc, so, ec, eo) || $(node).is('div') || website.snippet.globalSelector.is($(node));
            };

            $(window).on('resize', function () {
                if (self.$active_snipped_id) {
                    self.cover_target(self.$active_snipped_id.data("snippet-editor").$overlay, self.$active_snipped_id);
                }
                var $scroll = self.$snippet.find('.scroll:first').css("overflow", "");
                if ($scroll.children().last().height() + $scroll.children().first().height() + 34 > document.body.clientHeight) {
                    $scroll.css("overflow", "auto").css("width", "216px");
                } else {
                    $scroll.css("width", "");
                }
            });

            $(document).on('mousemove', function () {
                if (self.$active_snipped_id && self.$active_snipped_id.data("snippet-editor")) {
                    self.$active_snipped_id.data("snippet-editor").$overlay.removeClass('o_keypress');
                }
            });
            $(document).on('keydown', function (event) {
                if (self.$active_snipped_id && self.$active_snipped_id.data("snippet-editor")) {
                    self.$active_snipped_id.data("snippet-editor").$overlay.addClass('o_keypress');
                }
                if ((event.metaKey || (event.ctrlKey && !event.altKey)) && event.shiftKey && event.keyCode >= 48 && event.keyCode <= 57) {
                    self.$snippet.find('.scroll:first > ul li:eq('+(event.keyCode-49)+') a').trigger("click");
                    self.show();
                    event.preventDefault();
                }
            });
        },

        _get_snippet_url: function () {
            return '/website/snippets';
        },
        _add_check_selector : function (selector, no_check) {
            var self = this;
            var selector = selector.split(/\s*,/).join(":not(.o_snippet_not_selectable), ") + ":not(.o_snippet_not_selectable)";

            if (no_check) {
                return {
                    closest: function ($from, parentNode) {
                        return $from.closest(selector, parentNode);
                    },
                    all: function ($from) {
                        return $from ? $from.find(selector) : $(selector);
                    },
                    is: function ($from) {
                        return $from.is(selector);
                    }
                };
            } else {
                var selector = selector.split(/\s*,/).join(":o_editable, ") + ":o_editable";
                return {
                    closest: function ($from, parentNode) {
                        var parents = self.$editable.get();
                        return $from.closest(selector, parentNode).filter(function () {
                            var node = this;
                            while (node.parentNode) {
                                if (parents.indexOf(node)!==-1) {
                                    return true;
                                }
                                node = node.parentNode;
                            }
                            return false;
                        });
                    },
                    all: function ($from) {
                        return $from ? $from.find(selector) : self.$editable.filter(selector).add(self.$editable.find(selector));
                    },
                    is: function ($from) {
                        return $from.is(selector);
                    }
                };
            }
        },
        fetch_snippet_templates: function () {
            var self = this;
            return openerp.jsonRpc(this._get_snippet_url(), 'call', {})
                .then(function (html) {
                    var $html = $(html);

                    $html.siblings(".scroll").find('> ul li').tooltip({
                            delay: { "show": 500, "hide": 100 },
                            container: 'body',
                            title: function () {
                                return (navigator.appVersion.indexOf('Mac') > -1 ? 'CMD' : 'CTRL')+'+SHIFT+'+($(this).index()+1);
                            },
                            trigger: 'hover',
                            placement: 'right'
                        }).on('click', function () {$(this).tooltip('hide');});

                    // t-snippet
                    $html.find('> .tab-content > div > [data-oe-type="snippet"]').each(function () {
                        var $div = $('<div/>').insertAfter(this).append(this).attr('name', $(this).data('oe-name'));
                    });
                    // end

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
                    website.snippet.globalSelector = {
                        closest: function ($from) {
                            var $temp;
                            var $target;
                            var len = selector.length;
                            for (var i = 0; i<len; i++) {
                                $temp = selector[i].closest($from, $target && $target[0]);
                                if (!$target || $temp.length) {
                                    $target = $temp;
                                }
                            }
                            return $target;
                        },
                        all: function ($from) {
                            var $target;
                            var len = selector.length;
                            for (var i = 0; i<len; i++) {
                                if (!$target) $target = selector[i].all($from);
                                else $target = $target.add(selector[i].all($from));
                            }
                            return $target;
                        },
                        is: function ($from) {
                            var len = selector.length;
                            for (var i = 0; i<len; i++) {
                                if (selector[i].is($from)) {
                                    return true;
                                }
                            }
                            return false;
                        },
                    };

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

                                // from t-snippet
                                var thumbnail = $("[data-oe-thumbnail]", this).data("oe-thumbnail");
                                if (thumbnail) {
                                    $div.find('.oe_snippet_thumbnail_img').css('background-image', 'url(' + thumbnail + ')');
                                }
                                // end
                            }
                            $("> *:not(.oe_snippet_thumbnail)", this).addClass('oe_snippet_body');
                        });

                    // select all default text to edit (if snippet default text)
                    self.$snippets.find('.oe_snippet_body, .oe_snippet_body *')
                        .contents()
                        .filter(function() {
                            return this.nodeType === 3 && this.textContent.match(/\S/);
                        }).parent().addClass("o_default_snippet_text");
                    $(document).on("mouseup", ".o_default_snippet_text", function (event) {
                        $(event.target).selectContent();
                    });
                    $(document).on("keyup", function (event) {
                        var r = $.summernote.core.range.create();
                        $(r && r.sc).closest(".o_default_snippet_text").removeClass("o_default_snippet_text");
                    });
                    // end

                    // clean t-oe
                    $html.find('[data-oe-model]').each(function () {
                        for (var k=0; k<this.attributes.length; k++) {
                            if (this.attributes[k].name.indexOf('data-oe-') === 0) {
                                $(this).removeAttr(this.attributes[k].name);
                                k--;
                            }
                        }
                    });
                    // end

                    self.$el.append($html);

                    $(window).trigger('resize');

                    self.make_snippet_draggable(self.$snippets);
                });
        },
        cover_target: function ($el, $target){
            if($el.data('not-cover_target')) return;
            var pos = $target.offset();
            var mt = parseInt($target.css("margin-top") || 0);
            var mb = parseInt($target.css("margin-bottom") || 0);
            var width = $target.outerWidth();
            var bigger = pos.left+width > $("body").outerWidth()-8;
            $el.css({
                'width': width,
                'top': pos.top - mt - 5,
                'left': pos.left-1
            });
            $el.find(".oe_handle.e,.oe_handle.w").css({'height': $target.outerHeight() + mt + mb+1});
            if (bigger) {
                $el.find(".oe_handle.e").css({right: 0, margin: 0})
                    .find("div").css({right: 0, left: 'auto'});
            } else {
                $el.find(".oe_handle.e").css({right: "", margin: ""})
                    .find("div").css({right: "", left: ""});
            }
            $el.find(".oe_handle.s").css({'top': $target.outerHeight() + mt + mb});
            $el.find(".oe_handle.size").css({'top': $target.outerHeight() + mt});
            $el.find(".oe_handle.s,.oe_handle.n").css({'width': width-2});
        },

        show_blocks: function () {
            var cache = {};
            this.$snippet.find(".tab-pane").each(function () {
                var catcheck = false;
                var $category = $(this);
                $category.find(".oe_snippet_body").each(function () {
                    var $snippet = $(this);

                    var check = false;

                    for (var k in website.snippet.templateOptions) {
                        var option = website.snippet.templateOptions[k];
                        if ($snippet.is(option.base_selector)) {

                            cache[k] = cache[k] || {
                                'drop-near': option['drop-near'] ? option['drop-near'].all() : [],
                                'drop-in': option['drop-in'] ? option['drop-in'].all() : []
                            };

                            if (cache[k]['drop-near'].length || cache[k]['drop-in'].length) {
                                catcheck = true;
                                check = true;
                                break;
                            }
                        }
                    }

                    if (check) {
                        $snippet.closest(".oe_snippet").removeClass("disable");
                    } else {
                        $snippet.closest(".oe_snippet").addClass("disable");
                    }
                });

                $('#oe_snippets .scroll a[data-toggle="tab"][href="#' + $category.attr("id") + '"]').toggle(catcheck);
            });
        },
        show: function () {
            var self = this;
            this.make_active(false);
            this.$el.addClass("o_open");
            this.show_blocks();
        },
        hide: function () {
            this.$el.removeClass("o_open");
        },
        bind_snippet_click_editor: function () {
            var self = this;
            var snipped_event_flag;
            $(document).on('click', '*', function (event) {
                var srcElement = event.srcElement || (event.originalEvent && (event.originalEvent.originalTarget || event.originalEvent.target) || event.target);
                if (self.editor_busy || snipped_event_flag===srcElement || !srcElement) {
                    return;
                }
                snipped_event_flag = srcElement;

                setTimeout(function () {snipped_event_flag = false;}, 0);
                var $target = $(srcElement);

                if ($target.closest(".oe_overlay, .note-popover").length) {
                    return;
                }

                if (!website.snippet.globalSelector.is($target)) {
                    $target = website.snippet.globalSelector.closest($target);
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
                    template[k].selector.all().each(function () {
                        new Option(self, null, $(this), k).clean_for_save();
                    });
                }
            }
            this.$editable.find("*[contentEditable], *[attributeEditable]")
                .removeAttr('contentEditable')
                .removeProp('contentEditable')
                .removeAttr('attributeEditable')
                .removeProp('attributeEditable');
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
                    var $selector_siblings = $();
                    var $selector_children = $();
                    var vertical = false;
                    var temp = website.snippet.templateOptions;
                    for (var k in temp) {
                        if ($base_body.is(temp[k].base_selector)) {
                            if (temp[k]['drop-near']) {
                                if (!$selector_siblings) $selector_siblings = temp[k]['drop-near'].all();
                                else $selector_siblings = $selector_siblings.add(temp[k]['drop-near'].all());
                            }
                            if (temp[k]['drop-in']) {
                                if (!$selector_children) $selector_children = temp[k]['drop-in'].all();
                                else $selector_children = $selector_children.add(temp[k]['drop-in'].all());
                            }
                        }
                    }

                    $toInsert = $base_body.clone();

                    if (!$selector_siblings.length && !$selector_children.length) {
                        console.debug($snippet.find(".oe_snippet_thumbnail_title").text() + " have not insert action: data-drop-near or data-drop-in");
                        return;
                    }

                    self.activate_insertion_zones($selector_siblings, $selector_children);

                    $('.oe_drop_zone').droppable({
                        over:   function(){
                            dropped = true;
                            $(this).first().after($toInsert);
                        },
                        out:    function(){
                            var prev = $toInsert.prev();
                            if(this === prev[0]){
                                dropped = false;
                                $toInsert.detach();
                            }
                        }
                    });
                },
                stop: function(ev, ui){
                    $toInsert.removeClass('oe_snippet_body');
                    
                    if (! dropped && self.$editable.find('.oe_drop_zone') && ui.position.top > 3) {
                        var el = self.$editable.find('.oe_drop_zone').nearest({x: ui.position.left, y: ui.position.top}).first();
                        if (el.length) {
                            el.after($toInsert);
                            dropped = true;
                        }
                    }

                    self.$editable.find('.oe_drop_zone').droppable('destroy').remove();
                    
                    if (dropped) {

                        var prev = $toInsert.first()[0].previousSibling;
                        var next = $toInsert.last()[0].nextSibling;
                        var rte = self.parent.rte;

                        if (prev) {
                            $toInsert.detach();
                            rte.historyRecordUndo($(prev));
                            $toInsert.insertAfter(prev);
                        } else if (next) {
                            $toInsert.detach();
                            rte.historyRecordUndo($(next));
                            $toInsert.insertBefore(next);
                        } else {
                            var $parent = $toInsert.parent();
                            $toInsert.detach();
                            rte.historyRecordUndo($parent);
                            $parent.prepend($toInsert);
                        }

                        var $target = false;
                        $target = $toInsert;

                        setTimeout(function () {
                            self.$snippet.trigger('snippet-dropped', $target);

                            website.snippet.start_animation(true, $target);

                            // drop_and_build_snippet
                            self.create_overlay($target);
                            if ($target.data("snippet-editor")) {
                                $target.data("snippet-editor").drop_and_build_snippet();
                            }
                            for (var k in website.snippet.templateOptions) {
                                website.snippet.templateOptions[k].selector.all($target).each(function () {
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
        activate_insertion_zones: function($selector_siblings, $selector_children){
            var self = this;
            var zone_template = $("<div class='oe_drop_zone oe_insert'></div>");

            if ($selector_children) {
                $selector_children.each(function (){
                    var $zone = $(this);
                    var css = window.getComputedStyle(this);
                    var float = css.float || css.cssFloat;
                    var $drop = zone_template.clone();

                    $zone.append($drop);
                    var node = $drop[0].previousSibling;
                    var test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === "BR"));
                    if (test) {
                        $drop.addClass("oe_vertical oe_vertical_text").css({
                                'height': parseInt(window.getComputedStyle($zone[0]).lineHeight),
                                'float': 'none',
                                'display': 'inline-block'
                            });
                    } else if (float === "left" || float === "right") {
                        $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().last().outerHeight()), 30));
                    }

                    $drop = $drop.clone();

                    $zone.prepend($drop);
                    var node = $drop[0].nextSibling;
                    var test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === "BR"));
                    if (test) {
                        $drop.addClass("oe_vertical oe_vertical_text").css({
                                'height': parseInt(window.getComputedStyle($zone[0]).lineHeight),
                                'float': 'none',
                                'display': 'inline-block'
                            });
                    } else if (float === "left" || float === "right") {
                        $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().first().outerHeight()), 30));
                    }
                    if (test) {
                        $drop.css({'float': 'none', 'display': 'inline-block'});
                    }
                });

                // add children near drop zone
                $selector_siblings = $(_.uniq(($selector_siblings || $()).add($selector_children.children()).get()));
            }

            if ($selector_siblings) {
                $selector_siblings.filter(':not(.oe_drop_zone):not(.oe_drop_clone)').each(function (){
                    var $zone = $(this);
                    var $drop;
                    var css = window.getComputedStyle(this);
                    var float = css.float || css.cssFloat;

                    if($zone.prev('.oe_drop_zone:visible').length === 0){
                        $drop = zone_template.clone();
                        if (float === "left" || float === "right") {
                            $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.prev().outerHeight() || Infinity), 30));
                        }
                        $zone.before($drop);
                    }
                    if($zone.next('.oe_drop_zone:visible').length === 0){
                        $drop = zone_template.clone();
                        if (float === "left" || float === "right") {
                            $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.next().outerHeight() || Infinity), 30));
                        }
                        $zone.after($drop);
                    }
                });
            }

            var count;
            do {
                count = 0;
                $zones = self.$editable.find('.oe_drop_zone > .oe_drop_zone').remove();   // no recursive zones
                count += $zones.length;
                $zones.remove();
            } while (count > 0);

            // Cleaning consecutive zone and up zones placed between floating or inline elements. We do not like these kind of zones.
            var $zones = self.$editable.find('.oe_drop_zone:not(.oe_vertical)');
            $zones.each(function (){
                var zone = $(this);
                var prev = zone.prev();
                var next = zone.next();
                // remove consecutive zone
                if (prev.is('.oe_drop_zone') || next.is('.oe_drop_zone')) {
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
        activate_overlay_zones: function($targets){
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

                    var timer;
                    $target.closest('.o_editable').on("content_changed", function (event) {
                        if ($target[0] === $(event.target).data('last-mutation').target ||
                            $.contains($target[0], $(event.target).data('last-mutation').target)) {

                            $target.data('need_recover', true);
                            clearTimeout(timer);
                            timer = setTimeout(function () {
                                $(':data(need_recover)').each(function () {
                                    var $snippet = $(this);
                                    $snippet.data('need_recover', null);
                                    if ($snippet.data('overlay')) {
                                        self.cover_target($snippet.data('overlay'), $snippet);
                                    }
                                });
                            },50);
                        }
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
        },

        // helper for this.$target.find
        $: function (selector) {
            return this.$target(selector);
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
            this.set_active();
            this.$target.on('snippet-option-reset', _.bind(this.set_active, this));
            this._bind_li_menu();
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

        reset: function () {
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

        // call data-method args as method (data-only can be used)
        select: function (type, $li) {
            var self = this,
                $methods = [],
                el = $li[0],
                $el;

            if ($li.data('only') && type !== $li.data('only')) {
                return;
            }

            if (type==="click") {
                this.reset();
                this.BuildingBlock.parent.rte.historyRecordUndo(this.$target);
            }

            function filter (k) { return k !== 'oeId' && k !== 'oeModel' && k !== 'oeField' && k !== 'oeXpath' && k !== 'oeSourceId' && k !== 'only';}
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
        start: function ($change_target) {
            this.$bg = $change_target || this.$target;
            this._super();
            var src = this.$bg.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            if (this.$bg.hasClass('oe_custom_bg')) {
                this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
            }
        },
        background: function(type, value, $li) {
            if (value && value.length) {
                this.$bg.css("background-image", 'url(' + value + ')');
                this.$bg.addClass("oe_img_bg");
            } else {
                this.$bg.css("background-image", "");
                this.$bg.removeClass("oe_img_bg").removeClass("oe_custom_bg");
            }
        },
        choose_image: function(type, value, $li) {
            if(type !== "click") return;

            var self = this;
            var $image = $('<img class="hidden"/>');
            $image.attr("src", value);
            $image.appendTo(self.$bg);

            var editor = new website.editor.MediaDialog(null, $image[0]);
            editor.appendTo(document.body);
            editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');

            editor.on('saved', self, function (o) {
                var value = $image.attr("src");
                $image.remove();
                self.$el.find('li[data-choose_image]').data("background", value).attr("data-background", value);
                self.background(type, value,$li);
                self.$bg.addClass('oe_custom_bg');
                self.$bg.trigger("snippet-option-change", [self]);
                self.set_active();
            });
            editor.on('cancel', self, function () {
                $image.remove();
            });
        },
        set_active: function () {
            var self = this;
            var src = this.$bg.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
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

            if (!this.$el.find('.colorpicker').length) {
                this.$el.find('li').append( openerp.qweb.render('website.colorpicker') );
            }

            var classes = [];
            this.$el.find(".colorpicker button").map(function () {
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
            var $td = this.$el.find(".colorpicker td");
            var $colors = this.$el.find(".colorpicker button");
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
        },
        clean_for_save: function () {
            this._super();
            this.$target.find(".item").removeClass("next prev left right active")
                .first().addClass("active");
            this.$target.find('.carousel-indicators').find('li').removeClass('active')
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
                    self.editor.styles.background.$bg = self.$target.find(".item.active");
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
                    setTimeout(function () {
                        self.BuildingBlock.editor_busy = false;
                    },0);
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
            this.$target.on('attributes_change', function () {
                self.resetTransfo();
            });

            // don't unactive transform if rotation and mouseup on an other container
            var cursor_mousedown = false;
            $(document).on('mousedown', function (event) {
                if (self.$overlay.hasClass('oe_active') && $(event.target).closest(".transfo-controls").length) {
                    cursor_mousedown = event;
                }
            });
            $(document).on('mouseup', function (event) {
                if (cursor_mousedown) {
                    event.preventDefault();

                    var dx = event.clientX-cursor_mousedown.clientX;
                    var dy = event.clientY-cursor_mousedown.clientY;
                    setTimeout(function () {
                        self.$target.focusIn().activateBlock();
                        if (10 < Math.pow(dx, 2)+Math.pow(dy, 2)) {
                            setTimeout(function () {
                                self.$target.transfo({ 'hide': false });
                            },0);
                        }
                    },0);
                    cursor_mousedown = false;
                }
            });
        },
        style: function (type, value) {
            if (type !== 'click') return;
            var settings = this.$target.data("transfo").settings;
            this.$target.transfo({ 'hide': (settings.hide = !settings.hide) });
        },
        clear_style: function (type, value) {
            if (type !== 'click') return;
            this.$target.removeClass("fa-spin").attr("style", "");
            this.resetTransfo();
        },
        move_summernote_select: function () {
            var self = this;
            var transfo = this.$target.data("transfo");
            $('body > .note-handle')
                .attr('style', transfo.$markup.attr('style'))
                .css({
                    'z-index': 0,
                    'pointer-events': 'none'
                })
                .off('mousedown mouseup')
                .on('mousedown mouseup', function (event) {
                    self.$target.trigger( jQuery.Event( event.type, event ) );
                })
                .find('.note-control-selection').attr('style', transfo.$markup.find('.transfo-controls').attr('style'))
                    .css({
                        'display': 'block',
                        'cursor': 'auto'
                    });
        },
        resetTransfo: function () {
            var self = this;
            this.$overlay.css('width', '');
            this.$overlay.data('not-cover_target', true);
            this.$target.transfo("destroy");
            this.$target.transfo({
                hide: true,
                callback: function () {
                    var pos = $(this).data("transfo").$center.offset();
                    self.$overlay.css({
                        'top': pos.top | 0,
                        'left': pos.left | 0,
                        'position': 'absolute',
                    });
                    self.$overlay.find(".oe_overlay_options").attr("style", "width:0; left:0!important; top:0;");
                    self.$overlay.find(".oe_overlay_options > .btn-group").attr("style", "width:160px; left:-80px;");

                    self.move_summernote_select();
                }});
            this.$target.data('transfo').$markup
                .on("mouseover", function () {
                    self.$target.trigger("mouseover");
                })
                .mouseover();
        },
        on_focus : function () {
            var self = this;
            setTimeout(function () {
                self.$target.css({"-webkit-animation": "none", "animation": "none"});
                self.resetTransfo();
            },0);
        },
        on_blur : function () {
            this.$target.transfo("hide");
            $('.note-handle').hide(); // hide selection of summernote
            this.$target.css({"-webkit-animation-play-state": "", "animation-play-state": "", "-webkit-transition": "", "transition": "", "-webkit-animation": "", "animation": ""});
        },
        clean_for_save: function () {
            this.on_blur();
            this._super();
        }
    });

    website.snippet.options.media = website.snippet.Option.extend({
        start: function () {
            this._super();
            website.snippet.start_animation(true, this.$target);
        },
        edition: function (type, value) {
            if(type !== "click") return;
            var self = this;
            var editor = new website.editor.MediaDialog(this.$target.closest('.o_editable'), this.$target[0]);
            editor.appendTo(document.body);
            editor.on('saved', this, function (item, old) {
                self.editor.on_blur();
                self.BuildingBlock.make_active(false);
                if (self.$target.parent().data("oe-field") !== "image") {
                    setTimeout(function () {
                        self.BuildingBlock.make_active($(item));
                    },0);
                }
            });
        },
        on_focus : function () {
            var self = this;
            var $parent = this.$target.parent();

            if ($parent.data("oe-field") === "image" && $parent.hasClass('o_editable')) {
                this.$overlay.addClass("hidden");
                self.edition('click', null);
                self.BuildingBlock.make_active(false);
            }
        }
    });

    website.snippet.options.ul = website.snippet.Option.extend({
        start: function () {
            this._super();
            this.$target.data("snippet-view", new website.snippet.animationRegistry.ul(this.$target, true));
        },
        reset_ul: function () {
            this.$target.find('.o_ul_toggle_self, .o_ul_toggle_next').remove();

            this.$target.find('li:has(>ul,>ol)').map(function () {
                    // get if the li contain a text label
                    var texts = _.filter(_.toArray(this.childNodes), function (a) { return a.nodeType == 3;});
                    if (!texts.length || !texts.reduce(function (a,b) { return a.textContent + b.textContent;}).match(/\S/)) {
                        return;
                    }
                    $(this).children('ul,ol').addClass('o_close');
                    return $(this).children(':not(ul,ol)')[0] || this;
                })
                .prepend('<a href="#" class="o_ul_toggle_self fa" />');

            var $li = this.$target.find('li:has(+li:not(>.o_ul_toggle_self)>ul, +li:not(>.o_ul_toggle_self)>ol)');
            $li.map(function () { return $(this).children()[0] || this; })
                .prepend('<a href="#" class="o_ul_toggle_next fa" />');
            $li.removeClass('o_open').next().addClass('o_close');

            this.$target.find("li").removeClass('o_open').css('list-style', '');
            this.$target.find("li:has(.o_ul_toggle_self, .o_ul_toggle_next), li:has(>ul,>ol):not(:has(>li))").css('list-style', 'none');
        },
        clean_for_save: function () {
            this._super();
            if (!this.$target.hasClass('o_ul_folded')) {
                this.$target.find(".o_close").removeClass("o_close");
            }
            this.$target.find("li:not(:has(>ul))").css('list-style', '');
        },
        toggle_class: function (type, value, $li) {
            this._super(type, value, $li);
            this.$target.data("snippet-view").stop();
            this.reset_ul();
            this.$target.find("li:not(:has(>ul))").css('list-style', '');
            this.$target.data("snippet-view", new website.snippet.animationRegistry.ul(this.$target, true));
        }
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

            var $selector_siblings;
            for (var i=0; i<self.selector_siblings.length; i++) {
                if (!$selector_siblings) $selector_siblings = self.selector_siblings[i].all();
                else $selector_siblings = $selector_siblings.add(self.selector_siblings[i].all());
            }
            var $selector_children;
            for (var i=0; i<self.selector_children.length; i++) {
                if (!$selector_children) $selector_children = self.selector_children[i].all();
                else $selector_children = $selector_children.add(self.selector_children[i].all());
            }

            self.BuildingBlock.activate_insertion_zones($selector_siblings, $selector_children);

            $("body").addClass('move-important');

            self._drag_and_drop_after_insert_dropzone();
            self._drag_and_drop_active_drop_zone($('.oe_drop_zone'));
        },
        _drag_and_drop_stop: function (){
            var self = this;
            var $dropzone = this.$target.prev();
            var prev = $dropzone.length && $dropzone[0].previousSibling;
            var next = this.$target.last()[0].nextSibling;
            var $parent = this.$target.parent();

            $(".oe_drop_clone").after(this.$target);

            this.$overlay.removeClass("hidden");
            $("body").removeClass('move-important');
            $('.oe_drop_zone').droppable('destroy').remove();
            $(".oe_drop_clone, .oe_drop_to_remove").remove();

            if (this.dropped) {
                this.BuildingBlock.parent.rte.historyRecordUndo(this.$target);

                if (prev) {
                    this.$target.insertAfter(prev);
                } else if (next) {
                    this.$target.insertBefore(next);
                } else {
                    $parent.prepend(this.$target);
                }
            }

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
                if (!val.selector.is(self.$target)) {
                    return;
                }
                if (val['drop-near']) self.selector_siblings.push(val['drop-near']);
                if (val['drop-in']) self.selector_children.push(val['drop-in']);

                var option = val['option'];
                var Editor = website.snippet.options[option] || website.snippet.Option;
                var editor = self.styles[option] = new Editor(self.BuildingBlock, self, self.$target, option_id);
                $ul.append(editor.$el.addClass("snippet-option-" + option));
                editor.start();
            });

            if (!this.selector_siblings.length && !this.selector_children.length) {
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
            var $parent = website.snippet.globalSelector.closest(this.$target.parent());
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
            if (!this.$target.parent().is(':o_editable')) {
                this.$overlay.find('.oe_snippet_move, .oe_snippet_clone, .oe_snippet_remove').remove();
            } else {
                this.$overlay.on('click', '.oe_snippet_clone', _.bind(this.on_clone, this));
                this.$overlay.on('click', '.oe_snippet_remove', _.bind(this.on_remove, this));
                this._drag_and_drop();
            }
        },

        on_clone: function (event) {
            event.preventDefault();
            var $clone = this.$target.clone(false);
            this.$target.after($clone);
            for (var i in this.styles){
                this.styles[i].on_clone($clone);
            }
            this.BuildingBlock.create_overlay(this.$target);
            return false;
        },

        on_remove: function (event) {
            event.preventDefault();
            this.on_blur();

            this.BuildingBlock.parent.rte.historyRecordUndo(this.$target);

            var index = _.indexOf(this.BuildingBlock.snippets, this.$target.get(0));
            for (var i in this.styles){
                this.styles[i].on_remove();
            }
            delete this.BuildingBlock.snippets[index];

            // remove node and his empty
            var node = this.$target.parent()[0];

            this.$target.remove();
            this.$overlay.remove();

            if (node && node.firstChild) {
                $.summernote.core.dom.removeSpace(node, node.firstChild, 0, node.lastChild, 1);
                if (!node.firstChild.tagName && node.firstChild.textContent === " ") {
                    node.firstChild.parentNode.removeChild(node.firstChild);
                }
            }

            // clean editor if they are image or table in deleted content
            $(".note-control-selection").hide();
            $('.o_table_handler').remove();

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

    /* t-field options */

    website.snippet.options.many2one = website.snippet.Option.extend({
        start: function () {
            var self = this;

            this.Model = this.$target.data('oe-many2one-model');
            this.ID = +this.$target.data('oe-many2one-id');

            // create search button and bind search bar
            this.$btn = $(openerp.qweb.render("website.many2one.button"))
                .insertAfter(this.$overlay.find('.oe_options'));

            this.$ul = this.$btn.find("ul");
            this.$search = this.$ul.find('li:first');
            this.$search.find('input').on('mousedown click mouseup keyup keydown', function (e) {
                e.stopPropagation();
            });

            // move menu item
            setTimeout(function () {
                if (self.$overlay.find('.oe_options').hasClass('hidden')) {
                    self.$btn.css('height', '0').find('> a').addClass('hidden');
                    self.$ul.show().css({
                        'top': '-24px', 'margin': '0', 'padding': '2px 0', 'position': 'relative'
                    });
                } else {
                    self.$btn.find('a').on('click', function (e) {
                        self.clear();
                    });
                }
            },0);

            // bind search input
            this.$search.find('input')
                .focus()
                .on('keyup', function(e) {
                    self.find_existing($(this).val());
                });

            // bind result
            this.$ul.on('click', "li:not(:first) a", function (e) {
                self.select_record(this);
            });
        },

        on_focus: function () {
            this.$target.attr('contentEditable', 'false');
            this.clear();
            this._super();
        },

        clear: function () {
            var self = this;
            this.$search.siblings().remove();
            self.$search.find('input').val("");
            setTimeout(function () {
                self.$search.find('input').focus();
            },0);
        },

        find_existing: function (name) {
            var self = this;
            var domain = [];
            if (!name || !name.length) {
                self.$search.siblings().remove();
                return;
            }
            if (isNaN(+name)) {
                if (this.Model === "res.partner") {
                    domain.push(['name', 'ilike', name]);
                } else {
                    domain.push('|', ['name', 'ilike', name], ['email', 'ilike', name]);
                }
            } else {
                domain.push(['id', '=', name]);
            }

            openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: this.Model,
                method: 'search_read',
                args: [domain, this.Model === "res.partner" ? ['name', 'display_name', 'city', 'country_id'] : ['name', 'display_name']],
                kwargs: {
                    order: 'name DESC',
                    limit: 5,
                    context: website.get_context(),
                }
            }).then(function (result){
                self.$search.siblings().remove();
                self.$search.after(openerp.qweb.render("website.many2one.search",{contacts:result}));
            });
        },

        get_contact_rendering: function (options) {
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.qweb.field.contact',
                method: 'get_record_to_html',
                args: [[this.ID]],
                kwargs: {
                    options: options,
                    context: website.get_context(),
                }
            });
        },

        select_record: function (li) {
            var self = this;

            self.ID = +$(li).data("id");
            self.$target.attr('data-oe-many2one-id', self.ID).data('oe-many2one-id', self.ID);

            if (self.$target.data('oe-type') === "contact") {
                $('[data-oe-contact-options]')
                    .filter('[data-oe-model="'+self.$target.data('oe-model')+'"]')
                    .filter('[data-oe-id="'+self.$target.data('oe-id')+'"]')
                    .filter('[data-oe-field="'+self.$target.data('oe-field')+'"]')
                    .filter('[data-oe-contact-options!="'+self.$target.data('oe-contact-options')+'"]')
                    .add(self.$target)
                    .attr('data-oe-many2one-id', self.ID).data('oe-many2one-id', self.ID)
                    .each(function () {
                        var $node = $(this);
                        self.get_contact_rendering($node.data('oe-contact-options'))
                            .then(function (html){
                                $node.html(html);
                            });
                    });
            } else {
                self.$target.html($(li).data("name"));
            }

            self.clear();
        }
    });


    /* end*/

})();
