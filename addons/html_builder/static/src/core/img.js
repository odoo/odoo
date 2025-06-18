import { Component, onWillStart, onWillUpdateProps, useEffect, useRef, xml } from "@odoo/owl";
import { Cache } from "@web/core/utils/cache";

const svgCache = new Cache(async (src) => {
    let text;
    try {
        const response = await window.fetch(src);
        text = await response.text();
    } catch {
        // In some tours, the tour finishes before the fetch is done
        // and when a tour is finished, the python side will ask the
        // browser to stop loading resources. This causes the fetch
        // to fail and throw an error which crashes the test even
        // though it completed successfully.
        // So return an empty SVG to ensure everything completes
        // correctly.
        text = "<svg></svg>";
    }
    const parser = new window.DOMParser();
    const xmlDoc = parser.parseFromString(text, "text/xml");
    return xmlDoc.getElementsByTagName("svg")[0];
}, JSON.stringify);

export class Img extends Component {
    static props = {
        src: String,
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        alt: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        svgCheck: { type: Boolean, optional: true },
    };
    static defaultProps = {
        svgCheck: true,
    };
    static template = xml`
        <svg t-if="isSvg(props.src)" t-ref="svg"
             xmlns="http://www.w3.org/2000/svg"
             t-att-width="svg.width"
             t-att-viewBox="svg.viewBox"
             t-att-fill="svg.fill"
             class="hb-svg d-flex m-auto"
             t-att-class="props.class"
             t-att-style="props.style"
             t-att="props.attrs"/>
        <img t-else=""
             t-att-src="props.src"
             t-att-class="props.class"
             t-att-style="props.style"
             t-att-alt="props.alt"
             t-att="props.attrs"/>
        `;

    setup() {
        this.svgRef = useRef("svg");
        this.svg = {};

        onWillStart(async () => {
            await this.handleImgLoad(this.props.src);
        });
        onWillUpdateProps(async (nextProps) => {
            if (this.props.src !== nextProps.src) {
                await this.handleImgLoad(nextProps.src);
            }
        });
        useEffect(() => {
            if (this.isSvg(this.props.src) && this.svg.children.length) {
                // We can't use t-out with markup because it is parsed as HTML,
                // but SVG need to be parsed as XML for all features to work.
                const children = [];
                for (const child of this.svg.children) {
                    children.push(child.cloneNode(true));
                }
                this.svgRef.el.replaceChildren(...children);
            }
        });
    }

    async handleImgLoad(src) {
        if (this.isSvg(src)) {
            this.svg = await this.getSvg();
        } else {
            await this.loadImage(src);
        }
    }

    loadImage() {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve({ status: "loaded" });
            img.onerror = () => resolve({ status: "error" });
            img.src = this.props.src;
        });
    }

    isSvg(src) {
        return this.props.svgCheck && src.split(".").pop() === "svg";
    }

    async getSvg() {
        const svgEl = (await svgCache.read(this.props.src)).cloneNode(true);
        return {
            viewBox: svgEl.getAttribute("viewBox"),
            width: svgEl.getAttribute("width") || "",
            fill: svgEl.getAttribute("fill") || "",
            children: svgEl.children,
        };
    }
}
