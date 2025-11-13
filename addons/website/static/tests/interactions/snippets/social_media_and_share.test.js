import { animationFrame, click, queryOne, waitFor } from "@odoo/hoot-dom";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "../../builder/website_helpers";
import { expect, test } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

async function setDropdownOption(
    containerTitle,
    optionLabel,
    menuText,
    snippetSelector,
    verifySelector
) {
    await click(`[data-container-title='${containerTitle}'] [data-label='${optionLabel}'] button`);
    await animationFrame();
    await click(`.o_popover .o-dropdown-item:contains(${menuText})`);
    await waitFor(`${snippetSelector}${verifySelector}`);
}

async function testSocialSnippetOptions(snippetName, containerTitle, iconName) {
    const snippetSelector = `:iframe .${snippetName}`;
    onRpc("website", "read", ({ args }) => {
        expect(args[0]).toEqual([1]);
        expect(args[1]).toInclude(`social_${iconName}`);
        return [
            {
                id: 1,
                social_github: `https://${iconName}.com/odoo`,
            },
        ];
    });

    const core = await setupWebsiteBuilderWithSnippet(snippetName, {
        styleContent: `.${snippetName}.no_icon_color a {
            color: inherit !important;
        }`,
    });

    expect(snippetSelector).toHaveCount(1);
    await click(`${snippetSelector} i:first-child`);
    await animationFrame();
    if (snippetName === "s_share") {
        await click(
            `[data-container-title='${containerTitle}'] [data-label='Color'] input[type='checkbox']`
        );
        await animationFrame();
        // Here, .s_share selector can be removed but kept for specificity.
        expect(":iframe .s_share.no_icon_color").toHaveCount(1);
    }
    const textColor = "rgb(255, 0, 0)";
    core.getEditableContent().style.color = textColor;
    const icon = await queryOne(`${snippetSelector} a .fa-${iconName}`);
    if (icon) {
        const iconColor = getComputedStyle(icon).color;
        expect(iconColor).toBe(textColor);
    }
    const forbidden = ["Size", "Style", "Border", "Alignment", "Padding", "Animation"];
    for (const label of forbidden) {
        expect(`[data-container-title='Icon'] [data-label='${label}']`).toHaveCount(0);
    }
    const required = ["Animation", "Background Color"];
    for (const label of required) {
        expect(`[data-container-title='${containerTitle}'] [data-label='${label}']`).toHaveCount(1);
    }
    await setDropdownOption(
        containerTitle,
        "Link Style",
        "Underline On Hover",
        snippetSelector,
        "[data-icon-underline='hover']"
    );
    await setDropdownOption(
        containerTitle,
        "Link Style",
        "Always Underline",
        snippetSelector,
        "[data-icon-underline='always']"
    );
    await setDropdownOption(
        containerTitle,
        "Size",
        "Small",
        snippetSelector,
        " i:first-child.small_social_icon"
    );
    await setDropdownOption(
        containerTitle,
        "Size",
        "Medium",
        snippetSelector,
        " i:first-child:not(.small_social_icon):not(.fa-2x):not(.fa-3x)"
    );
    await setDropdownOption(
        containerTitle,
        "Size",
        "Large",
        snippetSelector,
        " i:first-child.fa-2x"
    );
    await setDropdownOption(
        containerTitle,
        "Size",
        "Huge",
        snippetSelector,
        " i:first-child.fa-3x"
    );
}

test("Social Media snippet options are correct", async () => {
    await testSocialSnippetOptions("s_social_media", "Social Media", "github");
});

test("Share snippet options are correct", async () => {
    await testSocialSnippetOptions("s_share", "Block", "facebook");
});
