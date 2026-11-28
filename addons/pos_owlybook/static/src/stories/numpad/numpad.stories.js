/** @odoo-module */

import { Component } from "@odoo/owl";
import {
    Numpad,
    getButtons,
    enhancedButtons,
    DECIMAL,
    ZERO,
    BACKSPACE,
    DEFAULT_LAST_ROW,
} from "@point_of_sale/app/components/numpad/numpad";
import { registry } from "@web/core/registry";

const defaultButtons = getButtons([DECIMAL, ZERO, BACKSPACE]);
const enhancedBtns = enhancedButtons();
const disabledButtons = getButtons([
    { ...DECIMAL, disabled: true },
    { ...ZERO, disabled: true },
    { ...BACKSPACE, disabled: true },
]).map((b) => ({ ...b, disabled: true }));

class NumpadDefault extends Component {
    static template = "pos_owlybook.NumpadDefault";
    static components = { Numpad };
}

NumpadDefault.storyConfig = {
    title: "Numpad - Default",
    component: Numpad,
    props: {
        buttons: {
            value: defaultButtons,
            readonly: true,
            help: "Standard 1-9 numpad with decimal, zero, and backspace",
        },
        onClick: {
            value: (value) => console.log("Numpad clicked:", value),
            readonly: true,
            help: "Callback triggered when a button is pressed",
        },
    },
};

class NumpadEnhanced extends Component {
    static template = "pos_owlybook.NumpadEnhanced";
    static components = { Numpad };
}

NumpadEnhanced.storyConfig = {
    title: "Numpad - Enhanced",
    component: Numpad,
    props: {
        buttons: {
            value: enhancedBtns,
            readonly: true,
            help: "Enhanced numpad with +10, +20, +50 quick-add buttons and backspace",
        },
        onClick: {
            value: (value) => console.log("Numpad clicked:", value),
            readonly: true,
        },
    },
};

class NumpadDisabled extends Component {
    static template = "pos_owlybook.NumpadDisabled";
    static components = { Numpad };
}

NumpadDisabled.storyConfig = {
    title: "Numpad - Disabled",
    component: Numpad,
    props: {
        buttons: {
            value: disabledButtons,
            readonly: true,
            help: "Numpad with all buttons disabled",
        },
        onClick: {
            value: (value) => console.log("Numpad clicked:", value),
            readonly: true,
        },
    },
};

export const PosNumpadStories = {
    title: "POS Components",
    module: "point_of_sale",
    stories: [NumpadDefault, NumpadEnhanced, NumpadDisabled],
};

registry.category("stories").add("pos_owlybook.numpad", PosNumpadStories);
