import { after, expect } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-dom";

/**
 * @typedef {{
 *  steps: any[];
 *  expectedSteps: any[] | null;
 *  deferred: Deferred | null;
 *  timeout: number;
 * }} StepState
 *
 * @typedef {{
 *  timeout?: number;
 * }} WaitForStepsOptions
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

/**
 * @param {boolean} forceVerifySteps
 */
const checkStepState = (forceVerifySteps) => {
    if (!currentStepState || !currentStepState.expectedSteps) {
        return;
    }

    const { expectedSteps, steps } = currentStepState;
    if (
        forceVerifySteps ||
        (expectedSteps.length === steps.length && expectedSteps.every((s, i) => s === steps[i]))
    ) {
        expect.verifySteps(expectedSteps);
        clearStepState();
    }
};

const clearStepState = () => {
    if (!currentStepState) {
        return;
    }
    if (currentStepState.timeout) {
        clearTimeout(currentStepState.timeout);
    }
    // Never reject since `verifySteps` will already log an error if steps do not match
    currentStepState.deferred?.resolve();
    currentStepState = null;
};

const ensureStepState = () => {
    if (!currentStepState) {
        currentStepState = {
            steps: [],
            deferred: null,
            expectedSteps: null,
            timeout: 0,
        };
        after(runLastCheck);
    }
    return currentStepState;
};

const runLastCheck = () => {
    if (currentStepState?.steps.length) {
        checkStepState(true);
    } else {
        clearStepState();
    }
};

/** @type {StepState | null} */
let currentStepState = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Indicate the completion of a test step. This step must then be verified by
 * calling {@link waitForSteps}.
 *
 * @param {any} step
 */
export function asyncStep(step) {
    const stepState = ensureStepState();
    stepState.steps.push(step);

    expect.step(step);

    // Soft check with newly added step
    checkStepState(false);
}

/**
 * Wait for the given steps to be executed (by {@link asyncStep}), before
 * the end of a given timeout (default: 2000ms).
 *
 * @param {any[]} steps
 * @param {WaitForStepsOptions} [options]
 */
export async function waitForSteps(steps, options) {
    // Check with previous steps (if any)
    checkStepState(true);

    const stepState = ensureStepState();
    stepState.expectedSteps = steps;
    stepState.deferred = new Deferred();
    stepState.timeout = setTimeout(() => checkStepState(true), options?.timeout ?? 2000);

    // Soft check with current steps
    checkStepState(false);

    return stepState.deferred;
}
