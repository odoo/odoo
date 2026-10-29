import { click, edit, queryAll, queryFirst, waitFor, waitUntil } from "@odoo/hoot-dom";
import { assertType } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { tutorialSchema } from "@web_tuto/plugin";

/**
 * Types a value in the field "Next" focused, once it did the step: a
 * number, a record picked in the autocomplete of a relational field
 * (created if none), a text otherwise; nothing unless it's an input (e.g.
 * stars), or a date
 * @param {string} number the number of the step, e.g. "2/10"
 */
async function fillFocusedField(number) {
    await waitUntil(() => !queryFirst(`.o_tutorial_progress:contains("Step ${number}")`));
    const input = document.activeElement;
    const widget = input?.closest(".o_field_widget");
    if (
        !input?.matches("input, textarea") ||
        !widget ||
        widget.matches(".o_field_date, .o_field_datetime")
    ) {
        return;
    }
    if (widget.matches(".o_field_float, .o_field_integer, .o_field_monetary")) {
        await edit("10");
    } else if (widget.matches("[class*='many2']")) {
        await click(input);
        await waitFor(".o-autocomplete--dropdown-menu");
        await waitUntil(() => !queryFirst(".o-autocomplete--dropdown-menu .o_loading"));
        const record = queryFirst(
            ".o-autocomplete--dropdown-item:not(.o_m2o_dropdown_option) a:not(.o_loading)"
        );
        if (record) {
            await click(record);
        } else {
            await edit("Tutorial");
            await click(await waitFor(".o_m2o_dropdown_option_create a"));
        }
    } else {
        await edit("Tutorial");
    }
}

/**
 * Names the column the step adds, in the column quick create where its
 * trigger is, for "Next" to add it
 * @param {string} trigger the trigger of the step
 */
async function fillColumnName(trigger) {
    const input = document.activeElement;
    const quickCreate = input?.closest(".o_column_quick_create");
    if (quickCreate && queryAll(trigger, { root: quickCreate }).length && !input.value) {
        await edit("Tutorial");
    }
}

/**
 * Fails unless the pointer shows the help of the step (once its trigger is
 * in view), the tour going through another tutorial otherwise (e.g. one with
 * as many steps)
 * @param {TutorialStepDefinition} step
 */
async function checkContent(step) {
    const isShown = () =>
        queryFirst(".o_tutorial_pointer_content")?.textContent.includes(String(step.content));
    try {
        await waitUntil(isShown, { timeout: 3000 });
    } catch {
        const shown = queryFirst(".o_tutorial_pointer_content")?.textContent;
        throw new Error(`The pointer shows "${shown}" instead of "${step.content}"`);
    }
}

/**
 * @param {string} name
 * @param {string} trigger
 * @returns {TourStep[]} the steps waiting for the trigger, failing right away
 *   with an explicit message if the pointer shows a field left invalid
 *   instead (e.g. a required field the tutorial doesn't make fill in)
 */
function getWaitingSteps(name, trigger) {
    const blocked = ".o_tutorial_invalid";
    return [
        { content: `Wait for ${name}`, trigger: `${trigger}, ${blocked}` },
        {
            content: `${name} isn't blocked by a field left invalid, such as a required one`,
            trigger: `body:not(:has(${blocked}))`,
        },
    ];
}

/**
 * Goes through the tutorial as a user would, only through its pointer: for
 * each step, waits for its bubble, checks it shows its help, and clicks
 * "Next", typing a value in the input "Next" focused when the step needs
 * one, until its rainbow man, closing the dialog and discarding the record
 * it may leave open. A drop is done by "Next" with its drag.
 * @param {TutorialChapterDefinition[]} chapters
 * @returns {TourStep[]}
 */
function getTutorialTourSteps(chapters) {
    assertType(chapters, tutorialSchema);
    const tutorialSteps = chapters.flatMap((chapter) => chapter.steps);
    const tourSteps = [];
    for (const [index, step] of tutorialSteps.entries()) {
        const number = `${index + 1}/${tutorialSteps.length}`;
        if (step.action === "drop") {
            continue;
        }
        tourSteps.push(
            ...getWaitingSteps(`step ${number}`, `.o_tutorial_progress:contains("Step ${number}")`),
            {
                content: `Step ${number} is the one of the tutorial`,
                trigger: ".o_tutorial_pointer_content",
                run: () => checkContent(step),
            }
        );
        if (step.action === "click") {
            tourSteps.push({
                content: `Name the column added by step ${number}, if any`,
                trigger: "body",
                run: () => fillColumnName(step.trigger),
            });
        }
        tourSteps.push({ content: `Do step ${number}`, trigger: ".o_tutorial_next", run: "click" });
        if (step.type === "field") {
            tourSteps.push({
                content: `Fill step ${number}`,
                trigger: "body",
                run: () => fillFocusedField(number),
            });
        }
    }
    return [
        ...tourSteps,
        ...getWaitingSteps("the end of the tutorial", ".o_reward_rainbow_man"),
        {
            content: "Close the dialog left open (e.g. confirming a deletion)",
            trigger: ".modal .btn-close, body:not(:has(.modal))",
            run: "click",
        },
        {
            content: "Discard the record left unsaved",
            trigger: ".o_form_button_cancel, body:not(:has(.o_form_dirty))",
            run: "click",
        },
        {
            content: "Wait for the record to be discarded",
            trigger: "body:not(:has(.o_form_dirty))",
        },
    ];
}

/**
 * Registers the tour going through the tutorial, as `<name>_test`, for its
 * test to start it
 * @param {string} name the name of the tutorial
 */
export function registerTutorialTour(name) {
    const chapters = registry.category("web_tuto.tutorials").get(name);
    registry.category("web_tour.tours").add(`${name}_test`, {
        steps: () => getTutorialTourSteps(chapters),
    });
}
