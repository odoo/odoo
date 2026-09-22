import { CommentNodeLayout } from "../core/render_models";

function wrapIfMso(content) {
    return `[if mso]>${content}<![endif]`.replace(/\s+/g, " ").trim();
}

function cssBackgroundPositionToVml(percent) {
    return percent / 100 - 0.5;
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
