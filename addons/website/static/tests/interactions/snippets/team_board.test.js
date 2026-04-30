import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { animationFrame, click, queryFirst } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList(["website.team_board", "website.team_board_modal"]);

const template = `
    <section class="s_team_board s_team_board_card_layout_grid pt48 pb48 o_colored_level" data-snippet="s_team_board" data-name="Onboarding Team Board">
        <div class="container">
            <h2 class="h3-fs">Meet Our Team</h2>
            <p class="lead mb-4">The people building the experience you rely on every day.</p>
            <div class="row g-4 s_team_board_members s_team_board_density_comfortable">
                <div class="col-12 col-md-6 col-xl-3 s_team_board_member o_colored_level" data-member-id="member_1" data-member-email="tony.fred@example.com" data-name="Team Member">
                    <article class="card h-100 border-0 shadow-sm position-relative">
                        <button type="button" class="s_team_board_member_button o_btn_reset o_button_area cursor-pointer z-1" aria-label="Tony Fred's information"></button>
                        <img class="card-img-top o_editable_media" src="/web/image/website.s_company_team_image_1" alt="Tony Fred" loading="lazy" data-mimetype="image/jpeg" style="">
                        <div class="card-body">
                            <h3 class="h5-fs card-title">Tony Fred</h3>
                            <p class="text-muted mb-2">Tony role</p>
                            <p class="card-text">Tony bio</p>
                        </div>
                    </article>
                </div>
                <div class="col-12 col-md-6 col-xl-3 s_team_board_member o_colored_level" data-member-id="member_2" data-member-email="mich.stark@example.com" data-name="Team Member">
                    <article class="card h-100 border-0 shadow-sm position-relative">
                        <button type="button" class="s_team_board_member_button o_btn_reset o_button_area cursor-pointer z-1" aria-label="Mich Stark's information"></button>
                        <img class="card-img-top o_editable_media" src="/web/image/website.s_company_team_image_2" alt="Mich Stark" loading="lazy" data-mimetype="image/jpeg" style="">
                        <div class="card-body">
                            <h3 class="h5-fs card-title">Mich Stark</h3>
                            <p class="text-muted mb-2">Mich role</p>
                            <p class="card-text">Mich bio</p>
                        </div>
                    </article>
                </div>
                <div class="col-12 col-md-6 col-xl-3 s_team_board_member o_colored_level" data-member-id="member_3" data-member-email="aline.turner@example.com" data-name="Team Member">
                    <article class="card h-100 border-0 shadow-sm position-relative">
                        <button type="button" class="s_team_board_member_button o_btn_reset o_button_area cursor-pointer z-1" aria-label="Aline Turner's information"></button>
                        <img class="card-img-top o_editable_media" src="/web/image/website.s_company_team_image_3" alt="Aline Turner" loading="lazy" data-mimetype="image/jpeg" style="">
                        <div class="card-body">
                            <h3 class="h5-fs card-title">Aline Turner</h3>
                            <p class="text-muted mb-2">Aline role</p>
                            <p class="card-text">Aline bio</p>
                        </div>
                    </article>
                </div>
            </div>
        </div>
    </section>
`;

test("team board modal are shown on click and are correctly filled", async () => {
    await startInteractions(template, { waitForStart: true });
    // Check that the modal is initially closed
    let dialogEl = document.querySelectorAll(".s_team_board_modal_dialog");
    expect(dialogEl).toHaveLength(0);

    // Check that only one modal is opened when a member is clicked
    const memberBtn = queryFirst(".s_team_board .s_team_board_member_button");
    await click(memberBtn);
    await animationFrame();
    dialogEl = document.querySelectorAll(".s_team_board_modal_dialog");
    expect(dialogEl).toHaveLength(1);

    // Check that the modal is filled with member information
    const modalNameEl = document.querySelector("h3.s_team_board_modal_name");
    expect(getContent(modalNameEl)).toBe("Tony Fred");
    const modalRoleEl = document.querySelector("p.s_team_board_modal_role");
    expect(getContent(modalRoleEl)).toBe("Tony role");
    const modalBioEl = document.querySelector("p.s_team_board_modal_bio");
    expect(getContent(modalBioEl)).toBe("Tony bio");
    const modalImageEl = document.querySelector("img.s_team_board_modal_image[alt='Tony Fred']");
    expect(modalImageEl).not.toBe(null);
});

test("team board modal is closed after successfully sending a message", async () => {
    let sendAttempt = 0;
    onRpc("/website/team_board/contact", async () => {
        if (sendAttempt == 0) {
            sendAttempt += 1;
            expect.step("contact fail");
            return { success: false };
        } else {
            expect.step("contact success");
            return { success: true };
        }
    });

    await startInteractions(template, { waitForStart: true });
    const memberBtn = queryFirst(".s_team_board .s_team_board_member_button");
    await click(memberBtn);
    await advanceTime(1000); // Accounts for modal animation
    const sendMessageEl = document.querySelectorAll(
        "button.s_team_board_contact_method_button[data-contact-method-id='sendMessage']"
    );
    expect(sendMessageEl).toHaveLength(1);

    // First click: sending fails, window stays open
    await click(sendMessageEl);
    await animationFrame();
    expect.verifySteps(["contact fail"]);

    await advanceTime(1000); // Accounts for modal animation
    let dialogEl = document.querySelectorAll(".s_team_board_modal_dialog");
    expect(dialogEl).toHaveLength(1);

    // Second click: sending is successful, window closes
    await click(sendMessageEl);
    await animationFrame();
    expect.verifySteps(["contact success"]);

    await advanceTime(1000); // Accounts for modal animation
    dialogEl = document.querySelectorAll(".s_team_board_modal_dialog");
    expect(dialogEl).toHaveLength(0);
});
