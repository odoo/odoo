/** @odoo-module */

<<<<<<< 17.0
export function confirmPopup() {
    return [
        {
            content: "confirm popup",
            trigger: ".popups .modal-dialog .button.confirm",
        },
    ];
}
export function clickTicketButton() {
    return [
        {
            trigger: ".pos-topheader .ticket-button",
        },
        {
            trigger: ".screen.ticket-screen",
            run: () => {},
        },
    ];
}
export function clickMenuButton() {
    return [
        {
            content: "Click on the menu button",
            trigger: ".menu-button",
        },
    ];
}
export function closeSession() {
    return [
        ...clickMenuButton(),
        {
            content: "click on the close session menu button",
            trigger: ".close-button",
        },
        {
            content: "click on the close session popup button",
            trigger: ".close-pos-popup .footer .button.highlight",
        },
        {
            content: "check that the session is closed without error",
            trigger: ".o_web_client",
            isCheck: true,
        },
    ];
}
export function isCashMoveButtonHidden() {
    return [
        {
            extraTrigger: ".pos-topheader",
            trigger: ".pos-topheader:not(:contains(Cash In/Out))",
            run: () => {},
        },
    ];
}
export function isCashMoveButtonShown() {
    return [
        {
            trigger: ".pos-topheader:contains(Cash In/Out)",
            run: () => {},
        },
    ];
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
        isCheck: true,
    };
}
||||||| 51296055790f8c6f01dfbbc82ca340756c54cdb3
    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        confirmPopup() {
            return [
                {
                    content: 'confirm popup',
                    trigger: '.popups .modal-dialog .button.confirm',
                },
            ];
        }
        clickTicketButton() {
            return [
                {
                    trigger: '.pos-topheader .ticket-button',
                },
                {
                    trigger: '.subwindow .ticket-screen',
                    run: () => {},
                },
            ];
        }
    }

    class Check {
        isCashMoveButtonHidden() {
            return [
                {
                    trigger: '.pos-topheader:not(:contains(Cash In/Out))',
                    run: () => {},
                }
            ];
        }

        isCashMoveButtonShown() {
            return [
                {
                    trigger: '.pos-topheader:contains(Cash In/Out)',
                    run: () => {},
                }
            ];
        }
    }

    return createTourMethods('Chrome', Do, Check);
});
=======
    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        confirmPopup() {
            return [
                {
                    content: 'confirm popup',
                    trigger: '.popups .modal-dialog .button.confirm',
                },
            ];
        }
        clickTicketButton() {
            return [
                {
                    trigger: '.pos-topheader .ticket-button',
                },
                {
                    trigger: '.subwindow .ticket-screen',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('Chrome', Do);
});
>>>>>>> c2acc7045d4e27d2ff68e7a61de9a50117f8ac2f
