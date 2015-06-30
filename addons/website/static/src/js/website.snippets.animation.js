odoo.define('website.snippets.animation', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var website = require('website.website');

var readyAnimation = [];

var animationRegistry = Object.create(null);

function load_called_template () {
    var ids_or_xml_ids = _.uniq($("[data-oe-call]").map(function () {return $(this).data('oe-call');}).get());
    if (ids_or_xml_ids.length) {
        ajax.jsonRpc('/website/multi_render', 'call', {
                'ids_or_xml_ids': ids_or_xml_ids
            }).then(function (data) {
                for (var k in data) {
                    var $data = $(data[k]).addClass('o_block_'+k);
                    $("[data-oe-call='"+k+"']").each(function () {
                        $(this).replaceWith($data.clone());
                    });
                }
            });
    }
}

function start_animation(editable_mode, $target) {
    for (var k in animationRegistry) {
        var Animation = animationRegistry[k];
        var selector = "";
        if (Animation.prototype.selector) {
            if (selector !== "") selector += ", ";
            selector += Animation.prototype.selector;
        }
        if ($target) {
            if ($target.is(selector)) selector = $target;
            else continue;
        }

        $(selector).each(function () {
            var $snipped_id = $(this);
            if (    !$snipped_id.parents("#oe_snippets").length &&
                    !$snipped_id.parent("body").length &&
                    !$snipped_id.data("snippet-view")) {
                readyAnimation.push($snipped_id);
                $snipped_id.data("snippet-view", new Animation($snipped_id, editable_mode));
            } else if ($snipped_id.data("snippet-view")) {
                $snipped_id.data("snippet-view").start(editable_mode);
            }
        });
    }
}

function stop_animation() {
    $(readyAnimation).each(function() {
        var $snipped_id = $(this);
        if ($snipped_id.data("snippet-view")) {
            $snipped_id.data("snippet-view").stop();
        }
    });
}

$(document).ready(function () {
    load_called_template(); // if asset is placed into head, move this call into $(document).ready

    if ($(".o_gallery:not(.oe_slideshow)").size()) {
        // load gallery modal template
        website.add_template_file('/website/static/src/xml/website.gallery.xml');
    }

    start_animation();
});



var Animation = core.Class.extend({
    selector: false,
    $: function () {
        return this.$el.find.apply(this.$el, arguments);
    },
    init: function (dom, editable_mode) {
        this.$el = this.$target = $(dom);
        this.start(editable_mode);
    },
    /*
    *  start
    *  This method is called after init
    */
    start: function () {
    },
    /*
    *  stop
    *  This method is called to stop the animation (e.g.: when rte is launch)
    */
    stop: function () {
    },
});

animationRegistry.slider = Animation.extend({
    selector: ".carousel",
    start: function () {
        this.$target.carousel();
    },
    stop: function () {
        this.$target.carousel('pause');
        this.$target.removeData("bs.carousel");
    },
});

animationRegistry.parallax = Animation.extend({
    selector: ".parallax",
    start: function () {
        var self = this;
        setTimeout(function () {self.set_values();});
        this.on_scroll = function () {
            var speed = parseFloat(self.$target.attr("data-scroll-background-ratio") || 0);
            if (speed == 1) return;
            var offset = parseFloat(self.$target.attr("data-scroll-background-offset") || 0);
            var top = offset + window.scrollY * speed;
            self.$target.css("background-position", "0px " + top + "px");
        };
        this.on_resize = function () {
            self.set_values();
        };
        $(window).on("scroll", this.on_scroll);
        $(window).on("resize", this.on_resize);
    },
    stop: function () {
        $(window).off("scroll", this.on_scroll)
                .off("resize", this.on_resize);
    },
    set_values: function () {
        var self = this;
        var speed = parseFloat(self.$target.attr("data-scroll-background-ratio") || 0);

        if (speed === 1 || this.$target.css("background-image") === "none") {
            this.$target.css("background-attachment", "fixed").css("background-position", "0px 0px");
            return;
        } else {
            this.$target.css("background-attachment", "scroll");
        }

        this.$target.attr("data-scroll-background-offset", 0);
        var img = new Image();
        img.onload = function () {
            var offset = 0;
            var padding =  parseInt($(document.body).css("padding-top"));
            if (speed > 1) {
                var inner_offset = - self.$target.outerHeight() + this.height / this.width * document.body.clientWidth;
                var outer_offset = self.$target.offset().top - (document.body.clientHeight - self.$target.outerHeight()) - padding;
                offset = - outer_offset * speed + inner_offset;
            } else {
                offset = - self.$target.offset().top * speed;
            }
            self.$target.attr("data-scroll-background-offset", offset > 0 ? 0 : offset);
            $(window).scroll();
        };
        img.src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)/g, "");
        $(window).scroll();
    }
});

animationRegistry.share = Animation.extend({
    selector: ".oe_share",
    start: function () {
        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent($("title").text());
        this.$("a").each(function () {
            var $a = $(this);
            var url_regex = /\{url\}|%7Burl%7D/, title_regex = /\{title\}|%7Btitle%7D/;
            $a.attr("href", $(this).attr("href").replace(url_regex, url).replace(title_regex, title));
            if ($a.attr("target") && $a.attr("target").match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', function () {
                    window.open(this.href,'','menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
                    return false;
                });
            }
        });
    }
});

