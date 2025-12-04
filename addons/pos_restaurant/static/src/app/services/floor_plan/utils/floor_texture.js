import { STATIC_IMG_BASE_URL } from "./utils";

export const FLOOR_TEXTURE = [];
export const FLOOR_TEXTURE_PREFIX = "texture-";
const URL = STATIC_IMG_BASE_URL;

FLOOR_TEXTURE.push({
    id: FLOOR_TEXTURE_PREFIX + "wood-h",
    css: "background-image:url('" + URL + "/wood-h.jpg');",
    previewCss: "background-image:url('" + URL + "/wood-hp.png');",
});

FLOOR_TEXTURE.push({
    id: FLOOR_TEXTURE_PREFIX + "wood-v",
    css: "background-image:url('" + URL + "/wood-v.jpg')",
    previewCss: "background-image:url('" + URL + "/wood-vp.png')",
});

FLOOR_TEXTURE.push({
    id: FLOOR_TEXTURE_PREFIX + "tile-2",
    css: "background-image:url('" + URL + "/tile-2.jpg')",
    previewCss: "background-image:url('" + URL + "/tile-2p.jpg')",
});

FLOOR_TEXTURE.push({
    id: FLOOR_TEXTURE_PREFIX + "tile-3",
    css: "background-image:url('" + URL + "/tile-3.jpg')",
    previewCss: "background-image:url('" + URL + "/tile-3p.jpg')",
});

FLOOR_TEXTURE.push({
    id: FLOOR_TEXTURE_PREFIX + "tile-1",
    css: "background-image:url('" + URL + "/tile-1.jpg')",
    previewCss: "background-image:url('" + URL + "/tile-1p.png')",
});

export function isFloorTextureId(id) {
    return id?.startsWith(FLOOR_TEXTURE_PREFIX);
}

export function getFloorTextureCss(id) {
    return FLOOR_TEXTURE.find((c) => c.id === id)?.css;
}
