import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ProductTileVideo extends Interaction {
    static selector = ".oe_product_tile_video_wrapper";
    dynamicContent = {
        _root: {
            "t-on-mouseenter": () => this.play(),
            "t-on-mouseleave": () => this.stop(),
        },
    };

    play() {
        const iframeEl = this.el.querySelector("iframe");
        if (!iframeEl.getAttribute("src")) {
            iframeEl.setAttribute("src", this.el.dataset.videoSrc);
        }
    }

    stop() {
        this.el.querySelector("iframe").removeAttribute("src");
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_tile_video", ProductTileVideo);
