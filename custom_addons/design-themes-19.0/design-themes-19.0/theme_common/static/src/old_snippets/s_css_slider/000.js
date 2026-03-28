/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.s_css_slider = publicWidget.Widget.extend({
    selector: ".s_css_slider",
    disabledInEditableMode: false,

    start: function () {
        var self = this;
        var $container = self.$el;
        $container.find(".s_css_slider_pagination").remove();
        // create slider pagination
        var sliderPagination = self.createSliderPagination($container);
        self.bindEvents($container, sliderPagination);
        $(window).on("resize", function () {
            self.resizeImgs($container);
        }).trigger("resize");
        return this._super.apply(this, arguments);
    },

    bindEvents: function ($container, sliderPagination) {
        var self      = this,
            $next_btn = $container.find('.next'),
            $prev_btn = $container.find('.prev');

        $next_btn.on('click.s_css', function (e) {
            self.nextSlide($container, sliderPagination);
        });

        $prev_btn.on('click.s_css', function (e) {
            self.prevSlide($container, sliderPagination);
        });

        if ($container.hasClass("autoplay") && this.editableMode !== true) {
            var interval;
            var autoplay = function () {
                interval = setInterval(function () {
                    if (!$next_btn.hasClass("inactive")) {
                        self.nextSlide($container, sliderPagination);
                    } else {
                        self.prevSlide($container, sliderPagination, 0);
                    }
                }, 3000);
            };
            autoplay();
            $container.hover(function () { clearInterval(interval); });
            $container.mouseleave(function () { autoplay(); });
        }

        sliderPagination.on('click.s_css', function () {
            var selectedDot = $(this);
            if (!selectedDot.hasClass('selected')) {
                var selectedPosition = selectedDot.index(),
                        activePosition = $container.find('.slider .selected').index();
                if ( activePosition < selectedPosition) {
                    self.nextSlide($container, sliderPagination, selectedPosition);
                } else {
                    self.prevSlide($container, sliderPagination, selectedPosition);
                }
            }
        });
    },

    resizeImgs: function ($container) {
        var cont_h = $container.height(),
            imgs   = $container.find(".slide img");

        imgs.each(function () {
            var $img  = $(this),
                img_h = $img.height();
            if (img_h > cont_h) {
                $img.css("width", "100%");
                $img.css("margin-top", (cont_h - img_h)/2);
            }
        });
    },

    createSliderPagination: function ($container) {
        var wrapper = $('<ul class="s_css_slider_pagination"></ul>').insertAfter($container.find('.navigation'));
        $container.find('.slider .slide').each(function (index) {
            var dotWrapper = (index === 0) ? $('<li class="selected"></li>') : $('<li></li>'),
                dot = $('<a href="#0"></a>').appendTo(dotWrapper);
            dotWrapper.appendTo(wrapper);
            dot.text(index+1);
        });
        return wrapper.children('li');
    },

    nextSlide: function ($container, $pagination, $n) {
        var self = this,
            visibleSlide = $container.find('.slider .selected'),
            navigationDot = $container.find('.s_css_slider_pagination .selected');

        if (typeof $n === 'undefined') $n = visibleSlide.index() + 1;
        visibleSlide.removeClass('selected');
        $container.find('.slider .slide').eq($n).addClass('selected').prevAll().addClass('move-left');
        navigationDot.removeClass('selected');
        $pagination.eq($n).addClass('selected');
        self.updateNavigation($container, $container.find('.slider .slide').eq($n));
    },

    prevSlide: function ($container, $pagination, $n) {
        var self = this,
            visibleSlide  = $container.find('.slider .selected'),
            navigationDot = $container.find('.s_css_slider_pagination .selected');

        if (typeof $n === 'undefined') $n = visibleSlide.index() - 1;
        visibleSlide.removeClass('selected');
        $container.find('.slider .slide').eq($n).addClass('selected').removeClass('move-left').nextAll().removeClass('move-left');
        navigationDot.removeClass('selected');
        $pagination.eq($n).addClass('selected');
        self.updateNavigation($container, $container.find('.slider .slide').eq($n));
    },

    updateNavigation: function ($container, $active) {
        $container.find('.prev').toggleClass('inactive', $active.is(':first-child'));
        $container.find('.next').toggleClass('inactive', $active.is(':last-child'));
    },
});
