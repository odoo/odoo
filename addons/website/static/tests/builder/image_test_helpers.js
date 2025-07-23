import { before, globals } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

function onRpcReal(route) {
    onRpc(route, async () => globals.fetch.call(window, route), { pure: true });
}

export const testImgSrc = "/web/image/website.s_text_image_default_image";

export const testImg = `
    <img src='/web/image/website.s_text_image_default_image'
        data-attachment-id="1" data-original-id="1"
        data-original-src="/website/static/src/img/snippets_demo/s_text_image.webp"
        data-mimetype-before-conversion="image/webp"
        >
    `;

export function mockImageRequests() {
    before(() => {
        onRpc("/html_editor/get_image_info", async (data) => ({
            attachment: {
                id: 1,
            },
            original: {
                id: 1,
                image_src: "/website/static/src/img/snippets_demo/s_text_image.webp",
                mimetype: "image/webp",
            },
        }));
        onRpcReal("/html_builder/static/image_shapes/geometric/geo_shuriken.svg");
        onRpcReal("/html_builder/static/image_shapes/pattern/pattern_wave_4.svg");
        onRpcReal("/html_builder/static/image_shapes/geometric/geo_tetris.svg");
        onRpcReal("/web/image/website.s_text_image_default_image");
        onRpcReal("/website/static/src/img/snippets_demo/s_text_image.webp");
        onRpcReal("/web/image/123/transparent.png");
        onRpcReal("/website/static/src/svg/hover_effects.svg");
        onRpcReal("/html_builder/static/image_shapes/geometric/geo_square.svg");
    });
}
