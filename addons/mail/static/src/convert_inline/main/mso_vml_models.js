import {
    CommentNodeLayout,
    CommentPairLayout,
    WrapperLayout,
} from "@mail/convert_inline/core/render_models";

const IF_NOT_MSO = `[if !mso]><!`;
const END_IF = `<![endif]`;
const VML_NAMESPACE = "urn:schemas-microsoft-com:vml";

export function wrapIfMso(content) {
    return `[if mso]>${content}<![endif]`;
}

/**
 * @param {number} percent
 * @returns {number} vml position
 */
export function cssBackgroundPositionToVml(percent) {
    return percent / 100 - 0.5;
}

/**
 * @param {number} radius (in pixels)
 * @param {number} height (in pixels)
 * @param {number} width (in pixels)
 * @returns {number} vml arcsize (%)
 */
export function cssBorderRadiusToVml({ radius, height, width }) {
    const minSize = Math.min(height, width);
    if (!radius || !minSize) {
        return 0;
    }
    return Math.round(Math.max(0, Math.min(100, (200 * radius) / minSize)));
}

function escapeHtmlAttribute(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

/**
 * @param {Object<string, *>} attributes, falsy values are ignored
 * @returns {string} serialized attributes
 */
function serializeAttributes(attributes) {
    return Object.entries(attributes)
        .filter(([, value]) => value || value === 0)
        .map(([name, value]) => `${name}="${escapeHtmlAttribute(value)}"`)
        .join(" ");
}

/**
 * @param {Element} element
 * @param {Object<string, *>} attributes, falsy values are ignored
 */
function setElementAttributes(element, attributes) {
    for (const [name, value] of Object.entries(attributes)) {
        if (value || value === 0) {
            element.setAttribute(name, value);
        }
    }
}

function removeComments(root) {
    const treeWalker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT);
    const comments = [];
    while (treeWalker.nextNode()) {
        comments.push(treeWalker.currentNode);
    }
    for (const comment of comments) {
        comment.remove();
    }
}

/**
 * Hide the wrapped content from MSO clients.
 */
export function buildHideFromMsoLayout() {
    return new CommentPairLayout({ prefix: IF_NOT_MSO, suffix: END_IF });
}

/**
 * Wrap the content in a VML rectangle with a background image for MSO clients.
 * The content itself is displayed for every mail client.
 */
export function buildBackgroundImageVmlLayout({ position, src, width }) {
    const { x, y } = position;
    const rectAttributes = serializeAttributes({
        "xmlns:v": VML_NAMESPACE,
        fill: "true",
        stroke: "false",
        style: `width:${width}px;`,
    });
    const fillAttributes = serializeAttributes({
        type: "frame",
        src,
        aspect: "atleast",
        origin: `${x},${y}`,
        position: `${x},${y}`,
    });
    const textboxAttributes = serializeAttributes({
        inset: "0,0,0,0",
        style: "mso-fit-shape-to-text:true;",
    });
    return new CommentPairLayout({
        prefix: wrapIfMso(
            `<v:rect ${rectAttributes}><v:fill ${fillAttributes}/><v:textbox ${textboxAttributes}>`
        ),
        suffix: wrapIfMso(`</v:textbox></v:rect>`),
    });
}

/**
 * Display the wrapped content only for MSO clients: the content is serialized
 * inside a single `[if mso]` conditional comment. Every comment inside the
 * content is removed (it would close the conditional comment prematurely).
 * Plugins are responsible to not spawn conditional comments inside an
 * `[if mso]` branch.
 */
export class MsoOnlyLayout extends WrapperLayout {
    renderToFragment(context = {}) {
        const container = document.createElement("DIV");
        container.append(...this.renderContent(context));
        removeComments(container);
        const comment = new CommentNodeLayout({ content: wrapIfMso(container.innerHTML) });
        return comment.renderToFragment();
    }
}

/**
 * Wrap the content in a VML rounded rectangle (shape of a button or a badge).
 * The VML elements are rendered as DOM elements, so this layout must only be
 * used inside a MsoOnlyLayout, which serializes them in a MSO conditional
 * comment.
 *
 * TODO EGGMAIL: link tracking might not work with
 * VML href (not using an anchor) -> to investigate
 */
export class VmlRoundRectLayout extends WrapperLayout {
    /**
     * @param {Object} options
     * @param {{ color: string }|null} options.fill
     * @param {{ color: string, width: number }|null} options.stroke
     * @param {number} options.arcSize (%)
     * @param {{ top: number, right: number, bottom: number, left: number }} options.padding (px)
     * @param {string|null} options.href
     */
    constructor({ fill, stroke, arcSize, padding, href }) {
        super();
        Object.assign(this, { fill, stroke, arcSize, padding, href });
    }

    renderToFragment(context = {}) {
        const { fill, stroke, arcSize, padding, href } = this;
        const shape = document.createElement("v:roundrect");
        setElementAttributes(shape, {
            "xmlns:v": VML_NAMESPACE,
            arcsize: `${arcSize}%`,
            filled: String(Boolean(fill)),
            fillcolor: fill?.color,
            stroked: String(Boolean(stroke)),
            strokecolor: stroke?.color,
            strokeweight: stroke && `${stroke.width}px`,
            href,
            style: "mso-wrap-style:none;",
        });
        const textbox = document.createElement("v:textbox");
        setElementAttributes(textbox, {
            inset: `${padding.left}px,${padding.top}px,${padding.right}px,${padding.bottom}px`,
            style: "mso-fit-shape-to-text:true;",
        });
        textbox.append(...this.renderContent(context));
        shape.append(textbox);
        const fragment = document.createDocumentFragment();
        fragment.append(shape);
        return fragment;
    }
}
