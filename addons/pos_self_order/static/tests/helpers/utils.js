/** @odoo-module */

export function clickBtn(buttonName) {
    return {
        content: `Click on button '${buttonName}'`,
        trigger: `.btn.btn-lg:contains('${buttonName}')`,
    };
}

export function checkBtn(buttonName) {
    return {
        content: `Check is button '${buttonName}'`,
        trigger: `.btn:contains('${buttonName}')`,
        run: () => {},
    };
}

export function checkIsNoBtn(buttonName) {
    return {
        content: `Check if '${buttonName}' do not exist`,
        trigger: `.btn`,
        run: () => {
            const element = document.querySelectorAll(".btn");

            for (const el of element) {
                const text = el.innerText;

                if (text === buttonName) {
                    throw new Error(`Button '${buttonName}' exist`);
                }
            }

            return true;
        },
    };
}

export function checkIsDisabledBtn(buttonName) {
    return {
        content: `Check if button '${buttonName}' is disabled`,
        trigger: `button.disabled:contains("${buttonName}")`,
        run: () => {},
    };
}
