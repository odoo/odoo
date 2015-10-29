odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var Class = require('web.Class');
var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var animation = require('web_editor.snippets.animation');
var options = require('web_editor.snippets.options');

var qweb = core.qweb;
var dummy = editor.dummy;

/* ----- SNIPPET SELECTOR ---- */

ajax.loadXML('/web_editor/static/src/xml/snippets.xml', qweb);

editor.Class.include({
    init: function() {
        var self = this;
        var res = this._super.apply(this, arguments);
        var $editable = this.rte.editable();
        this.buildingBlock = new BuildingBlock(this, $editable);
        this.buildingBlock.on("snippets:ready", this, function () {
            self.trigger("snippets:ready");
        });
        return res;
    },
    start: function () {
        var self = this;
        animation.stop();
        this.buildingBlock.insertAfter(this.$el);
        animation.start(true);

        this.rte.editable().find("*").off('mousedown mouseup click');
        return this._super();
    },
    save: function () {
        this.buildingBlock.clean_for_save();
        this._super();
    },
});

/* ----- SNIPPET SELECTOR ---- */

$.extend($.expr[':'],{
    hasData: function(node,i,m){
        return !!_.toArray(node.dataset).length;
    },
    data: function(node,i,m){
        return $(node).data(m[3]);
    }
});

var globalSelector = {
    closest: function () { return $(); },
    all: function () { return $(); },
    is: function () { return false; },
};

/* ----- Jquery activate block ---- */

$.fn.extend({
    activateBlock: function () {
        var target = globalSelector.closest($(this))[0] || (dom.isBR(this) ? this.parentNode : dom.node(this));
        var evt = document.createEvent("MouseEvents");
        evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
        target.dispatchEvent(evt);
        return this;
    }
});

/* ----- BuildingBlock (managment of drag&drop and focus/blur snippets) ---- */

