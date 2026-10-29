import { CommentNodeLayout } from "../core/render_models";

function wrapIfMso(content) {
    return `[if mso]>${content}<![endif]`.replace(/\s+/g, " ").trim();
}

/**
 * @param {number} percent
 * @returns {number} vml position
 */
function cssBackgroundPositionToVml(percent) {
    return percent / 100 - 0.5;
}

/**
 * @param {number} radius (in pixels)
 * @param {number} height (in pixels)
 * @returns {number} vml arcsize (%)
 */
function cssBorderRadiusToVml({ radius, height }) {
    if (!radius || !height) {
        return 0;
    }
    return Math.round((100 * radius) / height);
}

export function buildBadgeVmlNodes({
    backgroundColor,
    borderRadius,
    height,
    horizontalAlignment,
    padding,
}) {
    // TODO EGGMAIL WORKING HERE: maybe this form should replace the container
    // instead of wrapping it? But then it has to be duplicated
    // but duplication seems unavoidable anyways, also might be needed
    // for background images too? can they overlap?
    // if spacing has to be integrated in VML, it can not be repeated
    // in the HTML content
    // => conclusion, for background images we use prefix/suffix to avoid
    // duplicating a large subtree
    // => for badges and buttons => we use an alternate form
    // => both options should be available at the render_plugin level
    // actually they already are: prefix => if not mso,
    // suffix => if mso => mso form
    // OR => if mso + mso form + if not mso as a lone prefix => might be
    // cleaner? => except I still need a endif as suffix, but still
    // seems cleaner
    // => missing the logic to take the duplicated nodes and render them
    // => also if there are MSO considerations, they should only happen in the
    // MSO sub-branch, no need for them to happen in the non-MSO branch
    const arcSize = cssBorderRadiusToVml({ borderRadius, height });
    const { top, right, bottom, left } = padding;
    const prefixContent = `
        <v:roundrect
            xmlns:v="urn:schemas-microsoft-com:vml"
            arcsize="${arcSize}%"
            fillcolor="${backgroundColor}"
            mso-position-horizontal:${horizontalAlignment};
            mso-position-vertical:top;
            mso-wrap-style:none;
            stroked="false"
        >
            <v:textbox
                inset="${left}px,${top}px,${right}px,${bottom}px"
                style="mso-fit-shape-to-text:true;"
            >
    `;
    const suffixContent = `
            </v:textbox>
        </v:roundrect>
    `;
    const prefix = new CommentNodeLayout({ content: wrapIfMso(prefixContent) });
    const suffix = new CommentNodeLayout({ content: wrapIfMso(suffixContent) });
    return { prefix, suffix };
}

export function buildButtonVmlNodes({
    backgroundColor,
    borderRadius,
    height,
    horizontalAlignment,
    href,
    linkStyle,
    linkText,
}) {
    // const arcSize = cssBorderRadiusToVml({ borderRadius, height });
    // const { top, right, bottom, left } = padding;
    // const prefixContent = `
    //     <v:roundrect
    //         xmlns:v="urn:schemas-microsoft-com:vml"
    //         arcsize="${arcSize}%"
    //         fillcolor="${backgroundColor}"
    //         href="${href}"
    //         mso-position-horizontal:${horizontalAlignment};
    //         mso-position-vertical:top;
    //         mso-wrap-style:none;
    //         stroked="false"
    //     >
    //         <v:textbox inset="${left}px,${top}px,${right}px,${bottom}px" style="mso-fit-shape-to-text:true;"
    //             <center style="${linkStyle}">
    //                 ${linkText}
    //             </center>
    //         </v:textbox>
    //     </v:roundrect>
    // `;
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
