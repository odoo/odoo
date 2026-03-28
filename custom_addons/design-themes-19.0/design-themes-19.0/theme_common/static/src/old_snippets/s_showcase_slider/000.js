/** @odoo-module **/

import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.s_showcase_slider = publicWidget.Widget.extend({
    selector: ".s_showcase_slider",

    start: function () {
        setTimeout(this.bindEvents.bind(this), 0); // FIXME delayed to counter a web_editor bug which off all click event
        this.createPagination();
        return this._super.apply(this, arguments);
    },

    destroy: function () {
        this._super.apply(this, arguments);
        setTimeout(this.unbindEvents.bind(this), 0); // FIXME delayed to counter a web_editor bug which off all click event
        this.destroyPagination();
        this.$el.removeClass("active");
    },

    bindEvents: function () {
        // Enlarge image on click if not already enlarged
        this.$el.on("click.s_showcase_slider", ".s_ss_slider", (function (e) {
            if (this.$el.hasClass("active")) return;

            this.$el
                .addClass("active")
                .one("webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend", (function () {
                    dom.scrollTo(this.el, {
                        duration: 200,
                        extraOffset: 70,
                    });
                    this.$el.trigger("transitionIsFinished");
                }).bind(this));
        }).bind(this));

        // Close the enlarged image on close icon click
        this.$el.on("click.s_showcase_slider", ".s_ss_close", (function (e) {
            this.$el.removeClass("active");
        }).bind(this));

        // Handle click navigation
        this.$el.on("click.s_showcase_slider", ".s_ss_prev", this.prevSlide.bind(this));
        this.$el.on("click.s_showcase_slider", ".s_ss_next", this.nextSlide.bind(this));
        this.$el.on("click.s_showcase_slider", ".s_ss_slider_pagination > li > a", (function (e) {
            e.preventDefault();
            var $selectedDot = $(e.currentTarget).parent();
            if ($selectedDot.hasClass("selected")) return;
            this.changeSlide($selectedDot.index());
        }).bind(this));

        // Keyboard slider navigation
        $(document).on("keyup.s_showcase_slider", (function (e) {
            if (!this.$el.hasClass("active")) return;

            switch (e.which) {
                case $.ui.keyCode.LEFT:
                    this.prevSlide();
                    break;
                case $.ui.keyCode.RIGHT:
                    this.nextSlide();
                    break;
                case $.ui.keyCode.ESCAPE:
                    this.$el.removeClass("active");
                    break;
            }
        }).bind(this));
    },

    unbindEvents: function () {
        this.$el.off(".s_showcase_slider");
        $(document).off(".s_showcase_slider");
    },

    createPagination: function () { // FIXME pagination should be saved with editor but keep this for compatibility
        this.$el.find(".s_ss_slider_pagination").remove(); // Remove saved-with-editor pagination

        this.$pagination = $("<ul/>", {class: "s_ss_slider_pagination"});
        this.$pagination.insertAfter(this.$el.find(".s_ss_slider_navigation"));

        var nbSlides = this.$el.find(".s_ss_slider").children().length;
        for (var i = 0 ; i < nbSlides ; i++) {
            this.$pagination.append("<li><a href=\"#\"></a></li>");
        }

        this.$pagination.children().eq(this.getCurrentIndex()).addClass("selected");
    },

    destroyPagination: function () {
        if (this.$pagination) {
            this.$pagination.remove();
            this.$pagination = null;
        }
    },

    prevSlide: function () {
        var nbSlides = this.$el.find(".s_ss_slider").children().length;
        var currentIndex = this.getCurrentIndex();
        this.changeSlide(currentIndex > 0 ? (currentIndex - 1) : (nbSlides - 1));
    },

    nextSlide: function () {
        var nbSlides = this.$el.find(".s_ss_slider").children().length;
        var currentIndex = this.getCurrentIndex();
        this.changeSlide((currentIndex + 1) % nbSlides);
    },

    getCurrentIndex: function () {
        return this.$el.find(".s_ss_slider > .selected").index();
    },

    changeSlide: function (n) {
        var $slides = this.$el.find(".s_ss_slider > li").removeClass("selected");
        this.$el.find(".s_ss_slider_pagination > li").removeClass("selected");

        var $slide = $slides.eq(n).addClass("selected");
        $slides.removeClass("move-left");
        $slide.prevAll().addClass("move-left");

        this.$pagination.children().eq(n).addClass("selected");
        this.updateNavigation();
    },

    updateNavigation: function () {
        var $active = this.$el.find(".s_ss_slider > .selected");
        this.$el.find(".s_ss_prev").toggleClass("inactive", $active.is(":first-child"));
        this.$el.find(".s_ss_next").toggleClass("inactive", $active.is(":last-child"));
    },
});
