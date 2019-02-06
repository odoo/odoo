odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var Class = require('web.Class');
var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var editor = require('web_editor.editor');
var animation = require('web_editor.snippets.animation');
var options = require('web_editor.snippets.options');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/web_editor/static/src/xml/snippets.xml', qweb);

var data = {};

/* ----- SNIPPET SELECTOR ---- */

$.extend($.expr[':'], {
    hasData: function (node) {
        return !!_.toArray(node.dataset).length;
    },
    data: function (node, i, m) {
        return $(node).data(m[3]);
    }
});

data.globalSelector = {
    closest: function () { return $(); },
    all: function () { return $(); },
    is: function () { return false; },
};

/**
 * Snippet editor main class.
 * Management of drag&drop and focus/blur of snippets.
 * Previously named "BuildingBlock".
 */
data.Class = Widget.extend({
    id: "oe_snippets",
    activeSnippets: [],
    init: function (parent, $editable) {
        this.$editable = $editable;

        this._super.apply(this, arguments);
        if(!$('#oe_manipulators').length) {
            $("<div/>", {id: "oe_manipulators",  'class': "o_css_editor"}).appendTo('body');
        }
        this.$active_snipped_id = false;
        this.snippets = [];

        data.instance = this;
    },
    start: function () {
        var self = this;

        $(window).resize(function () {
            _.defer(function () { $(document).click(); });
        });

        this.fetch_snippet_templates();
        this.bind_snippet_click_editor();

        $(document).on('click', '.dropdown-submenu a[tabindex]', function (e) {
            e.preventDefault();
        });

        var _isNotBreakable = $.summernote.core.dom.isNotBreakable;
        $.summernote.core.dom.isNotBreakable = function (node) {
            return _isNotBreakable(node) || $(node).is('div') || data.globalSelector.is($(node));
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
                self.$('.scroll:first > ul li:eq('+(event.keyCode-49)+') a').trigger("click");
                event.preventDefault();
            }
        });
    },

    _get_snippet_url: function () {
        return '/web_editor/snippets';
    },
    _add_check_selector : function (selector, no_check, is_children) {
        var self = this;
        selector = selector.split(/\s*,/).join(":not(.o_snippet_not_selectable), ") + ":not(.o_snippet_not_selectable)";

        if (no_check) {
            return {
                closest: function ($from, parentNode) {
                    return $from.closest(selector, parentNode);
                },
                all: function ($from) {
                    return $from ? cssFind($from, selector) : $(selector);
                },
                is: function ($from) {
                    return $from.is(selector);
                }
            };
        } else {
            selector = selector.split(/\s*,/).join(":o_editable, ") + ":o_editable";
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
                    return cssFind($from || self.$editable, selector);
                } : function ($from) {
                    $from = $from || self.$editable;
                    return $from.filter(selector).add(cssFind($from, selector));
                },
                is: function ($from) {
                    return $from.is(selector);
                }
            };
        }

        /**
         * jQuery find function behavior is:
         *      $('A').find('A B') <=> $('A A B')
         * The searches behavior to find options' DOM needs to be
         *      $('A').find('A B') <=> $('A B')
         * This is what this function does.
         *
         * @param {jQuery} $from - the jQuery element(s) from which to search
         * @param {string} selector - the CSS selector to match
         * @returns {jQuery}
         */
        function cssFind($from, selector) {
            return $from.find('*').filter(selector);
        }
    },

    fetch_snippet_templates: function () {
        var self = this;
        var url = this._get_snippet_url();
        if (!url || !url.length) {
            this.$el.detach();
            return;
        }
        return ajax.jsonRpc(url, 'call', {}).then(function (html) {
            self.compute_snippet_templates(html);
            self.trigger("snippets:ready");
        }, function () {
            console.warn('Snippets template not found:', url);
        });
    },
    compute_snippet_templates: function (html) {
        var self = this;
        var $html = $(html);
        var $scroll = $html.siblings("#o_scroll");

        if (!$scroll.length) {
            throw new Error("Wrong snippets xml definition");
        }

        // t-snippet
        $html.find('[data-oe-type="snippet"]').each(function () {
            $(this).children().attr('data-oe-type', "snippet").attr('data-oe-thumbnail', $(this).data('oe-thumbnail'));
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
        data.globalSelector.closest = function ($from) {
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
        data.globalSelector.all = function ($from) {
            var $target;
            var len = selector.length;
            for (var i = 0; i<len; i++) {
                if (!$target) $target = selector[i].all($from);
                else $target = $target.add(selector[i].all($from));
            }
            return $target;
        };
        data.globalSelector.is = function ($from) {
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
                var $snippet = $(this);
                if (!$('.oe_snippet_thumbnail', this).size()) {
                    var $div = $(
                        '<div class="oe_snippet_thumbnail">'+
                            '<div class="oe_snippet_thumbnail_img"/>'+
                            '<span class="oe_snippet_thumbnail_title"></span>'+
                        '</div>');
                    $div.find('span').text($snippet.attr("name"));
                    $snippet.prepend($div);

                    // from t-snippet
                    var thumbnail = $("[data-oe-thumbnail]", this).data("oe-thumbnail");
                    if (thumbnail) {
                        $div.find('.oe_snippet_thumbnail_img').css('background-image', 'url(' + thumbnail + ')');
                    }
                    // end
                }
                if (!$snippet.data("selector")) {
                    $("> *:not(.oe_snippet_thumbnail)", this).addClass('oe_snippet_body');
                }
                number++;
            });

        // hide scroll if no snippets defined
        if (!number) {
            this.$el.detach();
        }
        $("body").toggleClass("editor_has_snippets", !!number);

        // select all default text to edit (if snippet default text)
        this.add_default_snippet_text_classes();
        $(document).on("click", ".o_default_snippet_text", function (event) {
            $(event.target).selectContent();
        });
        $(document).on("keyup", function (event) {
            var r = $.summernote.core.range.create();
            $(r && r.sc).closest(".o_default_snippet_text").removeClass("o_default_snippet_text");
        });

        // clean t-oe
        $html.find('[data-oe-model], [data-oe-type]').each(function () {
            for (var k=0; k<this.attributes.length; k++) {
                if (this.attributes[k].name.indexOf('data-oe-') === 0) {
                    $(this).removeAttr(this.attributes[k].name);
                    k--;
                }
            }
        });

        $html.find('.o_not_editable').attr("contentEditable", false);

        this.$el.html($html);

        self.make_snippet_draggable(self.$snippets);
        this.associate_snippet_names(this.$snippets);

        this.show_blocks();
        this.$el.on("snippet-dropped snippet-removed", this.show_blocks.bind(this));
    },

    associate_snippet_names: function ($snippets) {
        _.each($snippets, function (snippet) {
            var $snippet = $(snippet);
            var $sbody = $snippet.find(".oe_snippet_body");
            var snippet_classes = $sbody.attr("class").match(/s_[^ ]+/g);
            if (snippet_classes && snippet_classes.length) {
                snippet_classes = snippet_classes.join(".");
            }
            $("#wrapwrap ." + snippet_classes).data("name", $snippet.find(".oe_snippet_thumbnail_title").text());
        });
    },

    add_default_snippet_text_classes: function ($in) {
        if ($in === undefined) {
            $in = this.$snippets.find(".oe_snippet_body");
        }

        $in.find("*").addBack()
            .contents()
            .filter(function () {
                return this.nodeType === 3 && this.textContent.match(/\S/);
            }).parent().addClass("o_default_snippet_text");
    },

    cover_target: function ($el, $target) {
        if ($el.data('not-cover_target')) {
            return;
        }
        var pos = $target.offset();
        var mt = parseInt($target.css("margin-top") || 0);
        $el.css({
            width: $target.outerWidth(),
            left: pos.left,
            top: pos.top - mt,
        });
        $el.find('.oe_handles').css({
            height: $target.outerHeight(true),
        });

        $el.toggleClass('o_top_cover', pos.top <= (this.$('#o_scroll').position().top + 15));
    },

    show_blocks: function () {
        var self = this;
        var cache = {};
        this.$snippets.each(function () {
            var $snippet = $(this);
            var $snippet_body = $snippet.find(".oe_snippet_body");

            var check = false;
            _.each(self.templateOptions, function (option, k) {
                if (check || !$snippet_body.is(option.base_selector)) return;

                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? option['drop-near'].all().length : 0,
                    'drop-in': option['drop-in'] ? option['drop-in'].all().length : 0
                };
                check = (cache[k]['drop-near'] || cache[k]['drop-in']);
            });

            $snippet.toggleClass("disable", !check);
        });
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

            if (!data.globalSelector.is($target)) {
                $target = data.globalSelector.closest($target);
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
            if (Option && Option.prototype.clean_for_save !== editor.dummy) {
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
        this.$el.trigger('snippet-activated', $snippet);
        if ($snippet) {
            $snippet.trigger('snippet-activated', $snippet);
        }
    },
    create_snippet_editor: function ($snippet) {
        if (typeof $snippet.data("snippet-editor") === 'undefined') {
            if (!this.activate_overlay_zones($snippet).length) return;
            $snippet.data("snippet-editor", new data.Editor(this, $snippet));
        }
    },

    // activate drag and drop for the snippets in the snippet toolbar
    make_snippet_draggable: function ($snippets) {
        var self = this;
        var $tumb = $snippets.find(".oe_snippet_thumbnail_img:first");
        var left = $tumb.outerWidth()/2;
        var top = $tumb.outerHeight()/2;
        var $toInsert, dropped, $snippet;

        $snippets.draggable({
            greedy: true,
            helper: 'clone',
            zIndex: '1000',
            appendTo: 'body',
            cursor: "move",
            handle: ".oe_snippet_thumbnail",
            distance: 30,
            cursorAt: {
                'left': left,
                'top': top
            },
            start: function () {
                dropped = false;
                // snippet_selectors => to get drop-near, drop-in
                $snippet = $(this);
                var $base_body = $snippet.find('.oe_snippet_body');
                var $selector_siblings = $();
                var $selector_children = $();
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

                $toInsert = $base_body.clone().data("name", $snippet.find(".oe_snippet_thumbnail_title").text());

                if (!$selector_siblings.length && !$selector_children.length) {
                    console.warn($snippet.find(".oe_snippet_thumbnail_title").text() + " have not insert action: data-drop-near or data-drop-in");
                    return;
                }

                self.make_active(false);
                self.activate_insertion_zones($selector_siblings, $selector_children);

                $('.oe_drop_zone').droppable({
                    over: function () {
                        dropped = true;
                        $(this).first().after($toInsert).addClass('hidden');
                    },
                    out: function () {
                        var prev = $toInsert.prev();
                        if(this === prev[0]) {
                            dropped = false;
                            $toInsert.detach();
                            $(this).removeClass('hidden');
                        }
                    },
                });
            },
            stop: function (ev, ui) {
                $toInsert.removeClass('oe_snippet_body');

                if (! dropped && self.$editable.find('.oe_drop_zone') && ui.position.top > 3 && ui.position.left + 50 > self.$el.outerWidth()) {
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
                    var rte = self.getParent().rte;

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
                        self.$el.trigger('snippet-dropped', $target);

                        animation.start(true, $target);

                        self.call_for_all_snippets($target, function (editor, $snippet) {
                            _.defer(function () { editor.drop_and_build_snippet(); });
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
        $snippet.add(data.globalSelector.all($snippet)).each(function () {
            var $snippet = $(this);
            self.create_snippet_editor($snippet);
            if ($snippet.data("snippet-editor")) {
                callback.call(self, $snippet.data("snippet-editor"), $snippet);
            }
        });
    },

    // return the original snippet in the editor bar from a snippet id (string)
    get_snippet_from_id: function (id) {
        return $('.oe_snippet').filter(function () {
            return $(this).data('option') === id;
        }).first();
    },

    // Create element insertion drop zones. two css selectors can be provided
    // selector.children -> will insert drop zones as direct child of the selected elements
    //   in case the selected elements have children themselves, dropzones will be interleaved
    //   with them.
    // selector.siblings -> will insert drop zones after and before selected elements
    activate_insertion_zones: function ($selector_siblings, $selector_children) {
        var self = this;
        var zone_template = $("<div class='oe_drop_zone oe_insert'/>");

        function isFullWidth($elem) {
            return $elem.parent().width() === $elem.outerWidth(true);
        }

        if ($selector_children) {
            $selector_children.each(function () {
                var $zone = $(this);
                var css = window.getComputedStyle(this);
                var float = css.float || css.cssFloat;
                var $drop = zone_template.clone();

                $zone.append($drop);
                var node = $drop[0].previousSibling;
                var test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === "BR"));
                if (test) {
                    $drop.addClass("oe_vertical").css({
                        'height': parseInt(window.getComputedStyle($zone[0]).lineHeight),
                        'float': 'none',
                        'display': 'inline-block'
                    });
                } else if (float === "left" || float === "right") {
                    $drop.css('float', float);
                    if (!isFullWidth($zone)) {
                        $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().last().outerHeight()), 30));
                    }
                }

                $drop = $drop.clone();

                $zone.prepend($drop);
                node = $drop[0].nextSibling;
                test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === "BR"));
                if (test) {
                    $drop.addClass("oe_vertical").css({
                        'height': parseInt(window.getComputedStyle($zone[0]).lineHeight),
                        'float': 'none',
                        'display': 'inline-block'
                    });
                } else if (float === "left" || float === "right") {
                    $drop.css('float', float);
                    if (!isFullWidth($zone)) {
                        $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().first().outerHeight()), 30));
                    }
                }
                if (test) {
                    $drop.css({'float': 'none', 'display': 'inline-block'});
                }
            });

            // add children near drop zone
            $selector_siblings = $(_.uniq(($selector_siblings || $()).add($selector_children.children()).get()));
        }

        if ($selector_siblings) {
            $selector_siblings.filter(':not(.oe_drop_zone):not(.oe_drop_clone)').each(function () {
                var $zone = $(this);
                var $drop;
                var css = window.getComputedStyle(this);
                var float = css.float || css.cssFloat;

                if($zone.prev('.oe_drop_zone:visible').length === 0) {
                    $drop = zone_template.clone();
                    if (float === "left" || float === "right") {
                        $drop.css('float', float);
                        if (!isFullWidth($zone)) {
                            $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.prev().outerHeight() || Infinity), 30));
                        }
                    }
                    $zone.before($drop);
                }
                if($zone.next('.oe_drop_zone:visible').length === 0) {
                    $drop = zone_template.clone();
                    if (float === "left" || float === "right") {
                        $drop.css('float', float);
                        if (!isFullWidth($zone)) {
                            $drop.addClass("oe_vertical").css('height', Math.max(Math.min($zone.outerHeight(), $zone.next().outerHeight() || Infinity), 30));
                        }
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
        $zones.each(function () {
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
                &&  (float_next === 'left' || float_next === 'right')  ) {
                zone.remove();
            }else if( !( disp_prev === null
                      || disp_next === null
                      || disp_prev === 'block'
                      || disp_next === 'block' )) {
                zone.remove();
            }
        });
    },

    // generate drop zones covering the elements selected by the selector
    // we generate overlay drop zones only to get an idea of where the snippet are, the drop
    activate_overlay_zones: function ($targets) {
        var self = this;

        function is_visible($el) {
            return     $el.css('display')    !== 'none'
                    && $el.css('opacity')    !== '0'
                    && $el.css('visibility') !== 'hidden';
        }

        // filter out invisible elements
        $targets = $targets.filter(function () { return is_visible($(this)); });

        // filter out elements with invisible parents
        $targets = $targets.filter(function () {
            var parents = $(this).parents().filter(function () { return !is_visible($(this)); });
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
                        $target.each(function () {
                           // check if clicked point (taken from event) is inside element
                            event.srcElement = this;
                            $(this).trigger(event.type);
                        });
                        return false;
                    });
                }

                $zone.appendTo('#oe_manipulators');
                $zone.data('target', $target);
                $target.data('overlay', $zone);

                var timer;
                $target.closest('.o_editable').on("content_changed", function (event) {
                    clearTimeout(timer);
                    timer = setTimeout(function () {
                        if ($target.data('overlay') && $target.data('overlay').hasClass("oe_active")) {
                            self.cover_target($target.data('overlay'), $target);
                        }
                    }, 50);
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

/**
 * Snippet editor Editor class.
 * Management of the overlay and option list for a snippet.
 */
data.Editor = Class.extend({
    init: function (BuildingBlock, dom) {
        this.buildingBlock = BuildingBlock;
        this.$target = $(dom);
        this.$overlay = this.$target.data('overlay');

        // Initialize parent button
        this.init_parent_options();

        // Load overlay options content
        this.load_style_options();

        // Initialize move/clone/remove buttons
        if (!this.$target.parent().is(':o_editable')) {
            this.$overlay.find('.oe_snippet_move, .oe_snippet_clone, .oe_snippet_remove').remove();
        } else {
            this.$overlay.on('click', '.oe_snippet_clone', _.bind(this.on_clone, this));
            this.$overlay.on('click', '.oe_snippet_remove', _.bind(this.on_remove, this));
            this._drag_and_drop();
        }
    },

    getName: function () {
        if (this.$target.data("name") !== undefined) {
            return this.$target.data("name");
        }
        if (this.$target.parent(".row").length) {
            return _t("Column");
        }
        return _t("Block");
    },

    // activate drag and drop for the snippets in the snippet toolbar
    _drag_and_drop: function () {
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
            helper: function () {
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
    _drag_and_drop_after_insert_dropzone: function () {},
    _drag_and_drop_active_drop_zone: function ($zones) {
        var self = this;
        $zones.droppable({
            over: function () {
                $(".oe_drop_zone.hide").removeClass("hide");
                $(this).addClass("hide").first().after(self.$target);
                self.dropped = true;
            },
            out: function () {
                $(this).removeClass("hide");
                self.$target.detach();
                self.dropped = false;
            },
        });
    },
    _drag_and_drop_start: function () {
        var self = this;
        this.dropped = false;
        self.buildingBlock.editor_busy = true;
        self.size = {
            width: self.$target.width(),
            height: self.$target.height()
        };
        self.$target.after("<div class='oe_drop_clone' style='display: none;'/>");
        self.$target.detach();
        self.$overlay.addClass("hidden");

        var $selector_siblings;
        for (var i = 0 ; i < self.selector_siblings.length ; i++) {
            if (!$selector_siblings) $selector_siblings = self.selector_siblings[i].all();
            else $selector_siblings = $selector_siblings.add(self.selector_siblings[i].all());
        }
        var $selector_children;
        for (i = 0 ; i < self.selector_children.length ; i++) {
            if (!$selector_children) $selector_children = self.selector_children[i].all();
            else $selector_children = $selector_children.add(self.selector_children[i].all());
        }

        self.buildingBlock.make_active(false);
        self.buildingBlock.activate_insertion_zones($selector_siblings, $selector_children);

        $("body").addClass('move-important');

        self._drag_and_drop_after_insert_dropzone();
        self._drag_and_drop_active_drop_zone($('.oe_drop_zone'));
    },
    _drag_and_drop_stop: function (ev, ui) {
        var self = this;

        // TODO lot of this is duplicated code of the d&d feature of snippets
        if (!this.dropped) {
            var $el = $.nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone').first();
            if ($el.length) {
                $el.after(this.$target);
                this.dropped = true;
            }
        }

        $(".oe_drop_zone").droppable('destroy').remove();

        var prev = this.$target.first()[0].previousSibling;
        var next = this.$target.last()[0].nextSibling;
        var $parent = this.$target.parent();

        var $clone = $(".oe_drop_clone");
        if (prev === $clone[0]) {
            prev = $clone[0].previousSibling;
        } else if (next === $clone[0]) {
            next = $clone[0].nextSibling;
        }
        $clone.after(this.$target);

        this.$overlay.removeClass("hidden");
        $("body").removeClass('move-important');
        $clone.remove();

        if (this.dropped) {
            this.buildingBlock.getParent().rte.historyRecordUndo(this.$target);

            if (prev) {
                this.$target.insertAfter(prev);
            } else if (next) {
                this.$target.insertBefore(next);
            } else {
                $parent.prepend(this.$target);
            }

            for (var i in this.styles) {
                this.styles[i].on_move();
            }
        }

        self.buildingBlock.editor_busy = false;

        self.init_parent_options();
        _.defer(function () {
            self.buildingBlock.cover_target(self.$target.data('overlay'), self.$target);
        });
    },

    load_style_options: function () {
        var self = this;
        var $styles = this.$overlay.find('.oe_options');
        var $ul = $styles.find('ul:first');
        this.styles = {};
        this.selector_siblings = [];
        this.selector_children = [];

        var i = 0;
        $ul.append($("<li/>", {"class": "dropdown-header o_main_header", text: this.getName()}).data("editor", this));
        _.each(this.buildingBlock.templateOptions, function (val, option_id) {
            if (!val.selector.is(self.$target)) {
                return;
            }
            if (val['drop-near']) self.selector_siblings.push(val['drop-near']);
            if (val['drop-in']) self.selector_children.push(val['drop-in']);

            var option = val['option'];
            self.styles[option] = new (options.registry[option] || options.Class)(self.buildingBlock, self, self.$target, option_id);
            $ul.append(self.styles[option].$el.addClass("snippet-option-" + option));
            self.styles[option].start();
            self.styles[option].__order = i++;
        });
        $ul.append($("<li/>", {"class": "divider"}));

        var $parents = this.$target.parents();
        _.each($parents, function (parent) {
            var parentEditor = $(parent).data("snippet-editor");
            if (parentEditor) {
                for (var styleName in parentEditor.styles) {
                    if (!parentEditor.styles[styleName].preventChildPropagation) {
                        $ul.append($("<li/>", {"class": "dropdown-header o_parent_editor_header", text: parentEditor.getName()}).data("editor", parentEditor));
                        break;
                    }
                }
            }
        });

        if (!this.selector_siblings.length && !this.selector_children.length) {
            this.$overlay.find(".oe_snippet_move, .oe_snippet_clone").addClass('hidden');
        }

        this.$overlay.find('[data-toggle="dropdown"]').dropdown();
    },

    /**
     * The init_parent_options method initializes the "go to parent" button and create the editor options
     * management for them if they do not already have one.
     */
    init_parent_options: function () {
        var self = this;
        var $button = this.$overlay.find('.oe_snippet_parent');
        var $parent = data.globalSelector.closest(this.$target.parent());
        if (!$parent.data("snippet-editor")) {
            this.buildingBlock.create_snippet_editor($parent);
        }

        $button.toggleClass("hidden", $parent.length === 0);
        $button.off("click").on('click', function (event) {
            event.preventDefault();
            _.defer(function () {
                self.buildingBlock.make_active($parent);
            });
        });
    },

    on_clone: function (event) {
        event.preventDefault();
        var $clone = this.$target.clone(false);

        this.buildingBlock.getParent().rte.historyRecordUndo(this.$target);

        this.$target.after($clone);
        this.buildingBlock.call_for_all_snippets($clone, function (editor, $snippet) {
            for (var i in editor.styles) {
                editor.styles[i].on_clone($snippet, {
                    isCurrent: ($snippet.is($clone)),
                });
            }
        });
        return false;
    },

    on_remove: function (event) {
        if (event !== undefined) {
            event.preventDefault();
            this.buildingBlock.getParent().rte.historyRecordUndo(this.$target);
        }

        this.on_blur();

        var index = _.indexOf(this.buildingBlock.snippets, this.$target.get(0));
        this.buildingBlock.call_for_all_snippets(this.$target, function (editor, $snippet) {
            for (var i in editor.styles) {
                editor.styles[i].on_remove();
            }
        });
        delete this.buildingBlock.snippets[index];

        var $parent = this.$target.parent();
        this.$target.find("*").andSelf().tooltip("destroy");
        this.$target.remove();
        this.$overlay.remove();

        var node = $parent[0];
        if (node && node.firstChild) {
            $.summernote.core.dom.removeSpace(node, node.firstChild, 0, node.lastChild, 1);
            if (!node.firstChild.tagName && node.firstChild.textContent === " ") {
                node.removeChild(node.firstChild);
            }
        }

        if($parent.closest(":data(\"snippet-editor\")").length) {
            while (!$parent.data("snippet-editor")) {
                var $nextParent = $parent.parent();
                if ($parent.children().length === 0 && $parent.text().trim() === "" && !$parent.hasClass("oe_structure")) {
                    $parent.remove();
                }
                $parent = $nextParent;
            }
            if ($parent.children().length === 0 && $parent.text().trim() === "" && !$parent.hasClass("oe_structure")) {
                _.defer(function () {
                    $parent.data("snippet-editor").on_remove();
                });
            }
        }

        // clean editor if they are image or table in deleted content
        $(".note-control-selection").hide();
        $('.o_table_handler').remove();

        this.buildingBlock.$el.trigger("snippet-removed");

        return false;
    },

    /*
    *  drop_and_build_snippet
    *  This method is called just after that a thumbnail is drag and dropped into a drop zone
    *  (after the insertion of this.$body, if this.$body exists)
    */
    drop_and_build_snippet: function () {
        for (var i in this.styles) {
            this.styles[i].drop_and_build_snippet();
        }
    },

    /* on_focus
    *  This method is called when the user click inside the snippet in the dom
    */
    on_focus: function () {
        this._on_focus_blur(true);
    },

    /* on_focus
    *  This method is called when the user click outside the snippet in the dom, after a focus
    */
    on_blur: function () {
        this._on_focus_blur(false);
    },

    _on_focus_blur: function (focus) {
        var do_action = (focus ? _do_action_focus : _do_action_blur);

        // Attach own and parent options on the current overlay
        var $style_button = this.$overlay.find(".oe_options");
        var $ul = $style_button.find("ul:first");
        var $headers = $ul.find(".dropdown-header:data(editor)");
        _.each($headers, (function (el) {
            var $el = $(el);
            var styles = _.values($el.data("editor").styles);
            if ($el.data("editor") !== this) {
                styles = _.filter(styles, function (option) { return !option.preventChildPropagation; });
            }

            var count = 0;
            _.each(_.sortBy(styles, "__order").reverse(), function (style) {
                if (do_action(style, $el)) {
                    count++;
                }
            });
            $el.toggleClass("hidden", count === 0);
        }).bind(this));

        // Activate the overlay
        $style_button.toggleClass("hidden", $ul.children(":not(.o_main_header):not(.divider):not(.hidden)").length === 0);
        this.$overlay.toggleClass("oe_active", !!focus);

        function _do_action_focus(style, $dest) {
            style.$el.insertAfter($dest);
            style.on_focus();
            return (style.$el.length > 0);
        }
        function _do_action_blur(style, $dest) {
            style.$el.detach();
            style.on_blur();
            return false;
        }
    },
});

/**
 * Add the ability on the main editor class to instantiate the snippet editor component
 */
editor.Class.include({
    init: function () {
        var self = this;
        var res = this._super.apply(this, arguments);
        var $editable = this.rte.editable();
        this.buildingBlock = new data.Class(this, $editable);
        this.buildingBlock.on("snippets:ready", this, function () {
            self.trigger("snippets:ready");
        });
        return res;
    },
    start: function () {
        this.buildingBlock.insertAfter(this.$el);
        this.rte.editable().find("*").off('mousedown mouseup click');
        return this._super.apply(this, arguments);
    },
    save: function () {
        this.buildingBlock.clean_for_save();
        return this._super.apply(this, arguments);
    },
});

/**
 * Add the ability the restart the animations
 */
editor.Class.include({
    start: function () {
        animation.stop();
        return this._super.apply(this, arguments).then(function () {
            animation.start(true);
        });
    },
});

return data;
});
