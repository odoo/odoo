import {Interaction} from "@web/public/interaction";
import {registry} from "@web/core/registry";

export class DynamicCarouselSingleScroll extends Interaction {
	static selector = ".carousel.o_slide_single";
	dynamicContent = {
		_root: {
			"t-on-slide.bs.carousel": this.onSlideCarousel,
			"t-on-slid.bs.carousel": this.onSlidCarousel,
		},
	};

	setup() {
		this.carouselInnerEl = this.el.querySelector(".carousel-inner");
		this.isCycleEnable = this.el.dataset.bsWrap === "true";
		this.itemsPerSlide = parseInt(this.el.dataset.itemsPerSlide) || 4;
		// Preload 8 images in both directions.
		this.loadPrevItemsImages(8);
		this.loadNextItemsImages(8);
	}

	/**
	 * Allow the carousel to cycle otherwise it would reach an end
	 * This method is called when the carousel is sliding
	 *
	 *  @param {Event} ev
	 */
	onSlideCarousel(ev) {
		// We need to keep the active element at the beginning of the carousel-items elements
		// This allows to have a smooth transition when the carousel is sliding
		if (ev.direction === "right" && this.isCycleEnable) {
			const carouselItemsEls = Array.from(this.carouselInnerEl.querySelectorAll(".carousel-item"));
			// this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
			this.carouselInnerEl.prepend(carouselItemsEls.pop());
			// this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
		}
	}

	/**
	 * Prepare the carousel for the next sliding animation if needed
	 * This method is called after a sliding animation has finished
	 *
	 * @param {Event} ev
	 */
	onSlidCarousel(ev) {
		// As for the _onSlide method, we need to keep the active element at the beginning of the
		// carousel-items list in the DOM. So when animation is done,
		// we move the first item (which is not active anymore) to the end
		if (ev.direction === "left") {
			if (this.isCycleEnable) {
				const carouselItemsEls = Array.from(this.carouselInnerEl.querySelectorAll(".carousel-item"));
				// this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
				this.carouselInnerEl.appendChild(carouselItemsEls[0]);
				// this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
			}
			this.loadNextItemsImages();
		} else if (ev.direction === "right" && this.isCycleEnable) {
			this.loadPrevItemsImages();
		}
	}

	/**
	 * Load images of the carousel-item necessary for the 'prev' animation.
	 *
	 * @param {number} [nItemsToLoad=1]
	 */
	loadPrevItemsImages(nItemsToLoad = 1) {
		const startIndex = Math.max(0, this.carouselInnerEl.children.length - nItemsToLoad);
		const prevItemsToLoad = Array.from(this.carouselInnerEl.children).slice(startIndex, this.carouselInnerEl.children.length);
		this.loadItemImages(prevItemsToLoad.reverse());
	}

	/**
	 * Load images of the carousel-item necessary for the 'next' animation.
	 *
	 * @param {number} [nItemsToLoad=1]
	 */
	loadNextItemsImages(nItemsToLoad = 1) {
		const endIndex = Math.min((this.itemsPerSlide + nItemsToLoad + 1), this.carouselInnerEl.children.length);
		const nextItemsToLoad = Array.from(this.carouselInnerEl.children).slice(this.itemsPerSlide, endIndex);
		this.loadItemImages(nextItemsToLoad);
	}

	/**
	 * Load images of the carousel-item to enhance sliding animations.
	 *
	 * @param {Array<HTMLElement>} itemsToLoad
	 */
	loadItemImages(itemsToLoad) {
		// If the images in an item are not loaded yet due to `loading="lazy"`
		// and they come into the viewport, the animation may break.
		// To prevent this, we force images that are likely to come into the
		// viewport to be loaded eagerly.
		for (let carouselItemEl of itemsToLoad) {
			carouselItemEl.querySelectorAll('img[loading="lazy"]').forEach(img => {
				img.setAttribute('loading', 'eager');
			});
		}
	}
}

registry
	.category("public.interactions")
	.add("website.dynamic_carousel_single_scroll", DynamicCarouselSingleScroll);
