/** @odoo-module **/

import {
    Component,
    onMounted,
    onRendered,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

export class Carousel extends Component {
    static template = "odx_owl.Carousel";
    static props = {
        className: { type: String, optional: true },
        defaultIndex: { type: Number, optional: true },
        dir: { type: String, optional: true },
        index: { type: Number, optional: true },
        loop: { type: Boolean, optional: true },
        onIndexChange: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        setApi: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultIndex: 0,
        loop: false,
        orientation: "horizontal",
        tag: "div",
    };

    setup() {
        const self = this;
        this.viewportEl = null;
        this.items = [];
        this.state = useState({
            baseId: nextId("odx-carousel"),
            canScrollNext: false,
            canScrollPrev: false,
            index: Math.max(0, Number(this.props.index ?? this.props.defaultIndex) || 0),
        });

        useChildSubEnv({
            odxCarousel: {
                get currentIndex() {
                    return self.state.index;
                },
                get dir() {
                    return self.direction;
                },
                get itemCount() {
                    return self.items.length;
                },
                get orientation() {
                    return self.props.orientation;
                },
                canScrollNext: () => self.state.canScrollNext,
                canScrollPrev: () => self.state.canScrollPrev,
                getItemIndex: (itemId) => self.getItemIndex(itemId),
                registerItem: (itemApi) => self.registerItem(itemApi),
                registerViewport: (element) => self.registerViewport(element),
                scrollNext: () => self.scrollNext(),
                scrollPrev: () => self.scrollPrev(),
                scrollToIndex: (index, behavior) => self.scrollToIndex(index, behavior),
                unregisterItem: (itemId) => self.unregisterItem(itemId),
                unregisterViewport: () => self.unregisterViewport(),
                updateFromViewport: (emit = false) => self.updateFromViewport(emit),
            },
        });

        useExternalListener(window, "resize", () => this.updateFromViewport());

        onMounted(() => {
            this.props.setApi?.(this.getApi());
            browser.setTimeout(() => {
                this.scrollToIndex(this.state.index, "auto", false);
                this.updateFromViewport();
            }, 0);
        });

        onRendered(() => {
            if (this.props.index !== undefined && this.viewportEl) {
                this.scrollToIndex(this.props.index, "auto", false);
                return;
            }
            this.updateFromViewport();
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.index !== undefined) {
                this.state.index = Math.max(0, Number(nextProps.index) || 0);
            }
        });
    }

    get classes() {
        return cn(
            "odx-carousel",
            {
                "odx-carousel--horizontal": this.props.orientation !== "vertical",
                "odx-carousel--vertical": this.props.orientation === "vertical",
            },
            this.props.className
        );
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get isHorizontalRtl() {
        return this.props.orientation !== "vertical" && isRtlDirection(this.direction);
    }

    getApi() {
        return {
            canScrollNext: () => this.state.canScrollNext,
            canScrollPrev: () => this.state.canScrollPrev,
            scrollNext: () => this.scrollNext(),
            scrollPrev: () => this.scrollPrev(),
            scrollTo: (index, behavior) => this.scrollToIndex(index, behavior),
            selectedScrollSnap: () => this.state.index,
        };
    }

    getItemIndex(itemId) {
        return this.items.findIndex((item) => item.id === itemId);
    }

    getNearestItemIndex() {
        if (!this.viewportEl || !this.items.length) {
            return 0;
        }
        let nearestIndex = 0;
        let nearestDistance = Infinity;
        this.items.forEach((item, index) => {
            const distance = Math.abs(this.getViewportDeltaForItem(item.el));
            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearestIndex = index;
            }
        });
        return nearestIndex;
    }

    getViewportDeltaForItem(itemEl) {
        if (!this.viewportEl || !itemEl) {
            return 0;
        }
        const viewportRect = this.viewportEl.getBoundingClientRect();
        const itemRect = itemEl.getBoundingClientRect();
        if (this.props.orientation === "vertical") {
            return itemRect.top - viewportRect.top;
        }
        if (this.isHorizontalRtl) {
            return itemRect.right - viewportRect.right;
        }
        return itemRect.left - viewportRect.left;
    }

    notifyIndexChange(index) {
        if (index === this.state.index) {
            return;
        }
        this.state.index = index;
        this.props.onIndexChange?.(index);
    }

    registerItem(itemApi) {
        if (!itemApi?.id || !itemApi.el) {
            return;
        }
        if (!this.items.find((item) => item.id === itemApi.id)) {
            this.items.push(itemApi);
            this.items.sort((left, right) => {
                const position = left.el.compareDocumentPosition(right.el);
                return position & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
            });
        }
        this.updateFromViewport();
    }

    registerViewport(element) {
        this.viewportEl = element;
        this.updateFromViewport();
    }

    scrollNext() {
        this.scrollToIndex(this.state.index + 1);
    }

    scrollPrev() {
        this.scrollToIndex(this.state.index - 1);
    }

    scrollToIndex(index, behavior = "smooth", emit = true) {
        if (!this.items.length || !this.viewportEl) {
            return;
        }
        let nextIndex = Number(index) || 0;
        if (this.props.loop && this.items.length > 1) {
            nextIndex = (nextIndex + this.items.length) % this.items.length;
        } else {
            nextIndex = clamp(nextIndex, 0, this.items.length - 1);
        }
        const item = this.items[nextIndex];
        if (!item?.el) {
            return;
        }
        const delta = this.getViewportDeltaForItem(item.el);
        this.viewportEl.scrollBy({
            top: this.props.orientation === "vertical" ? delta : 0,
            left: this.props.orientation === "vertical" ? 0 : delta,
            behavior,
        });
        this.state.canScrollPrev = this.props.loop ? this.items.length > 1 : nextIndex > 0;
        this.state.canScrollNext = this.props.loop
            ? this.items.length > 1
            : nextIndex < this.items.length - 1;
        if (emit) {
            this.notifyIndexChange(nextIndex);
            return;
        }
        this.state.index = nextIndex;
    }

    unregisterItem(itemId) {
        this.items = this.items.filter((item) => item.id !== itemId);
        if (this.state.index >= this.items.length) {
            this.state.index = Math.max(0, this.items.length - 1);
        }
        this.updateFromViewport();
    }

    unregisterViewport() {
        this.viewportEl = null;
    }

    updateFromViewport(emit = false) {
        if (!this.items.length) {
            this.state.canScrollPrev = false;
            this.state.canScrollNext = false;
            this.state.index = 0;
            return;
        }
        const nextIndex = this.viewportEl ? this.getNearestItemIndex() : clamp(this.state.index, 0, this.items.length - 1);
        this.state.canScrollPrev = this.props.loop ? this.items.length > 1 : nextIndex > 0;
        this.state.canScrollNext = this.props.loop
            ? this.items.length > 1
            : nextIndex < this.items.length - 1;
        if (emit) {
            this.notifyIndexChange(nextIndex);
            return;
        }
        this.state.index = nextIndex;
    }
}

