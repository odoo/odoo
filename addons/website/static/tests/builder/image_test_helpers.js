import { onRpc } from "@web/../tests/web_test_helpers";
import { loadTestImages } from "./image.hoot";

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

export async function mockImageRequests() {
    const imageRealRPCCached = await loadTestImages();
    for (const route in imageRealRPCCached) {
        onRpc(route, () => {
            console.log(route);
            return imageRealRPCCached[route];
        });
    }

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
}
