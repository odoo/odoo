import { uniqueId } from "@web/core/utils/functions";
import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import * as masonryUtils from "@web_editor/js/common/masonry_layout_utils";
import wUtils from "@website/js/utils";

const GalleryWidget = publicWidget.Widget.extend({

    selector: '.s_image_gallery:not(.o_slideshow)',
    events: {
        'click img': '_onClickImg',
        "click #btn-expand-gallery": "_expandGallery",
        "click #btn-collapse-gallery": "_collapseGallery",
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this.originalSources = [...this.el.querySelectorAll("img")].map(img => img.getAttribute("src"));

        if (this.el.classList.contains("o_masonry")) {
            masonryUtils.observeMasonryLayoutWidthChange(this.el);
        }
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        if (this.el.dataset.expandable === "true") {
            this._collapseGallery({ scrollGalleryIntoView: false });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when an image is clicked. Opens a dialog to browse all the images
     * with a bigger size.
     *
     * @private
     * @param {Event} ev
     */
    _onClickImg: function (ev) {
        const clickedEl = ev.currentTarget;
        if (this.$modal || clickedEl.matches("a > img")) {
            return;
        }
        var self = this;

        let imageEls = this.el.querySelectorAll("img");
        const currentImageEl = clickedEl.closest("img");
        const currentImageIndex = [...imageEls].indexOf(currentImageEl);
        // We need to reset the images to their original source because it might
        // have been changed by a mouse event (e.g. "hover effect" animation).
        imageEls = [...imageEls].map((el, i) => {
            const cloneEl = el.cloneNode(true);
            cloneEl.src = this.originalSources[i];
            return cloneEl;
        });

        var size = 0.8;
        var dimensions = {
            min_width: Math.round(window.innerWidth * size * 0.9),
            min_height: Math.round(window.innerHeight * size),
            max_width: Math.round(window.innerWidth * size * 0.9),
            max_height: Math.round(window.innerHeight * size),
            width: Math.round(window.innerWidth * size * 0.9),
            height: Math.round(window.innerHeight * size)
        };

        const milliseconds = this.el.dataset.interval || false;
        const lightboxTemplate = this.$target[0].dataset.vcss === "002" ?
            "website.gallery.s_image_gallery_mirror.lightbox" :
            "website.gallery.slideshow.lightbox";
        this.$modal = $(renderToElement(lightboxTemplate, {
            images: imageEls,
            index: currentImageIndex,
            dim: dimensions,
            interval: milliseconds || 0,
            ride: !milliseconds ? "false" : "carousel",
            id: uniqueId("slideshow_"),
        }));
        this.__onModalKeydown = this._onModalKeydown.bind(this);
        this.$modal.on('hidden.bs.modal', function () {
            $(this).hide();
            $(this).siblings().filter('.modal-backdrop').remove(); // bootstrap leaves a modal-backdrop
            this.removeEventListener("keydown", self.__onModalKeydown);
            $(this).remove();
            self.$modal = undefined;
        });
        this.$modal.one('shown.bs.modal', function () {
            self.trigger_up('widgets_start_request', {
                editableMode: false,
                $target: self.$modal.find('.modal-body.o_slideshow'),
            });
            this.addEventListener("keydown", self.__onModalKeydown);
        });
        this.$modal.appendTo(document.body);
        const modalBS = new Modal(this.$modal[0], {keyboard: true, backdrop: true});
        modalBS.show();
    },
    _onModalKeydown(ev) {
        if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
            const side = ev.key === "ArrowLeft" ? "prev" : "next";
            this.$modal[0].querySelector(`.carousel-control-${side}`).click();
        }
        if (ev.key === "Escape") {
            // If the user is connected as an editor, prevent the backend header
            // from collapsing.
            ev.stopPropagation();
        }
    },
    /**
     * Shows gallery items that are hidden by expandable option.
     *
     * @private
     */
    _expandGallery() {
        const showMoreButtonEl = this.el.querySelector("#btn-expand-gallery");
        const hideExtraButtonEl = this.el.querySelector("#btn-collapse-gallery");

        if (!showMoreButtonEl || !hideExtraButtonEl) {
            return;
        }

        // Toggle expandable control buttons visibility
        showMoreButtonEl.classList.add("d-none");
        hideExtraButtonEl.classList.remove("d-none");

        const maxAllowedItemCount =
            parseInt(this.el.dataset.expandableCount, 10) || galleryItemEls.length;
        const galleryItemEls = wUtils.getSortedGalleryItems(this.el, [".o_grid_item"]);
        galleryItemEls
            .slice(maxAllowedItemCount) // Selects the gallery items beyond allowed limit
            .forEach((galleryItemEl) =>
                // Show all the hidden gallery items
                galleryItemEl.classList.remove("d-none")
            );
    },
    /**
     * Hides gallery items that should be hidden by expandable options
     *
     * @private
     * @param {{ scrollGalleryIntoView?: boolean }} options - Options for
     *                                            controlling collapse behavior.
     * @param {boolean} [options.scrollGalleryIntoView=true] - Determines if the
     *                                          gallery should scroll into view.
     */
    _collapseGallery({ scrollGalleryIntoView = true } = {}) {
        const showMoreButtonEl = this.el.querySelector("#btn-expand-gallery");
        const hideExtraButtonEl = this.el.querySelector("#btn-collapse-gallery");

        if (!showMoreButtonEl || !hideExtraButtonEl) {
            return;
        }

        const maxAllowedItemCount =
            parseInt(this.el.dataset.expandableCount, 10) || galleryItemEls.length;
        const galleryItemEls = wUtils.getSortedGalleryItems(this.el, [".o_grid_item"]);
        galleryItemEls
            .slice(maxAllowedItemCount) // Selects the gallery items beyond allowed limit
            .forEach((galleryItemEl) =>
                // Hide items that are beyond allowed limit
                galleryItemEl.classList.add("d-none")
            );

        // Toggle expandable control buttons visibility
        if (galleryItemEls.length > maxAllowedItemCount) {
            hideExtraButtonEl.classList.add("d-none");
            showMoreButtonEl.classList.remove("d-none");
        }

        // Bring the gallery into view if needed
        if (scrollGalleryIntoView) {
            showMoreButtonEl.scrollIntoView({
                behavior: "smooth",
                block: "end",
            });
        }
    },
});

const GallerySliderWidget = publicWidget.Widget.extend({
    selector: '.o_slideshow',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$carousel = this.$el.is('.carousel') ? this.$el : this.$('.carousel');
        this.$indicator = this.$carousel.find('.carousel-indicators');
        this.$prev = this.$indicator.find('li.o_indicators_left').css('visibility', ''); // force visibility as some databases have it hidden
        this.$next = this.$indicator.find('li.o_indicators_right').css('visibility', '');
        var $lis = this.$indicator.find('li[data-bs-slide-to]');
        let indicatorWidth = this.$indicator.width();
        if (indicatorWidth === 0) {
            // An ancestor may be hidden so we try to find it and make it
            // visible just to take the correct width.
            const $indicatorParent = this.$indicator.parents().not(':visible').last();
            if (!$indicatorParent[0].style.display) {
                $indicatorParent[0].style.display = 'block';
                indicatorWidth = this.$indicator.width();
                $indicatorParent[0].style.display = '';
            }
        }
        let nbPerPage = Math.floor(indicatorWidth / $lis.first().outerWidth(true)) - 3; // - navigator - 1 to leave some space
        var realNbPerPage = nbPerPage || 1;
        var nbPages = Math.ceil($lis.length / realNbPerPage);

        var index;
        var page;
        update();

        function hide() {
            $lis.each(function (i) {
                $(this).toggleClass('d-none', i < page * nbPerPage || i >= (page + 1) * nbPerPage);
            });
            if (page <= 0) {
                self.$prev.detach();
            } else {
                self.$prev.removeClass('d-none');
                self.$prev.prependTo(self.$indicator);
            }
            if (page >= nbPages - 1) {
                self.$next.detach();
            } else {
                self.$next.removeClass('d-none');
                self.$next.appendTo(self.$indicator);
            }
        }

        function update() {
            const active = $lis.filter('.active');
            index = active.length ? $lis.index(active) : 0;
            page = Math.floor(index / realNbPerPage);
            hide();
        }

        this.$carousel.on('slide.bs.carousel.gallery_slider', function () {
            setTimeout(function () {
                var $item = self.$carousel.find('.carousel-inner .carousel-item-prev, .carousel-inner .carousel-item-next');
                var index = $item.index();
                $lis.removeClass('active')
                    .filter('[data-bs-slide-to="' + index + '"]')
                    .addClass('active');
            }, 0);
        });
        this.$indicator.on('click.gallery_slider', '> li:not([data-bs-slide-to])', function () {
            page += ($(this).hasClass('o_indicators_left') ? -1 : 1);
            page = Math.max(0, Math.min(nbPages - 1, page)); // should not be necessary
            self.$carousel.carousel(page * realNbPerPage);
            // We dont use hide() before the slide animation in the editor because there is a traceback
            // TO DO: fix this traceback
            if (!self.editableMode) {
                hide();
            }
        });
        this.$carousel.on('slid.bs.carousel.gallery_slider', update);

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        if (!this.$indicator) {
            return;
        }

        this.$prev.prependTo(this.$indicator);
        this.$next.appendTo(this.$indicator);
        this.$carousel.off('.gallery_slider');
        this.$indicator.off('.gallery_slider');
    },
});

publicWidget.registry.gallery = GalleryWidget;
publicWidget.registry.gallerySlider = GallerySliderWidget;

export default {
    GalleryWidget: GalleryWidget,
    GallerySliderWidget: GallerySliderWidget,
};