animationRegistry.media_video = Animation.extend({
    selector: ".media_iframe_video",
    start: function () {
        if (!this.$target.has('.media_iframe_video_size')) {
            var editor = '<div class="css_editable_mode_display">&nbsp;</div>';
            var size = '<div class="media_iframe_video_size">&nbsp;</div>';
            this.$target.html(editor+size+'<iframe src="'+this.$target.data("src")+'" frameborder="0" allowfullscreen="allowfullscreen"></iframe>');
        }
    },
});

animationRegistry.ul = Animation.extend({
    selector: "ul.o_ul_folded, ol.o_ul_folded",
    start: function () {
        this.$('.o_ul_toggle_self').off('click').on('click', function (event) {
            $(this).toggleClass('o_open');
            $(this).closest('li').find('ul,ol').toggleClass('o_close');
            event.preventDefault();
        });

        this.$('.o_ul_toggle_next').off('click').on('click', function (event) {
            $(this).toggleClass('o_open');
            $(this).closest('li').next().toggleClass('o_close');
            event.preventDefault();
        });
    },
});

/* -------------------------------------------------------------------------
Gallery Animation  

This ads a Modal window containing a slider when an image is clicked 
inside a gallery 
-------------------------------------------------------------------------*/
animationRegistry.gallery = Animation.extend({
    selector: ".o_gallery:not(.o_slideshow)",
    start: function() {
        this.$el.on("click", "img", this.click_handler);
    },
    click_handler : function(event) {
        var $cur = $(event.currentTarget);
        var edition_mode = ($cur.closest("[contenteditable='true']").size() !== 0);
        
        // show it only if not in edition mode
        if (!edition_mode) {
            var urls = [],
                idx = undefined,
                milliseconds = undefined,
                params = undefined,
                $images = $cur.closest(".o_gallery").find("img"),
                size = 0.8,
                dimensions = {
                    min_width  : Math.round( window.innerWidth  *  size*0.9),
                    min_height : Math.round( window.innerHeight *  size),
                    max_width  : Math.round( window.innerWidth  *  size*0.9),
                    max_height : Math.round( window.innerHeight *  size),
                    width : Math.round( window.innerWidth *  size*0.9),
                    height : Math.round( window.innerHeight *  size)
            };

            $images.each(function() {
                urls.push($(this).attr("src"));
            });
            var $img = ($cur.is("img") === true) ? $cur : $cur.closest("img");
            idx = urls.indexOf($img.attr("src"));

            milliseconds = $cur.closest(".o_gallery").data("interval") || false;
            params = {
                srcs : urls,
                index: idx,
                dim  : dimensions,
                interval : milliseconds,
                id: _.uniqueId("slideshow_")
            };
            var $modal = $(core.qweb.render('website.gallery.slideshow.lightbox', params));
            $modal.modal({
                keyboard : true,
                backdrop : true
            });
            $modal.on('hidden.bs.modal', function() {
                $(this).hide();
                $(this).siblings().filter(".modal-backdrop").remove(); // bootstrap leaves a modal-backdrop
                $(this).remove();

            });
            $modal.find(".modal-content, .modal-body.o_slideshow").css("height", "100%");
            $modal.appendTo(document.body);

            this.carousel = new animationRegistry.gallery_slider($modal.find(".carousel").carousel());
        }
    } // click_handler  
});

animationRegistry.gallery_slider = Animation.extend({
    selector: ".o_slideshow",
    start: function() {
        var $carousel = this.$target.is(".carousel") ? this.$target : this.$target.find(".carousel");
        var $indicator = $carousel.find('.carousel-indicators');
        var $lis = $indicator.find('li:not(.fa)');
        var $prev = $indicator.find('li.fa:first');
        var $next = $indicator.find('li.fa:last');
        var index = ($lis.filter('.active').index() || 1) -1;
        var page = Math.floor(index / 10);
        var nb = Math.ceil($lis.length / 10);

         // fix bootstrap use index insead of data-slide-to
        $carousel.on('slide.bs.carousel', function() {
            setTimeout(function () {
                var $item = $carousel.find('.carousel-inner .prev, .carousel-inner .next');
                var index = $item.index();
                $lis.removeClass("active")
                    .filter('[data-slide-to="'+index+'"]')
                    .addClass("active");
            },0);
        });

        function hide () {
            $lis.addClass('hidden').each(function (i) {
                if (i >= page*10 && i < (page+1)*10) {
                    $(this).removeClass('hidden');
                }
            });
            $prev.css('visibility', page === 0 ? 'hidden' : '');
            $next.css('visibility', (page+1) >= nb ? 'hidden' : '');
        }

        $indicator.find('li.fa').on('click', function () {
            page = (page + ($(this).hasClass('o_indicators_left')?-1:1)) % nb;
            $carousel.carousel(page*10);
            hide();
        });
        hide();

        $carousel.on('slid.bs.carousel', function() {
            var index = ($lis.filter('.active').index() || 1) -1;
            page = Math.floor(index / 10);
            hide();
        });
    }
});

return {
    Animation: Animation,
    readyAnimation: readyAnimation,
    start_animation: start_animation,
    stop_animation: stop_animation,
    registry: animationRegistry,
};

});

