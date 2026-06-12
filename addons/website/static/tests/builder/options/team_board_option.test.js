import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

function assertMemberOrder(expectedNames) {
    expectedNames.forEach((name, index) => {
        const position = index + 1;
        expect(
            `:iframe .s_team_board_member:nth-of-type(${position}) h3:contains('${name}')`
        ).toHaveCount(1);
    });
}

test("can add members to team board", async () => {
    await setupWebsiteBuilderWithSnippet("s_team_board");
    expect(":iframe .s_team_board .s_team_board_member").toHaveCount(3);

    await contains(":iframe .s_team_board").click();
    await contains(".options-container button[data-action-id='addItem']").click();
    expect(":iframe .s_team_board_member").toHaveCount(4);
});

test("can remove members from team board except the last one", async () => {
    await setupWebsiteBuilderWithSnippet("s_team_board");
    expect(":iframe .s_team_board_member").toHaveCount(3);

    // Click on member, check that delete button is shown and enabled
    await contains(":iframe .s_team_board .s_team_board_member").click();
    expect(".o-overlay-container button.fa-trash").toHaveCount(1);
    expect(".o-overlay-container button.fa-trash").toBeEnabled();

    // Click on delete button, check that element is deleted (2 members remaining).
    // Focus in automatically moved to next member, check that delete button is
    // shown and enabled.
    await contains(".o-overlay-container button.fa-trash").click();
    expect(":iframe .s_team_board_member").toHaveCount(2);
    expect(".o-overlay-container button.fa-trash").toHaveCount(1);
    expect(".o-overlay-container button.fa-trash").toBeEnabled();

    // Click on delete button, check that element is deleted (1 member remaining).
    // Focus in automatically moved to next (last) member, check that delete
    // button is shown but not enabled.
    await contains(".o-overlay-container button.fa-trash").click();
    expect(":iframe .s_team_board_member").toHaveCount(1);
    expect(".o-overlay-container button.fa-trash").toHaveCount(1);
    expect(".o-overlay-container button.fa-trash").not.toBeEnabled();
});

test("can alphabetically sort members in team board", async () => {
    await setupWebsiteBuilderWithSnippet("s_team_board");
    assertMemberOrder(["Tony", "Mich", "Aline"]);

    await contains(":iframe .s_team_board").click();
    await contains(
        ".options-container button[data-action-id='sortTeamBoardMembersAlphabetically']"
    ).click();
    expect(":iframe .s_team_board .s_team_board_member").toHaveCount(3);
    assertMemberOrder(["Aline", "Mich", "Tony"]);
});

test("can feature members in team board", async () => {
    await setupWebsiteBuilderWithSnippet("s_team_board");
    assertMemberOrder(["Tony", "Mich", "Aline"]);

    await contains(":iframe .s_team_board_member h3:contains('Mich')").click();
    await contains(".o-overlay-container button.fa-star").click();
    expect(":iframe .s_team_board .s_team_board_member").toHaveCount(3);
    assertMemberOrder(["Mich", "Tony", "Aline"]);
});

test("can add new team board", async () => {
    await setupWebsiteBuilderWithSnippet("s_team_board");
    expect(":iframe .s_team_board").toHaveCount(1);

    await contains(":iframe .s_team_board").click();
    await contains(
        ".options-container[data-container-title='Onboarding Team Board'] button.fa-plus"
    ).click();
    expect(":iframe .s_team_board").toHaveCount(2);
});
