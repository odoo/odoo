/** @odoo-module */

const buttonTriger = (buttonValue) => `div.numpad.row button.col:contains("${buttonValue}")`;
export const Numpad = {
    click: (buttonValue, options = {}) => ({
        content: `click numpad button: ${buttonValue}`,
        trigger: buttonTriger(buttonValue),
        run: () => {
            [...$(buttonTriger(buttonValue))]
                .filter((el) => el.innerHTML == buttonValue)[0]
                ?.click();
        },
        mobile: options.mobile,
    }),
    isActive: (buttonValue) => ({
        content: `check if --${buttonValue}-- mode is activated`,
        trigger: `${buttonTriger(buttonValue)}.active`,
        isCheck: true,
    }),
};
