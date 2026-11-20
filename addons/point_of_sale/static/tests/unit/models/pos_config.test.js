import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

function generateLogoContent(width, height) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas.toDataURL().split(",")[1];
}

async function getImageSize(dataUrl) {
    const img = new Image();
    img.src = dataUrl;
    await img.decode();
    return [img.naturalWidth, img.naturalHeight];
}

describe("cacheReceiptLogo", () => {
    test("large logo is downscaled", async () => {
        const store = await setupPosEnv();
        store.config.logo = { content: generateLogoContent(1292, 646) };
        await store.config.cacheReceiptLogo();
        expect(await getImageSize(store.config.receiptLogoUrl)).toEqual([256, 128]);
    });

    test("small logo is kept as is", async () => {
        const store = await setupPosEnv();
        const content = generateLogoContent(100, 50);
        store.config.logo = { content };
        await store.config.cacheReceiptLogo();
        expect(store.config.receiptLogoUrl).toBe(`data:image/png;base64,${content}`);
    });

    test("cache is ignored when the logo changes", async () => {
        const store = await setupPosEnv();
        store.config.logo = { content: generateLogoContent(1292, 646) };
        await store.config.cacheReceiptLogo();
        const content = generateLogoContent(600, 300);
        store.config.logo = { content };
        expect(store.config.receiptLogoUrl).toBe(`data:image/png;base64,${content}`);
    });
});
