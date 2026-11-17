import { CommentNodeLayout } from "../core/render_models";

const IF_NOT_MSO = `[if !mso]><!`;
const END_IF = `<![endif]`;

export function wrapIfMso(content) {
    return `[if mso]>${content}<![endif]`.replace(/\s+/g, " ").trim();
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
 * @returns {number} vml arcsize (%)
 */
export function cssBorderRadiusToVml({ radius, height }) {
    if (!radius || !height) {
        return 0;
    }
    return Math.round((100 * radius) / height);
}

export function buildHideIfNotMsoNodes() {
    const prefix = new CommentNodeLayout({ content: IF_NOT_MSO });
    const suffix = new CommentNodeLayout({ content: END_IF });
    return { prefix, suffix };
}

function escapeHtmlAttribute(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

/**
{
    fill: {
        color: "#ff8800",
        opacity: 1,
    },
    stroke: {
        color: "#cc6600",
        width: 1,
        opacity: 1,
    },
    arcSize: 50,
    padding: {
        top: 6,
        right: 12,
        bottom: 6,
        left: 12,
    },
    href: "https://example.com",
    horizontalAlignment: "center",
}
 */
/**
 * TODO EGGMAIL: link tracking might not work with
 * VML href (not using an anchor) -> to investigate
 */
export function buildInlineShapeVmlContent(
    { fill, stroke, arcSize, padding, href, horizontalAlignment },
    htmlContent
) {
    const shapeStyles = [
        horizontalAlignment && `mso-position-horizontal:${horizontalAlignment}`,
        "mso-position-vertical:top",
        "mso-wrap-style:none",
    ].filter(Boolean);

    const shapeAttributes = [
        'xmlns:v="urn:schemas-microsoft-com:vml"',
        `arcsize="${arcSize}%"`,
        `filled="${Boolean(fill)}"`,
        fill && `fillcolor="${fill.color}"`,
        `stroked="${Boolean(stroke)}"`,
        stroke && `strokecolor="${stroke.color}"`,
        stroke && `strokeweight="${stroke.width}px"`,
        href && `href="${escapeHtmlAttribute(href)}"`,
        `style="${shapeStyles.join(";")}"`,
    ].filter(Boolean);

    const { top, right, bottom, left } = padding;
    const prefixContent = `
        <v:roundrect ${shapeAttributes.join(" ")}>
            <v:textbox
                inset="${left}px,${top}px,${right}px,${bottom}px"
                style="mso-fit-shape-to-text:true;"
            >
    `;
    const suffixContent = `
            </v:textbox>
        </v:roundrect>
    `;
    return [prefixContent, htmlContent, suffixContent].join("");
}

export function buildBackgroundImageVmlNodes({ position, src, width }) {
    const { x, y } = position;
    const prefixContent = `
        <v:rect
            xmlns:v="urn:schemas-microsoft-com:vml"
            fill="true"
            stroke="false"
            style="width:${width}px;"
        >
            <v:fill
                type="frame"
                src="${src}"
                aspect="atleast"
                origin="${x},${y}"
                position="${x},${y}"
            />
            <v:textbox
                inset="0,0,0,0"
                style="mso-fit-shape-to-text:true;"
            >
    `;
    const suffixContent = `
            </v:textbox>
        </v:rect>
    `;
    const prefix = new CommentNodeLayout({ content: wrapIfMso(prefixContent) });
    const suffix = new CommentNodeLayout({ content: wrapIfMso(suffixContent) });
    return { prefix, suffix };
}
