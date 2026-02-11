// @ts-ignore
const owl = globalThis.owl;

const customDirectives = {
    /**
     * @param {HTMLElement} node
     * @param {string} value
     */
    ref: (node, value) => {
        node.setAttribute("t-ref", value);
    },
    /**
     * @param {HTMLElement} node
     * @param {string} value
     * @param {string[]} modifiers
     */
    model: (node, value, modifiers) => {
        let attribute = "t-model";
        for (const modifier of modifiers) {
            attribute += `.${modifier}`;
        }
        node.setAttribute(attribute, value);
    },
};

class App extends owl.App {
    /**
     * @param {any} component
     * @param {any} config
     */
    constructor(component, config) {
        super(component, {
            ...config,
            customDirectives: {
                ...customDirectives,
                ...config.customDirectives,
            },
        });
    }
}
owl.App = App;
