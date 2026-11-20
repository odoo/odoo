import { CommentNodeLayout } from "../core/render_models";

const IF_NOT_MSO = `[if !mso]><!`;
const END_IF = `<![endif]`;

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

export function buildHideFromMsoNodes() {
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
 * TODO EGGMAIL: link tracking might not work with
 * VML href (not using an anchor) -> to investigate
 */
export function buildInlineShapeVmlContent({ fill, stroke, arcSize, padding, href }, htmlContent) {
    const shapeStyles = ["mso-wrap-style:none"];

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

    const prefixContent = `
        <v:roundrect ${shapeAttributes.join(" ")}>
            <v:textbox
                inset="${padding.left}px,${padding.top}px,${padding.right}px,${padding.bottom}px"
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
                src="${escapeHtmlAttribute(src)}"
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
