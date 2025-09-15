import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { negate } from "@point_of_sale/../tests/tours/utils/common";
const { DateTime } = luxon;
import { waitFor } from "@odoo/hoot-dom";

export function confirmPopup() {
    return [Dialog.confirm()];
}
export function clickMenuButton() {
    return {
        content: "Click on the menu button",
        trigger: ".pos-rightheader button:has(.fa-bars)",
        run: "click",
    };
}
export function clickMenuOption(name, options) {
    return [clickMenuButton(), clickMenuDropdownOption(name, options)];
}
export function clickMenuDropdownOption(name, { expectUnloadPage = false } = {}) {
    return {
        content: `click on something in the burger menu`,
        trigger: `span.dropdown-item:contains(${name})`,
        run: "click",
        expectUnloadPage,
    };
}
export function isCashMoveButtonHidden() {
    return [
        clickMenuButton(),
        {
            trigger: "span.dropdown-item:not(:contains(Cash In/Out))",
            run: () => {},
        },
    ];
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
    };
}
export function isSyncStatusConnected() {
    return {
        trigger: negate(".oe_status", ".pos-rightheader .status-buttons"),
    };
}
export function clickPlanButton() {
    return [
        {
            content: "go back to the floor screen",
            trigger: ".pos-leftheader .back-button:not(.btn-primary)",
            run: "click",
        },
        ...waitRequest(),
    ];
}
export function startPoS() {
    return [
        {
            content: "Start PoS",
            trigger: ".screen-login .btn.open-register-btn",
            run: "click",
        },
    ];
}
export function clickBtn(name, { expectUnloadPage = false } = {}) {
    return {
        content: `Click on ${name}`,
        trigger: `body button:contains(${name})`,
        run: "click",
        expectUnloadPage,
    };
}
export function fillTextArea(target, value) {
    return {
        content: `Fill text area with ${value}`,
        trigger: `textarea${target}`,
        run: `edit ${value}`,
    };
}
export function createFloatingOrder() {
    return { trigger: ".pos-leftheader .list-plus-btn", run: "click" };
}

export function waitRequest() {
    return [
        {
            trigger: "body",
            content: "Wait loading is finished if it is shown",
            timeout: 15000,
            async run() {
                let isLoading = false;
                try {
                    isLoading = await waitFor("body:has(.fa-circle-o-notch)", { timeout: 2000 });
                } catch {
                    /* fa-circle-o-notch will certainly never appears :'( */
                }
                if (isLoading) {
                    await waitFor("body:not(:has(.fa-circle-o-notch))", { timeout: 10000 });
                }
            },
        },
    ];
}

export function freezeDateTime(millis) {
    return [
        {
            trigger: "body",
            run: () => {
                DateTime.now = () => DateTime.fromMillis(millis);
            },
        },
    ];
}

export function isSynced() {
    return {
        content: "Check if the request is proceeded",
        trigger: negate(".fa-spin", ".status-buttons"),
    };
}
