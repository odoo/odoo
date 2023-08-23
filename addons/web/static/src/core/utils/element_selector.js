/** @odoo-module **/

export class ElementSelector {
    constructor(textSelector) {
        this.result = [];
        this.textSelector = textSelector;
        this.textElement = null;
        this.element = null;
        if (textSelector instanceof HTMLElement) {
            this.element = textSelector;
        } else if (typeof textSelector === "string") {
            this.toNative();
        }
        return this;
    }
    get toText() {
        return this.textElement;
    }
    get toNodeList() {
        const nodelist = eval(this.textElement);
        return [...nodelist];
    }
    get toElement() {
        if (this.element) {
            return this.element;
        } else {
            const nodelist = eval(this.textElement);
            return [...nodelist][0];
        }
    }

    children(depth = 10) {
        const children = [];
        function getChildren(node, i) {
            if (node.childNodes instanceof NodeList && i < depth) {
                i++;
                children.push(...node.childNodes);
                node.childNodes.forEach((child) => {
                    getChildren(child, i);
                });
            }
        }
        getChildren(this.toElement, 0);
        return children;
    }

    contains(nodelist) {
        console.log(nodelist);
        nodelist =
            nodelist instanceof NodeList
                ? nodelist
                : nodelist instanceof HTMLElement
                ? [nodelist]
                : typeof nodelist === "string"
                ? new ElementSelector(nodelist).toNodeList
                : Array.isArray(nodelist)
                ? nodelist
                : nodelist instanceof ElementSelector
                ? nodelist.toNodeList
                : [];
        console.log(nodelist);
        const children = this.children();
        return nodelist.length > 0
            ? [...nodelist].filter((node) => {
                  return node instanceof HTMLElement && children.includes(node);
              }).length
            : 0;
    }

    toNative(selector = this.textSelector) {
        if (String(selector).startsWith("document.querySelector")) {
            this.textElement = this.textSelector;
            return;
        } else if (selector.trim().length === 0) {
            this.build();
            return;
        } else if (selector.includes(":contains(")) {
            const match = selector.match(
                /(?<before>.*?):contains\((["']?)(?<contains>.*?)\2\)(?<after>.*)/
            );
            const { before, contains, after } = match.groups;
            this.result.push("querySelectorAll(`" + before.trim() + "`)");
            this.result.push("containsText(`" + contains.trim() + "`)");
            return this.toNative(after);
        } else {
            this.result.push("querySelectorAll(`" + selector.trim() + "`)");
            this.build();
        }
    }
    build() {
        this.result.unshift("document");
        this.textElement = this.result.join(".") + ";";
        console.log(this.textElement);
    }
}

/**
 * @param {NodeList} elements
 * @param {string} string
 * @returns {HTMLElement[]}
 */
export function containsText(elements, string) {
    if (!(elements instanceof NodeList)) {
        throw new Error(`elements has to be instance of NodeList[] (use .querySelectorAll)`);
    }
    return [...elements].filter((element) => element.textContent.includes(string));
}

/**
 * @param {NodeList} elements
 * @param {string} string
 * @returns {HTMLElement | null}
 */
export function containsTextOnce(elements, string) {
    if (!(elements instanceof NodeList)) {
        throw new Error(`elements has to be instance of NodeList[] (use .querySelectorAll)`);
    }
    return [...elements].find((element) => element.textContent.includes(string));
}

/**
 * @param {NodeList} elements
 * @returns {string}
 */
export function getText(elements) {
    if (!(elements instanceof NodeList)) {
        throw new Error(`elements has to be instance of NodeList[] (use .querySelectorAll)`);
    }
    return [...elements].map((element) => element.textContent).join("");
}

NodeList.prototype.containsTextOnce = function (text) {
    return containsTextOnce(this, text);
};
NodeList.prototype.containsText = function (text) {
    return containsText(this, text);
};
NodeList.prototype.getText = function () {
    return getText(this);
};

window.ElementSelector = ElementSelector;
