import { queryAll } from "@odoo/hoot-dom";

const buttonTriger = (buttonValue) => `div.numpad.row button.col:contains("${buttonValue}")`;
export const click = (buttonValue, options = {}) => ({
    content: `click numpad button: ${buttonValue}`,
    trigger: buttonTriger(buttonValue),
    // here we couldn't simply use the jquery `:contains` selector because it
    // would match (for ex) the button with the value "+10" when we want to click the
    // button with the value "1". Here we need to match the exact value.
    run: () => {
        queryAll(buttonTriger(buttonValue))
            .filter((el) => el.innerHTML == buttonValue)
            .at(0)
            ?.click();
    },
    mobile: options.mobile,
});
export const enterValue = (keys) => keys.split("").map((key) => click(key));
export const isActive = (buttonValue) => ({
    content: `check if --${buttonValue}-- mode is activated`,
    trigger: `${buttonTriger(buttonValue)}.active`,
    isCheck: true,
});