var BuildingBlock = Widget.extend({
    template: 'web_editor.snippets',
    activeSnippets: [],
    init: function (parent, $editable) {
        this.parent = parent;
        this.$editable = $editable;

        this._super.apply(this, arguments);
        if(!$('#oe_manipulators').length){
            $("<div id='oe_manipulators' class='o_css_editor'></div>").appendTo('body');
        }
        this.$active_snipped_id = false;
        this.snippets = [];
        
        data.instance = this;
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
        $.summernote.core.dom.isNotBreakable = function (node) {
            return _isNotBreakable(node) || $(node).is('div') || globalSelector.is($(node));
        };

        $(window).on('resize', function () {
            if (self.$active_snipped_id && self.$active_snipped_id.data("snippet-editor")) {
                self.cover_target(self.$active_snipped_id.data("snippet-editor").$overlay, self.$active_snipped_id);
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
        return '/web_editor/snippets';
    },
    _add_check_selector : function (selector, no_check, is_children) {
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
                all: is_children ? function ($from) {
                    return ($from || self.$editable).find(selector);
                } : function ($from) {
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
        var url = this._get_snippet_url();
        if (!url || !url.length) {
            this.$snippet.detach();
            return;
        }
        this.$el.find("#o_left_bar").addClass("hidden");
        return ajax.jsonRpc(url, 'call', {}).then(function (html) {
            self.compute_snippet_templates(html);
            self.trigger("snippets:ready");
        }, function () {
            self.$snippet.hide();
            console.warn('Snippets template not found:', url);
        });
    },
    compute_snippet_templates: function (html) {
        var self = this;
        var $html = $(html);
        var $left_bar = this.$el.find("#o_left_bar");
        var $ul = $html.siblings("ul");
        var $scroll = $html.siblings("#o_scroll");

        if (!$scroll.length) {
            throw new Error("Wrong snippets xml definition");
        }

        $ul.children().tooltip({
                delay: { "show": 500, "hide": 100 },
                container: 'body',
                title: function () {
                    return (navigator.appVersion.indexOf('Mac') > -1 ? 'CMD' : 'CTRL')+'+SHIFT+'+($(this).index()+1);
                },
                trigger: 'hover',
                placement: 'top'
            }).on('click', function () {$(this).tooltip('hide');});

        // t-snippet
        $html.find('[data-oe-type="snippet"][data-oe-name]').each(function () {
            var $div = $('<div/>').insertAfter(this).append(this).attr('name', $(this).data('oe-name'));
        });
        // end

        self.templateOptions = [];
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
                'drop-near': $style.data('drop-near') && self._add_check_selector($style.data('drop-near'), no_check, true),
                'drop-in': $style.data('drop-in') && self._add_check_selector($style.data('drop-in'), no_check),
                'data': $style.data()
            };
            self.templateOptions.push(option);
            selector.push(option.selector);
        });

        $styles.addClass("hidden");
        globalSelector.closest = function ($from) {
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
        };
        globalSelector.all = function ($from) {
                var $target;
                var len = selector.length;
                for (var i = 0; i<len; i++) {
                    if (!$target) $target = selector[i].all($from);
                    else $target = $target.add(selector[i].all($from));
                }
                return $target;
        };
        globalSelector.is = function ($from) {
                var len = selector.length;
                for (var i = 0; i<len; i++) {
                    if (selector[i].is($from)) {
                        return true;
                    }
                }
                return false;
        };

        var number = 0;

        // oe_snippet_body
        self.$snippets = $scroll.find(".o_panel_body").children()
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
                if (!$(this).data("selector")) {
                    $("> *:not(.oe_snippet_thumbnail)", this).addClass('oe_snippet_body');
                }
                number++;
            });

        // hide scroll if no snippets defined
        if (!number) {
            this.$snippet.detach();
        } else {
            this.$el.find("#o_left_bar").removeClass("hidden");
        }
        $("body").toggleClass("editor_has_snippets", !!number);

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
        $html.find('[data-oe-model], [data-oe-type]').each(function () {
            for (var k=0; k<this.attributes.length; k++) {
                if (this.attributes[k].name.indexOf('data-oe-') === 0) {
                    $(this).removeAttr(this.attributes[k].name);
                    k--;
                }
            }
        });
        // end

        $html.find('.o_not_editable').attr("contentEditable", false);

        $left_bar.html($html);

        // animate for list of snippet blocks
        $left_bar.on('click', '.scroll-link', function (event) {
            event.preventDefault();
            var targetOffset =  $($(this).attr("href")).position().top - $ul.outerHeight() + $scroll[0].scrollTop;
            $scroll.animate({'scrollTop': targetOffset}, 750);
        });
        $scroll.on('scroll', function () {
            var middle = $scroll.height()/4;
            var $li = $ul.find("a").parent().removeClass('active');
            var last;
            for (var k=0; k<$li.length; k++) {
                var li = $($li[k]);
                if (!li.data('target')) {
                    li.data('target', $($("a", li).attr("href")));
                }
                if (li.data('target').position().top > middle) {
                    break;
                }
                last = $li[k];
            }
            $(last).addClass("active");
        });
        // end

        // display scrollbar
        $(window).on('resize', function () {
            $scroll.css("overflow", "");
            var height = $left_bar.height() - $ul.outerHeight();
            $scroll.css("height", height);
            var $last = $scroll.children(":visible").last().children(".o_panel_body");
            $last.css({'min-height': (height-$last.prev().outerHeight())+'px'});
            if ($scroll[0].scrollHeight + $ul[0].scrollHeight > document.body.clientHeight) {
                $scroll.css("overflow", "auto").css("width", "226px");
            } else {
                $scroll.css("width", "");
            }
        }).trigger('resize');
        // end

        self.make_snippet_draggable(self.$snippets);
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
        var self = this;
        var cache = {};
        this.$snippet.find(".o_panel").each(function () {
            var catcheck = false;
            var $category = $(this);
            $category.find(".oe_snippet_body").each(function () {
                var $snippet = $(this);

                var check = false;

                for (var k in self.templateOptions) {
                    var option = self.templateOptions[k];
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

            if (!globalSelector.is($target)) {
                $target = globalSelector.closest($target);
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
        var opt = options.registry;
        var template = self.templateOptions;
        for (var k in template) {
            var Option = opt[template[k]['option']];
            if (Option && Option.prototype.clean_for_save !== dummy) {
                template[k].selector.all().filter(function () {
                        var node = this;
                        while (!/o_dirty|o_editable/.test(node.className) && node !== document) {
                            node = node.parentNode;
                        }
                        return node.className.indexOf("o_dirty") !== -1;
                    }).each(function () {
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
            this.create_snippet_editor(this.$active_snipped_id);
            this.cover_target($snippet.data('overlay'), $snippet);
            this.snippet_focus($snippet);
        }
        this.$snippet.trigger('snippet-activated', $snippet);
        if ($snippet) {
            $snippet.trigger('snippet-activated', $snippet);
        }
    },
    create_snippet_editor: function ($snippet) {
        if (typeof $snippet.data("snippet-editor") === 'undefined') {
            if (!this.activate_overlay_zones($snippet).length) return;
            $snippet.data("snippet-editor", new Editor(this, $snippet));
        }
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
                var temp = self.templateOptions;
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

                    $toInsert.closest(".o_editable").trigger("content_changed");

                    var $target = false;
                    $target = $toInsert;

                    setTimeout(function () {
                        self.$snippet.trigger('snippet-dropped', $target);

                        animation.start(true, $target);

                        self.call_for_all_snippets($target, function (editor, $snippet) {
                            editor.drop_and_build_snippet();
                        });
                        self.create_snippet_editor($target);
                        self.cover_target($target.data('overlay'), $target);
                        $target.closest(".o_editable").trigger("content_changed");

                        self.make_active($target);
                    },0);
                } else {
                    $toInsert.remove();
                }
            },
        });
    },

    // call a method on a snippet and all his children
    call_for_all_snippets: function ($snippet, callback) {
        var self = this;
        $snippet.add(globalSelector.all($snippet)).each(function () {
            var $snippet = $(this);
            setTimeout(function () {
                self.create_snippet_editor($snippet);
                if ($snippet.data("snippet-editor")) {
                    callback.call(self, $snippet.data("snippet-editor"), $snippet);
                }
            });
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
                var $zone = $(qweb.render('web_editor.snippet_overlay'));

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
                    clearTimeout(timer);
                    timer = setTimeout(function () {
                        if ($target.data('overlay') && $target.data('overlay').hasClass("oe_active")) {
                            self.cover_target($target.data('overlay'), $target);
                        }
                    },50);
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

/* ----- Editor (object who contain overlay and the option list) ---- */

var Editor = Class.extend({
    init: function (BuildingBlock, dom) {
        this.buildingBlock = BuildingBlock;
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
        self.buildingBlock.hide();
        self.buildingBlock.editor_busy = true;
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

        self.buildingBlock.activate_insertion_zones($selector_siblings, $selector_children);

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
            this.buildingBlock.parent.rte.historyRecordUndo(this.$target);

            if (prev) {
                this.$target.insertAfter(prev);
            } else if (next) {
                this.$target.insertBefore(next);
            } else {
                $parent.prepend(this.$target);
            }

            for (var i in this.styles){
                this.styles[i].on_move();
            }
        }

        self.buildingBlock.editor_busy = false;

        self.get_parent_block();
        setTimeout(function () {
            self.buildingBlock.cover_target(self.$target.data('overlay'), self.$target);
        },0);
    },

    load_style_options: function () {
        var self = this;
        var $styles = this.$overlay.find('.oe_options');
        var $ul = $styles.find('ul:first');
        this.styles = {};
        this.selector_siblings = [];
        this.selector_children = [];
        _.each(this.buildingBlock.templateOptions, function (val, option_id) {
            if (!val.selector.is(self.$target)) {
                return;
            }
            if (val['drop-near']) self.selector_siblings.push(val['drop-near']);
            if (val['drop-in']) self.selector_children.push(val['drop-in']);

            var option = val['option'];
            var Editor = options.registry[option] || options.Class;
            var editor = self.styles[option] = new Editor(self.buildingBlock, self, self.$target, option_id);
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
        var $parent = this.$target.parents().filter(function () { return $(this).data("snippet-editor"); });
        if (!$parent.length) {
            $parent = globalSelector.closest(this.$target.parent());
        }
        if ($parent.length) {
            $button.removeClass("hidden");
            $button.off("click").on('click', function (event) {
                event.preventDefault();
                setTimeout(function () {
                    self.buildingBlock.make_active($parent);
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

        this.buildingBlock.parent.rte.historyRecordUndo(this.$target);

        this.$target.after($clone);
        this.buildingBlock.call_for_all_snippets($clone, function (editor, $snippet) {
            for (var i in editor.styles){
                editor.styles[i].on_clone($snippet);
            }
        });
        return false;
    },

    on_remove: function (event) {
        event.preventDefault();
        this.on_blur();

        this.buildingBlock.parent.rte.historyRecordUndo(this.$target);

        var index = _.indexOf(this.buildingBlock.snippets, this.$target.get(0));
        this.buildingBlock.call_for_all_snippets(this.$target, function (editor, $snippet) {
            for (var i in editor.styles){
                editor.styles[i].on_remove();
            }
        });
        delete this.buildingBlock.snippets[index];

        var $editable = this.$target.closest(".o_editable");

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

var data = {
    Class: BuildingBlock,
    Editor: Editor,
    globalSelector: globalSelector,
};
return data;

});