export class CarouselContent extends Component {
    static template = "odx_owl.CarouselContent";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        trackClassName: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Carousel slides",
        className: "",
        trackClassName: "",
    };

    setup() {
        this.viewportRef = useRef("viewportRef");
        useEffect(
            () => {
                this.env.odxCarousel.registerViewport(this.viewportRef.el);
                return () => this.env.odxCarousel.unregisterViewport();
            },
            () => []
        );
    }

    get classes() {
        return cn(
            "odx-carousel__content",
            {
                "odx-carousel__content--vertical": this.env.odxCarousel.orientation === "vertical",
                "odx-carousel__content--horizontal": this.env.odxCarousel.orientation !== "vertical",
            },
            this.props.className
        );
    }

    get trackClasses() {
        return cn(
            "odx-carousel__track",
            {
                "odx-carousel__track--vertical": this.env.odxCarousel.orientation === "vertical",
                "odx-carousel__track--horizontal": this.env.odxCarousel.orientation !== "vertical",
            },
            this.props.trackClassName
        );
    }

    onKeydown(ev) {
        const orientation = this.env.odxCarousel.orientation;
        const isRtl = orientation !== "vertical" && isRtlDirection(this.env.odxCarousel.dir);
        const previousKeys = orientation === "vertical"
            ? ["ArrowUp"]
            : [isRtl ? "ArrowRight" : "ArrowLeft"];
        const nextKeys = orientation === "vertical"
            ? ["ArrowDown"]
            : [isRtl ? "ArrowLeft" : "ArrowRight"];
        if (!previousKeys.includes(ev.key) && !nextKeys.includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        if (previousKeys.includes(ev.key)) {
            this.env.odxCarousel.scrollPrev();
            return;
        }
        this.env.odxCarousel.scrollNext();
    }

    onScroll() {
        this.env.odxCarousel.updateFromViewport(true);
    }
}

export class CarouselItem extends Component {
    static template = "odx_owl.CarouselItem";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    setup() {
        this.itemRef = useRef("itemRef");
        this.state = useState({
            id: nextId("odx-carousel-item"),
        });
        useEffect(
            () => {
                this.env.odxCarousel.registerItem({
                    id: this.state.id,
                    el: this.itemRef.el,
                });
                return () => this.env.odxCarousel.unregisterItem(this.state.id);
            },
            () => []
        );
    }

    get accessibleLabel() {
        if (this.props.ariaLabel) {
            return this.props.ariaLabel;
        }
        const index = this.env.odxCarousel.getItemIndex(this.state.id);
        const total = this.env.odxCarousel.itemCount;
        return `Slide ${index + 1} of ${total}`;
    }

    get classes() {
        return cn(
            "odx-carousel__item",
            {
                "odx-carousel__item--vertical": this.env.odxCarousel.orientation === "vertical",
                "odx-carousel__item--horizontal": this.env.odxCarousel.orientation !== "vertical",
            },
            this.props.className
        );
    }
}

class CarouselButton extends Component {
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "",
        className: "",
        disabled: false,
        title: "",
    };

    get isDisabled() {
        return this.props.disabled || !this.isAvailable;
    }

    get isHorizontalRtl() {
        return this.env.odxCarousel.orientation !== "vertical" && isRtlDirection(this.env.odxCarousel.dir);
    }
}

export class CarouselPrevious extends CarouselButton {
    static template = "odx_owl.CarouselPrevious";

    get classes() {
        return cn("odx-carousel__previous", this.props.className);
    }

    get isAvailable() {
        return this.env.odxCarousel.canScrollPrev();
    }

    get iconPath() {
        return this.isHorizontalRtl ? "M6.25 3.5L10.75 8L6.25 12.5" : "M9.75 3.5L5.25 8L9.75 12.5";
    }

    onClick(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxCarousel.scrollPrev();
    }
}

export class CarouselNext extends CarouselButton {
    static template = "odx_owl.CarouselNext";

    get classes() {
        return cn("odx-carousel__next", this.props.className);
    }

    get isAvailable() {
        return this.env.odxCarousel.canScrollNext();
    }

    get iconPath() {
        return this.isHorizontalRtl ? "M9.75 3.5L5.25 8L9.75 12.5" : "M6.25 3.5L10.75 8L6.25 12.5";
    }

    onClick(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxCarousel.scrollNext();
    }
}
