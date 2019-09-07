(function ($) {

    $(function () {

        // --  Initialize fallbacks for requestAnimationFrame
        window.requestAnimationFrame = window.requestAnimationFrame
        || window.webkitRequestAnimationFrame
        || window.mozRequestAnimationFrame
        || window.msRequestAnimationFrame
        || window.oRequestAnimationFrame
        || function (callback) { setTimeout(callback, 10); };


        // =======  Define variables =======
        // =================================
        // --  Screen resolutions
        var screen_md = 992;

        // --  Window, window's properties
        var $win  = $(window),
            win_w = $win.width();

        // --  Main elements
        var $body    = $('body'),
            $header  = $body.find('> header'),
            $sub_nav = $header.find(".o_sub_nav"),
            $wrap    = $body.find('> #wrap'),
            $main    = $wrap.find('main'),
            $footer  = $body.find('> footer');

        // --  Detect page type
        var page_type = (function () {
            if ($wrap.hasClass('index')) {
                return 'index';
            } else if ($main.find('article').hasClass('doc-tocindex-category')){
                return 'category-index';
            } else {
                return 'article';
            }
        })();

        // --  CP > "Card Top"
        var $cp       = $wrap.find('> .card.top'),
            $cp_image = $cp.find('> .card-img'),
            $cp_text  = $cp.find('> .container'),

            cp_h           = $cp.outerHeight(),
            has_cp_image   = $cp_image.length > 0,
            cp_image_alpha = has_cp_image ? $cp_image.css('opacity') : undefined,
            cp_end_point   = has_cp_image ? cp_h/2 : undefined;

        // --  Floating action
        var $mask       = $body.find('#mask'),
            $float      = $body.find("#floating_action"),
            $float_menu = $body.find("#floating_action_menu");

        // -- Elements' heights
        var body_h     = $body.height(),
            header_h   = $header.outerHeight(),
            main_h     = $main.height(),
            sub_nav_h  = $sub_nav.height();

        // --  Aside
        var $aside       = $main.find('aside'),
            has_aside    = $aside.length > 0,
            $aside_nav   = has_aside ? $aside.find('> .navbar-aside') : undefined,
            aside_links  = has_aside ? $aside_nav.find("li > a") : undefined;



        // ======= Affix =================
        // ===============================
        function set_affix() {
            var aside_offset_top = $aside.offset().top - sub_nav_h,
                aside_offset_bot = parseInt($wrap.css('padding-bottom')),
                aside_width      = $aside.width();

            $aside.css('height', main_h);
            $aside_nav.css('width', aside_width).affix({
                offset: {
                    top    : aside_offset_top,
                    bottom : aside_offset_bot,
                }
            });
        }

        // ======= Footer animations =====
        // ===============================
        var footer_animation = function () {
            var footer_effect = $main.outerHeight() >= $win.outerHeight();

            if (!footer_effect) {
                footer_stop();
                return;
            }

            $footer.toggleClass('o_footer_effect', footer_effect);
            $body.css('padding-bottom', $footer.outerHeight());

            var checkIfSearch = function (e) {
                if ((e.ctrlKey || e.metaKey) && String.fromCharCode(e.which).toLowerCase() === 'f') {
                    footer_stop();
                }
            };
            $win.on('keydown.footer', function (e) {
                checkIfSearch(e);
            });
        };

        var footer_stop = function () {
            $footer.removeClass('o_footer_effect');
            $body.css('padding-bottom', 0);
            $win.off('keydown.footer');
        };


        // ======= Docs Functions ==========
        // =================================
        // -- Layouting
        var init = function () {
            var $floating_container = $body.find("> .floating_action_container");

            // Adapt Title font size according to its length
            $cp_text
                .toggleClass('o_short_title', $cp_text.text().trim().length < 15)
                .toggleClass('o_long_title',  $cp_text.text().trim().length > 45);

            if (page_type == 'index') {
                var half_cols_selector = '.tutorials,.api';

                $main.find("#index .index-tree").find(half_cols_selector)
                    .wrap('<div class="o_half_col col-sm-6"/>')
                    .find('.col-md-3').removeClass('col-md-3 col-sm-6').addClass('col-sm-12 col-md-6');

                var half_cols_els = $main.find(".o_half_col");
                for(var i = 0; i < half_cols_els.length; i+=2) {
                    half_cols_els.slice(i, i+2).wrapAll("<div class='row'></div>");
                }
            }

            if (page_type == 'index' || page_type == 'category-index') {
                $floating_container.add($mask).remove();
                $main.toggleClass('o_slim_page', page_type == 'category-index');
            }

            if (page_type == 'article') {
                attach_permalink_markers();

                // Hide empty-permalink first sections
                var $f_s = $main.find('article.doc-body > section:first-child');
                $f_s.toggleClass('hidden', $f_s[0].childElementCount == 1 && $f_s.children().is('i:empty'));

                if (has_aside) {
                    if (aside_links.length < 2) {
                        has_aside = false;
                        $main.addClass("o_aside_removed");
                        $floating_container.add($mask).add($aside).remove();
                        return;
                    }

                    floating_menu_layout();
                    set_scroll_to(aside_links);
                    ripple_animation(aside_links);
                    $aside_nav.find("li").has("ul").addClass("parent");
                }
            }

            bind_window_events();
        };

        // -- Float action menu
        var floating_menu_layout = function () {
            var lis = $aside_nav.find("> ul > li").clone(true)
                .addClass("ripple")
                .css({
                    position: 'relative',
                    overflow: 'hidden'
                });
            lis.find("ul").remove().end()
                .find("a").removeClass("ripple").on("click", function () {
                    _toggle_float();
                });
            $float_menu.find(".content").empty().append(lis);
            $float.add($mask).on("click", function  () {
                _toggle_float();
                return false;
            });
        };

        // -- Scroll To
        var set_scroll_to = function (el_list) {
            el_list.each(function () {
                var $link     = $(this),
                    target_id = $link.attr("href");

                $link.on("click", function () {
                    $aside_nav.find("li").removeClass("active");
                    $link.parents("li").addClass("active");
                    _scroll_and_set_hash(target_id);
                    return false;
                });
            });

            $body.scrollspy({
                target: 'aside',
                offset: 200,
            });
        };

        // -- Ripple buttons
        var ripple_animation = function (el_list) {
            el_list.each(function () {
                var btn = $(this);
                btn
                    .css({
                        position: 'relative',
                        overflow: 'hidden'
                    })
                    .bind('mousedown', function (e) {
                        var ripple;
                        if (btn.find('.inner-ripple').length === 0) {
                            ripple = $('<span class="inner-ripple"/>');
                            btn.prepend(ripple);
                        } else {
                            ripple = btn.find('.inner-ripple');
                        }
                        ripple.removeClass('inner-ripple-animated');

                        if (!ripple.height() && !ripple.width()) {
                            var diameter = Math.max(btn.outerWidth(), btn.outerHeight());
                            ripple.css({
                                height: diameter,
                                width: diameter
                            });
                        }
                        var x = e.pageX - btn.offset().left - ripple.width() / 2;
                        var y = e.pageY - btn.offset().top - ripple.height() / 2;
                        ripple.css({
                            top: y + 'px',
                            left: x + 'px'
                        }).addClass('inner-ripple-animated');
                        setTimeout(function () {
                            ripple.removeClass('inner-ripple-animated');
                        }, 351);
                    });
            });
        };

        // -- Header buttons
        var header_buttons = function () {
            var timer;
            $header.on('click', '.o_primary_nav .dropdown-toggle', function (e) {
                e.preventDefault();

                var $a = $(this);
                clearTimeout(timer);

                $a.parent().toggleClass('open');
                $a.closest('ul').toggleClass('o_sub_opened', $a.parent().hasClass('open'));
                if ($a.closest('.o_primary_nav').children('.open').length > 0) {
                    $header.addClass("o_sub_opened");
                } else {
                    timer = setTimeout(function () {
                        $header.removeClass("o_sub_opened");
                    }, 200);
                }
            });
            $header.on('click', '.o_primary_nav .o_secondary_nav', function (e) {
                if (e.target === e.currentTarget) {
                    $header.find('.open').removeClass('open');
                    $header.find('.o_sub_opened').andSelf().removeClass('o_sub_opened');
                }
            });

            // -- Mobile menu opening
            $header.on('click', '.o_mobile_menu_toggle', function (e) {
                e.preventDefault();
                $(this).find('i').toggleClass('fa-bars fa-times');
                $header.toggleClass('o_mobile_menu_opened');
            });
        };

        // -- Attach permalink markers to sections' title
        var attach_permalink_markers = function () {
            $main.find('article.doc-body > section').each( function () {
                var $section  = $(this),
                    $title    = $section.find('> h2, > h3, > h4, > h5, > h6'),
                    target_id = $section.attr('id'),
                    $icon     = $('<i/>').addClass('mdi-content-link');

                if ($title.length <= 0) {
                    return;
                }

                $title.addClass('o_has_permalink_marker').append($icon);

                $icon.on('click', function () {
                    _scroll_and_set_hash("#" + target_id);

                    $title.addClass('o_marked').delay(1000).queue(function (){
                        $title.removeClass('o_marked').dequeue();
                    });
                    return false;
                });
            });
        };

        var cp_animation = function (win_top, cp_end_point){
            var top = Math.min(win_top, cp_h);

            $cp_image.css({
                'opacity'   : cp_image_alpha - (top * (cp_image_alpha/cp_end_point)),
                'transform' : 'scale(' + (1 + (top * (0.1/cp_end_point))) +')'
            });

            $cp_text.css({
                'transform' : 'translateY(' + (top/4)  + 'px)',
                'opacity'   : 1 - (top/cp_h)
            });
        };

        $(".content-switcher").each(function (index, switcher) {
            var $switcher = $(switcher),
                $links    = $switcher.find('> ul > li'),
                $tabs     = $switcher.find('> .tabs > *'),
                $all      = $links.add($tabs);

            function select(index) {
                $all.removeClass('active');
                $links.eq(index).add($tabs.eq(index)).addClass('active');
            }
            select(0);
            $switcher.on('click', '> ul > li', function () {
                select($(this).index());
                return false;
            });
        });


        // ======= Utils ==================
        // =================================
        var _scroll_and_set_hash = function (target_id) {
            $('html, body').animate({
                scrollTop: $(target_id).offset().top - 60
            }, 100);
            window.location.hash = target_id;
        };

        var _toggle_float = function () {
            $float.toggleClass("active");
            setTimeout(function () {
                $float_menu.toggleClass("active");
                $mask.toggleClass("active");
            }, 300);
        };


        var bind_window_events = function () {
            // ======= On resize ==============
            // Update properties and conditionally call functions according to resolution
            $win.on('resize', function () {
                // Update size variables
                win_w        = $win.width();
                body_h       = $body.height();
                cp_h         = $cp.outerHeight();
                main_h       = $main.height();
                cp_end_point = has_cp_image ? cp_h/2 : undefined;

                if (win_w >= screen_md){
                    footer_animation();
                    (has_aside)? set_affix(): '';
                } else {
                    footer_stop();
                }
            });

            // ======= On scroll ==============
            $win.on('scroll', function () {
                var win_top  = $win.scrollTop();

                $win[0].requestAnimationFrame(function () {
                    cp_animation(win_top, cp_end_point);
                });

                if (win_w >= screen_md) {
                    $header.toggleClass('o_scrolled', win_top > header_h);
                }
            });
        };


        // ======= Onload ==================
        // =================================
        // -- Call default functions
        init();
        header_buttons();
        ripple_animation($(".ripple"));

        // -- Conditionally call specific functions according to resolution
        if (win_w >= screen_md){
            footer_animation();
            (has_aside)? set_affix(): '';
        }
    });
})(jQuery);
