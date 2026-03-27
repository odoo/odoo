import { escapeRegExp } from "@web/core/utils/strings";

export const buttonTriger = (buttonValue) =>
    `div.numpad button:contains(/^${escapeRegExp(buttonValue)}$/)`; // regex to match the exact button value ( for ex: avoids matching "+10" instead of "1")

export const click = (buttonValue) => ({
    content: `click numpad button: ${buttonValue}`,
    trigger: buttonTriger(buttonValue),
    run: "click",
});
export const enterValue = (keys) => keys.split("").map((key) => click(key));
export const isActive = (buttonValue) => ({
    content: `check if --${buttonValue}-- mode is activated`,
    trigger: `${buttonTriger(buttonValue)}.active`,
});

export const isVisible = () => ({
    content: "check if numpad is visible",
    trigger: "div.numpad:visible",
});
