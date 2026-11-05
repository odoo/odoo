import { expect, test } from "@odoo/hoot";
import { delay, setInputFiles, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { showAddFontDialog } from "@website/builder/plugins/font/add_font_dialog";
import { defineWebsiteModels } from "../website_helpers";

defineWebsiteModels();

async function openDialog() {
    onRpc("/website/theme_upload_font", () => {
        expect.step("upload");
        return [{ name: "Regular.ttf", url: "/web/content/1/Regular.ttf" }];
    });
    onRpc("ir.attachment", "create_unique", () => [1]);
    mockService("website", { currentWebsite: { cookies_bar: false } });
    await mountWithCleanup(MainComponentsContainer);
    const fonts = { allFonts: [], googleFonts: [], googleLocalFonts: [], uploadedLocalFonts: [] };
    const customize = async () => expect.step("customize");
    showAddFontDialog(getService("dialog"), fonts, "font", customize, async () => {});
}

async function uploadFont(fileName) {
    await contains("input#upload_font").click();
    await setInputFiles([new File(["font"], fileName)]);
}

const refused = [",", ":", "'", '"', "\\", "#", "?", "%"].map((char) => `A${char}B.ttf`);
for (const fileName of [...refused, ".ttf"]) {
    test(`uploaded font ${fileName} is refused and clears the previous upload`, async () => {
        await openDialog();
        await uploadFont("Caveat.zip");
        await waitFor(".modal:contains('Preview of Caveat')");
        await uploadFont(fileName);
        await waitFor(".modal-title:contains('Invalid font name')");
        await delay(100);
        expect("input#upload_font").toHaveValue("");
        expect(".modal:contains('Preview of')").toHaveCount(0);
        expect.verifySteps(["upload"]);
    });
}

for (const fileName of ["Caveat.zip", "Noto Sans-Regular.ttf", "A 9pt.v2.woff2", "Café.ttf", "A"]) {
    test(`uploaded font ${fileName} is saved`, async () => {
        await openDialog();
        await uploadFont(fileName);
        await waitFor(".modal:contains('Preview of')");
        await contains(".modal-footer .btn-primary").click();
        await expect.waitForSteps(["upload", "customize"]);
    });
}
