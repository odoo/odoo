import { getMimetypeFromSrc } from "@html_editor/utils/image";
import { before, globals } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

export function onRpcReal(route) {
    onRpc(route, async () => globals.fetch.call(window, route), { pure: true });
}

export const testImg = `
    <img src='/web/image/website.s_text_image_default_image'
        data-original-id="1"
        data-original-src="/website/static/src/img/snippets_demo/s_text_image.jpg"
        data-mimetype-before-conversion="image/jpeg"
        >
    `;

const mockedImgs = {
    "/website/static/src/img/snippets_demo/s_text_image.jpg": {
        id: 1,
        mimetype: "image/jpeg",
    },
    "/web/static/img/logo2.png": {
        id: 2,
        mimetype: "image/png",
    },
};

export function mockImageRequests() {
    before(() => {
        onRpc("/html_editor/get_image_info", async (data) => {
            if (!data.url.endsWith("/html_editor/get_image_info")) {
                return {};
            }
            const body = await data.json();
            console.warn(`body:`, body);
            const src = body.params.src;
            console.warn(`src:`, src);
            if (!mockedImgs[src]) {
                // Character sum
                const numberHash = (str) => str.split("").reduce((h, c) => h + c.charCodeAt(0), 0);
                return {
                    original: {
                        id: numberHash(src),
                        mimetype: getMimetypeFromSrc(src),
                        image_src: src,
                    },
                };
            }
            return {
                original: Object.assign(mockedImgs[src], { image_src: src }),
            };
        });
        onRpcReal("/html_builder/static/image_shapes/geometric/geo_shuriken.svg");
        onRpcReal("/html_builder/static/image_shapes/pattern/pattern_wave_4.svg");
        onRpcReal("/html_builder/static/image_shapes/geometric/geo_tetris.svg");
        onRpcReal("/web/image/website.s_text_image_default_image");
        for (const src in mockedImgs) {
            onRpcReal(src);
        }
    });
}
