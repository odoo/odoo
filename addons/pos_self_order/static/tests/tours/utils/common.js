export function clickBtn(buttonName) {
    return {
        content: `Click on button '${buttonName}'`,
        trigger: `.btn:contains('${buttonName}')`,
        run: "click",
    };
}

export function checkBtn(buttonName) {
    return {
        content: `Check is button '${buttonName}'`,
        trigger: `.btn:contains('${buttonName}')`,
    };
}

export function checkIsNoBtn(buttonName) {
    return {
        content: `Check if '${buttonName}' do not exist`,
        trigger: `body`,
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
    };
}

export function checkLanguageIsAvailable(language) {
    return {
        content: `Check that the language is available`,
        trigger: `.self_order_language_popup .btn:contains(${language})`,
    };
}

export function openLanguageSelector() {
    return {
        content: `Click on language selector`,
        trigger: `.self_order_language_selector`,
        run: "click",
    };
}
