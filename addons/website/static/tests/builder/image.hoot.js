import { globals } from "@odoo/hoot";

export const imageRoutes = [
    "/html_builder/static/image_shapes/geometric/geo_shuriken.svg",
    "/html_builder/static/image_shapes/pattern/pattern_wave_4.svg",
    "/html_builder/static/image_shapes/geometric/geo_tetris.svg",
    "/web/image/website.s_text_image_default_image",
    "/website/static/src/img/snippets_demo/s_text_image.jpg",
    "/website/static/src/img/snippets_options/header_effect_fade_out.gif",
    "/web/image/123/transparent.png",
    "/website/static/src/svg/hover_effects.svg",
    "/html_builder/static/image_shapes/geometric/geo_square.svg",
];

let imageRealRPCCached;
export async function loadTestImages() {
    if (!imageRealRPCCached) {
        imageRealRPCCached = {};
        const proms = [];
        for (const route of imageRoutes) {
            const prom = globals.fetch.call(window, route);
            proms.push(prom);
            imageRealRPCCached[route] = prom;

            prom.then((res) => {
                const text = res.text;
                let value;
                res.text = () => {
                    if (!value) {
                        value = text();
                    }
                    return value;
                };
            });
        }
        await Promise.all(proms);
    }
    return imageRealRPCCached;
}
