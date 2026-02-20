import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.age_verification_popup");
describe.current.tags("interaction_dev");

const modal = "#sAgeVerificationPopup .modal";
const getVerifyBtnSelector = (verificationType) => `${modal} .o_age_verify_${verificationType}_btn`;
const modalErrorMessage = `${modal} #verification_error span`;

/**
 * Generate age verification popup template.
 *
 * @param {Object} [options]
 * @param {string} [options.confirmationType="yes_or_no"]
 * @param {number} [options.minAge=18]
 * @returns {string} Age verification popup template
 */
function getAgeVerificationTemplate(options = {}) {
    const { confirmationType = "yes_or_no", minAge = 18 } = options;

    const TEMPLATES = {
        yes_or_no: `
            <div>
                <a href="#" class="o_age_verification_yes_btn oe_unremovable">Yes</a>
                <a href="#" class="o_age_verification_no_btn oe_unremovable">No</a>
            </div>
        `,
        birth_year: `
            <div>
                <input
                    type="number"
                    class="form-control o_age_verification_birth_year"
                    name="birth_year"
                    min="1900"
                    placeholder="Enter your birth year"
                />
                <a href="#" class="o_age_verify_year_btn oe_unremovable">Verify</a>
            </div>
        `,
        birth_date: `
            <div>
                <div class="input-group">
                    <input
                        type="text"
                        class="form-control o_age_verification_birth_date"
                        name="birth_date"
                        placeholder="Enter your birth date"
                    />
                    <div><i class="fa fa-calendar"></i></div>
                </div>
                <p><a href="#" class="o_age_verify_date_btn oe_unremovable">Verify</a></p>
            </div>
        `,
    };

    return `
        <div class="s_popup s_age_verification_popup o_snippet_invisible" data-vcss="001" id="sAgeVerificationPopup" data-invisible="1">
            <div class="modal fade s_popup_middle" tabindex="-1" role="dialog"
                data-bs-focus="false" data-bs-backdrop="false" data-bs-keyboard="false"
                data-min-age="${minAge}" data-blur-background="true" data-show-after="0" data-display="afterDelay" data-consents-duration="30">
                <div class="modal-dialog">
                    <div class="modal-content oe_structure">
                        <section>
                            <div id="verification_error" class="d-none">
                                <span>You must be older to continue!</span>
                            </div>
                            <div>
                                <h2>Are you 18 years or older?</h2>
                                <p>Our services are available only to adults of legal age.</p>
                            </div>
                            <div id="age_confirmation_block" class="row">
                                ${TEMPLATES[confirmationType]}
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function setupAgeVerificationPopup(options = {}) {
    const { core } = await startInteractions(getAgeVerificationTemplate(options));
    await tick();
    await animationFrame();
    expect(core.interactions).toHaveLength(1);
    expect(modal).toBeVisible();
    expect(modalErrorMessage).not.toBeVisible();
    return core;
}

test("Yes button closes popup and No button displays the error message", async () => {
    await setupAgeVerificationPopup();
    await contains(`${modal} .o_age_verification_no_btn`).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("You must be older to continue!");

    await contains(`${modal} .o_age_verification_yes_btn`).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modal).not.toBeVisible();
});

test("Using birth year input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_year",
        minAge: 20,
    });
    const verifyBtn = getVerifyBtnSelector("year");
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(0);
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2006");
    await contains(verifyBtn).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("You must be older to continue!");
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(0);

    await contains(`${modal} .o_age_verification_birth_year`).edit("1899");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2026");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("1950.25");
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_year.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_year`).edit("2000");
    await contains(verifyBtn).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modal).not.toBeVisible();
});

test("Using birth date input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_date",
        minAge: 20,
    });
    const verifyBtn = getVerifyBtnSelector("date");
    expect(`${modal} .o_age_verification_birth_date.is-invalid`).toHaveCount(0);
    await contains(verifyBtn).click();
    expect(`${modal} .o_age_verification_birth_date.is-invalid`).toHaveCount(1);

    await contains(`${modal} .o_age_verification_birth_date`).edit("01/01/2006");
    await contains(verifyBtn).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessage).toBeVisible();
    expect(modalErrorMessage).toHaveText("You must be older to continue!");

    await contains(`${modal} .o_age_verification_birth_date`).edit("01/01/2004");
    await contains(verifyBtn).click();
    expect("#sAgeVerificationPopup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modal).not.toBeVisible();
});
