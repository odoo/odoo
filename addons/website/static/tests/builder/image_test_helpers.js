import { before, globals } from "@odoo/hoot";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ImagePositionOverlay } from "@html_builder/plugins/image/image_position_overlay";

// Pre-fetch image routes so they're cached and available faster during tests
const imgCache = new Map();
export function onRpcImg(route) {
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
            const { params } = await data.json();
            if (params.src === testGifImgSrc) {
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

export function patchDragImage(el, from, to) {
    patchWithCleanup(ImagePositionOverlay.prototype, {
        onDragMove(ev) {
            // Mock the movementX and movementY readonly property
            super.onDragMove({
                preventDefault: () => {},
                movementX: ev.clientX === to.x ? to.x - from.x : 0,
                movementY: ev.clientY === to.y ? to.y - from.y : 0,
            });
        },
    });
    const startDrag = () => contains(el).drag({ position: from });
    const endDrag = async (dragActions) => {
        await dragActions.moveTo(el, { position: to });
        await dragActions.drop();
    };
    return { startDrag, endDrag };
}
