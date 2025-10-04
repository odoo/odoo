import { before, globals } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

const imageRpcCache = new Map();
function onRpcReal(route) {
    onRpc(route, async () => imageRpcCache.get(route), { pure: true });
}

function loadImages(imageRoutes) {
    const proms = [];
    for (const route of imageRoutes) {
        const prom = globals.fetch.call(window, route);
        imageRpcCache.set(route, prom);
        proms.push(prom);
    }
    return Promise.all(proms);
}

export const testImgSrc = "/web/image/website.s_text_image_default_image";

export const testImg = `
    <img src='/web/image/website.s_text_image_default_image'
        data-original-id="1"
        data-original-src="/website/static/src/img/snippets_demo/s_text_image.jpg"
        data-mimetype-before-conversion="image/jpeg"
        >
    `;

export const testGifImgSrc = "/web/image/456-test/test.gif";

export const testGifImg = `
    <img src='/web/image/456-test/test.gif'>
    `;

export function mockImageRequests() {
    before(async () => {
        onRpc("/html_editor/get_image_info", async (data) => {
            const body = await data.body.getReader().read();
            const { src } = JSON.parse(new TextDecoder().decode(body.value)).params;
            if (src === testGifImgSrc) {
                return {
                    attachment: {
                        id: 456,
                    },
                    original: {
                        id: 456,
                        image_src:
                            "/website/static/src/img/snippets_options/header_effect_fade_out.gif",
                        mimetype: "image/gif",
                    },
                };
            }
            return {
                attachment: {
                    id: 1,
                },
                original: {
                    id: 1,
                    image_src: "/website/static/src/img/snippets_demo/s_text_image.jpg",
                    mimetype: "image/jpeg",
                },
            };
        });
        const images = [
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
        await loadImages(images);

        for (const img of images) {
            onRpcReal(img);
        }
    });
}
