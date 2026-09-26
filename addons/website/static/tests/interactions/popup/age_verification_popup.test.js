import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, runAllTimers, tick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { contains, defineStyle } from "@web/../tests/web_test_helpers";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList("website.age_verification_popup");
beforeEach(() => defineStyle(/* css */ `* { transition: none !important; }`));

describe.current.tags("interaction_dev");

const modalSelector = ".s_age_verification_popup .modal";
const modalErrorMessageSelector = `${modalSelector} #verification_error`;

const TEMPLATES = {
    yes_or_no: `
        <div>
            <a href="#" class="o_age_verification_btn o_age_verification_yes_btn oe_unremovable">Yes</a>
            <a href="#" class="o_age_verification_btn o_age_verification_no_btn oe_unremovable">No</a>
        </div>
    `,
    birth_year: `
        <div>
            <input
                type="number"
                class="form-control"
                name="age_verification_birth_year"
                min="1900"
                placeholder="Enter your birth year"/>
            <a href="#" class="o_age_verification_btn o_age_verification_year_btn oe_unremovable">Verify</a>
        </div>
    `,
    birth_date: `
        <div>
            <div class="input-group">
                <input
                    type="text"
                    class="form-control"
                    name="age_verification_birth_date"
                    placeholder="Enter your birth date"/>
                <div><i class="fa fa-calendar"></i></div>
            </div>
            <p><a href="#" class="o_age_verification_btn o_age_verification_date_btn oe_unremovable">Verify</a></p>
        </div>
    `,
};

function processAgeVerificationPopupHTML({ minAge = 18, confirmationType = "yes_or_no" } = {}) {
    return (html) => {
        const ageVerificationPopupEl = html.querySelector(
            "[data-snippet='s_age_verification_popup']"
        );
        ageVerificationPopupEl.querySelector(".modal").dataset.minAge = minAge;
        ageVerificationPopupEl.querySelector("#age_confirmation_block").innerHTML =
            TEMPLATES[confirmationType];
    };
}

/**
 * Setup the age verification popup for tests.
 *
 * @param {Object} [options]
 * @param {string} [options.confirmationType="yes_or_no"]
 * @param {number} [options.minAge=18]
 * @returns {Promise<{ core: InteractionService }>}
 */
async function setupAgeVerificationPopup(options) {
    const { core } = await startInteractionsWithSnippet("s_age_verification_popup", {
        processHTML: processAgeVerificationPopupHTML(options),
    });
    await tick();
    await animationFrame();
    expect(core.interactions).toHaveLength(1);
    expect(modalSelector).toBeVisible();
    expect(modalErrorMessageSelector).not.toBeVisible();
    return core;
}

test("Yes button closes popup and No button displays the error message", async () => {
    await setupAgeVerificationPopup();
    await contains(`${modalSelector} .o_age_verification_no_btn`).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessageSelector).toBeVisible();

    await runAllTimers();
    await contains(`${modalSelector} .o_age_verification_yes_btn`).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modalSelector).not.toBeVisible();
});

test("Using birth year input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_year",
        minAge: 20,
    });
    const verifyBtnSelector = `${modalSelector} .o_age_verification_year_btn`;
    const birthYearInputSelector = `${modalSelector} input[name="age_verification_birth_year"]`;
    expect(birthYearInputSelector).not.toHaveClass("is-invalid");
    await contains(verifyBtnSelector).click();
    expect(birthYearInputSelector).toHaveClass("is-invalid");

    await contains(birthYearInputSelector).edit("2006");
    await contains(verifyBtnSelector).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessageSelector).toBeVisible();
    expect(birthYearInputSelector).not.toHaveClass("is-invalid");

    // Value below min (1900) is not allowed.
    await contains(birthYearInputSelector).edit("1899");
    await contains(verifyBtnSelector).click();
    expect(birthYearInputSelector).toHaveClass("is-invalid");

    // Value above max (current year) is not allowed.
    await contains(birthYearInputSelector).edit("2026");
    await contains(verifyBtnSelector).click();
    expect(birthYearInputSelector).toHaveClass("is-invalid");

    // Fractional value is not allowed.
    await contains(birthYearInputSelector).edit("1950.25");
    await contains(verifyBtnSelector).click();
    expect(birthYearInputSelector).toHaveClass("is-invalid");

    await contains(birthYearInputSelector).edit("2000");
    await contains(verifyBtnSelector).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modalSelector).not.toBeVisible();
});

test("Using birth date input, Verify button closes popup when age meets minimum", async () => {
    mockDate("2025-11-14 12:00:00");
    await setupAgeVerificationPopup({
        confirmationType: "birth_date",
        minAge: 20,
    });
    const verifyBtnSelector = `${modalSelector} .o_age_verification_date_btn`;
    const birthDateInputSelector = `${modalSelector} input[name='age_verification_birth_date']`;
    expect(birthDateInputSelector).not.toHaveClass("is-invalid");
    await contains(verifyBtnSelector).click();
    expect(birthDateInputSelector).toHaveClass("is-invalid");

    await contains(birthDateInputSelector).edit("01/01/2006");
    await contains(verifyBtnSelector).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "true");
    expect(modalErrorMessageSelector).toBeVisible();

    await contains(birthDateInputSelector).edit("01/01/2004");
    await contains(verifyBtnSelector).click();
    expect(".s_age_verification_popup").toHaveAttribute("data-age-verification-pending", "false");
    expect(modalSelector).not.toBeVisible();
});
