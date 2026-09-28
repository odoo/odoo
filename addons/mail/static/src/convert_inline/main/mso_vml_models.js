import { CommentNodeLayout } from "../core/render_models";

function wrapIfMso(content) {
    return `[if mso]>${content}<![endif]`.replace(/\s+/g, " ").trim();
}

function cssBackgroundPositionToVml(percent) {
    return percent / 100 - 0.5;
}

function cssBorderRadiusToVml(pixels) {
    return;
}

export function buildBadgeVmlNodes({ borderRadius, backgroundColor, horizontalAlignment, padding }) {
    const arcsize = cssBorderRadiusToVml({ borderRadius });
    const { top, right, bottom, left } = padding;
    const prefixContent = `
        <v:roundrect
            xmlns:v="urn:schemas-microsoft-com:vml"
            arcsize="${arcsize}%"
            fillcolor="${backgroundColor}"
            mso-position-horizontal:${horizontalAlignment};
            mso-position-vertical:top;
            stroked="false">
            <v:textbox inset="${left}px,${top}px,${right}px,${bottom}px" style="mso-fit-shape-to-text:true;"
        >
    `;
    const suffixContent = `
            </v:textbox>
        </v:roundrect>
    `;
}

export function buildButtonVmlNodes({ href }) {
    const prefixContent = `
        <v:roundrect
            xmlns:v="urn:schemas-microsoft-com:vml"
            xmlns:w="urn:schemas-microsoft-com:office:word"
            href="https://example.com"
            style="width:200px;height:48px;v-text-anchor:middle;"
            arcsize="25%"
            fillcolor="#2563eb"
            stroked="false"
        >
            <w:anchorlock/>
            <center
                style="
                    color:#ffffff;
                    font-family:Arial,sans-serif;
                    font-size:16px;
                    font-weight:bold;
                ">
                Click me
            </center>
        </v:roundrect>
    `;
}

export function buildBackgroundImageVmlNodes({ position, src, width }) {
    const x = cssBackgroundPositionToVml(position.x);
    const y = cssBackgroundPositionToVml(position.y);
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
