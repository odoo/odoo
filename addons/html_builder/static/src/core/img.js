import {
    Component,
    onMounted,
    onPatched,
    onWillStart,
    useEffect,
    props,
    signal,
    t,
    xml,
} from "@odoo/owl";
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

export class Image extends Component {
    props = props({
        src: t.string(),
        class: t.string().optional(),
        style: t.string().optional(),
        alt: t.string().optional(),
        attrs: t.object().optional(),
        svgCheck: t.boolean().optional(true),
    });
    static template = xml`
        <t t-if="this.loaded()">
            <svg xmlns="http://www.w3.org/2000/svg" t-if="this.isSvg(this.props.src)" t-ref="this.svgRef"
                t-att-width="this.svg.width"
                t-att-viewBox="this.svg.viewBox"
                t-att-fill="this.svg.fill"
                class="hb-svg d-flex m-auto"
                t-att-class="this.props.class"
                t-att-style="this.props.style"
                t-att="this.props.attrs"/>
            <img t-else=""
                t-att-src="this.props.src"
                t-att-class="this.props.class"
                t-att-style="this.props.style"
                t-att-alt="this.props.alt"
                t-att="this.props.attrs"/>
        </t>
        `;

    loaded = signal(false);
    svgRef = signal(null);

    setup() {
        this.svg = {};

        onWillStart(async () => this.handleImgLoad(this.props.src));
        useEffect(() => {
            const src = this.props.src;
            this.loaded.set(false);
            this.handleImgLoad(src);
        });
        const insertSvgChildren = () => {
            if (
                this.loaded() &&
                this.svgRef() &&
                this.isSvg(this.props.src) &&
                this.svg.children?.length
            ) {
                // We can't use t-out with markup because it is parsed as HTML,
                // but SVG need to be parsed as XML for all features to work.
                const children = [];
                for (const child of this.svg.children) {
                    children.push(child.cloneNode(true));
                }
                this.svgRef().replaceChildren(...children);
            }
        };
        onMounted(insertSvgChildren);
        onPatched(insertSvgChildren);
    }

    async handleImgLoad(src) {
        const prom = this.isSvg(src) ? this.getSvg() : this.loadImage(src);
        if (this.isSvg(src)) {
            prom.then((svg) => {
                this.svg = svg;
            });
        }
        if (this.env.imgGroup) {
            this.env.imgGroup.addImgProm(prom);
            this.env.imgGroup.loaded.then(() => {
                this.loaded.set(true);
            });
        } else {
            await prom;
            this.loaded.set(true);
        }
    }

    loadImage() {
        return new Promise((resolve, reject) => {
            const img = new window.Image();
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
