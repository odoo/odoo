export const BASE_CONTAINER_CLASS = "o-base-container";

const SUPPORTED_BASE_CONTAINER_NAMES = ["P", "DIV"];

export class BaseContainer {
    static selector;

    static getBaseContainer(el, document = document) {
        if (!el) {
            return null;
        }
        const baseContainer = new BaseContainer(el.nodeName, document);
        if (!baseContainer || el.nodeName !== baseContainer.nodeName) {
            return null;
        }
        const attributes = baseContainer.attributes;
        for (const attr in attributes) {
            if (attr === "class") {
                for (const className of attributes.class.split(" ")) {
                    if (!el.classList.contains(className)) {
                        return null;
                    }
                }
            } else if (attributes[attr] !== el.getAttribute(attr)) {
                return null;
            }
        }
        return baseContainer;
    }

    constructor(nodeName, document = document) {
        this.document = document;
        this.nodeName =
            nodeName && SUPPORTED_BASE_CONTAINER_NAMES.includes(nodeName) ? nodeName : "P";
        this.classSet = new Set();
        if (this.nodeName !== "P") {
            this.classSet.add(BASE_CONTAINER_CLASS);
        }
    }

    get attributes() {
        if (this.classSet.size) {
            return {
                class: [...this.classSet].join(" "),
            };
        }
        return {};
    }

    get selector() {
        // TODO ABD: unnecessary but maybe attributes other than class should be enforced too
        return `${this.nodeName}${this.classSet.size ? "." : ""}${[...this.classSet].join(".")}`;
    }

    create(document = this.document) {
        const el = document.createElement(this.nodeName);
        if (this.classSet.size) {
            el.setAttribute("class", this.attributes.class);
        }
        return el;
    }

    equals(baseContainer) {
        return (baseContainer && baseContainer.nodeName) === this.nodeName;
    }
}

BaseContainer.selector = SUPPORTED_BASE_CONTAINER_NAMES.map(
    // document may not be loaded yet and is not required to get the selector
    // passing null instead.
    (name) => new BaseContainer(name, null).selector
).join(",");
