import { before, globals } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

// Pre-fetch image routes so they're cached and available faster during tests
const imgCache = new Map();
function onRpcImg(route) {
    if (!imgCache.has(route)) {
        imgCache.set(route, globals.fetch.call(window, route));
    }
    onRpc(route, async () => (await imgCache.get(route)).clone());
}

export const testImgSrc = "/web/image/website.s_text_image_default_image";

export const testImg = `
    <img src='/web/image/website.s_text_image_default_image'
        data-attachment-id="1" data-original-id="1"
        data-original-src="/website/static/src/img/snippets_demo/s_text_image.webp"
        data-mimetype-before-conversion="image/webp"
        >
    `;

export const testGifImgSrc = "/web/image/456-test/test.gif";

export const testGifImg = `
    <img src='/web/image/456-test/test.gif'>
    `;

export function mockImageRequests() {
    before(() => {
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
                    image_src: "/website/static/src/img/snippets_demo/s_text_image.webp",
                    mimetype: "image/webp",
                },
            };
        });
        onRpcImg("/html_builder/static/image_shapes/geometric/geo_shuriken.svg");
        onRpcImg("/html_builder/static/image_shapes/pattern/pattern_wave_4.svg");
        onRpcImg("/html_builder/static/image_shapes/geometric/geo_tetris.svg");
        onRpcImg("/web/image/website.s_text_image_default_image");
        onRpcImg("/website/static/src/img/snippets_demo/s_text_image.webp");
        onRpcImg("/website/static/src/img/snippets_options/header_effect_fade_out.gif");
        onRpcImg("/web/image/123/transparent.png");
        onRpcImg("/website/static/src/svg/hover_effects.svg");
        onRpcImg("/html_builder/static/image_shapes/geometric/geo_square.svg");
    });
}
