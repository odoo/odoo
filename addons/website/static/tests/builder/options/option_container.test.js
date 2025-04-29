import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

const simpleTitleHtml = `
    <section class="s_title" data-snippet="s_title" data-name="Title">
        <h1>Title</h1>
    </section>`;

test("version control: bypass outdated", async () => {
    await setupWebsiteBuilder(simpleTitleHtml, { versionControl: true });
    await contains(":iframe .s_title").click();
    await waitFor(".o_we_version_control");
    expect(".o_we_version_control").toHaveCount(1);
    expect(".we-bg-options-container:contains('Visibility'").toHaveCount(0);
    await contains(".o_we_version_control button:contains('ACCESS')").click();
    await animationFrame();
    expect(".o_we_version_control").toHaveCount(0);
    expect(".we-bg-options-container:contains('Visibility'").toHaveCount(1);
});

test("version control: replace outdated", async () => {
    await setupWebsiteBuilder(simpleTitleHtml, { versionControl: true });
    await contains(":iframe .s_title").click();
    await waitFor(".o_we_version_control");
    expect(".o_we_version_control").toHaveCount(1);
    expect(".we-bg-options-container:contains('Visibility'").toHaveCount(0);
    await contains(".o_we_version_control button:contains('REPLACE')").click();
    await animationFrame();
    expect(".o_we_version_control").toHaveCount(0);
    expect(".we-bg-options-container:contains('Visibility'").toHaveCount(1);
    expect(":iframe .s_title:contains('Your Site Title')").toHaveCount(1);
});
