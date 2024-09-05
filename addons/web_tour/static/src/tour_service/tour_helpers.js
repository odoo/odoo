import * as hoot from "@odoo/hoot-dom";

export class TourHelpers {
    /**
     * @typedef {string|Node} Selector
     */

    constructor(anchor) {
        this.anchor = anchor;
        this.delay = 20;
    }

    /**
     * Ensures that the given {@link Selector} is checked.
     * @description
     * If it is not checked, a click is triggered on the input.
     * If the input is still not checked after the click, an error is thrown.
     *
     * @param {string|Node} selector
     * @example
     *  run: "check", //Checks the action element
     * @example
     *  run: "check input[type=checkbox]", // Checks the selector
     */
    async check(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "check");
        await hoot.check(element);
    }

    /**
     * Clears the **value** of the **{@link Selector}**.
     * @description
     * This is done using the following sequence:
     * - pressing "Control" + "A" to select the whole value;
     * - pressing "Backspace" to delete the value;
     * - (optional) triggering a "change" event by pressing "Enter".
     *
     * @param {Selector} selector
     * @example
     *  run: "clear", // Clears the value of the action element
     * @example
     *  run: "clear input#my_input", // Clears the value of the selector
     */
    async clear(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "clear");
        await hoot.click(element);
        await hoot.clear();
    }

    /**
     * Performs a click sequence on the given **{@link Selector}**
     * @description Let's see more informations about click sequence here: {@link hoot.click}
     * @param {Selector} selector
     * @example
     *  run: "click", // Click on the action element
     * @example
     *  run: "click .o_rows:first", // Click on the selector
     */
    async click(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "click");
        await hoot.click(element);
    }

    /**
     * Performs two click sequences on the given **{@link Selector}**.
     * @description Let's see more informations about click sequence here: {@link hoot.dblclick}
     * @param {Selector} selector
     * @example
     *  run: "dblclick", // Double click on the action element
     * @example
     *  run: "dblclick .o_rows:first", // Double click on the selector
     */
    async dblclick(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "dblclick");
        await hoot.dblclick(element);
    }

    /**
     * Starts a drag sequence on the active element (anchor) and drop it on the given **{@link Selector}**.
     * @param {Selector} selector
     * @param {hoot.PointerOptions} options
     * @example
     *  run: "drag_and_drop .o_rows:first", // Drag the active element and drop it in the selector
     * @example
     *  async run(helpers) {
     *      await helpers.drag_and_drop(".o_rows:first", {
     *          position: {
     *              top: 40,
     *              left: 5,
     *          },
     *          relative: true,
     *      });
     *  }
     */
    async drag_and_drop(selector, options) {
        if (typeof options !== "object") {
            options = { position: "top", relative: true };
        }
        const dragEffectDelay = async () => {
            await new Promise((resolve) => requestAnimationFrame(resolve));
            await new Promise((resolve) => setTimeout(resolve, this.delay));
        };
        const element = this.anchor;
        this._ensureEnabled(element, "drag and drop");
        const { drop, moveTo } = await hoot.drag(element);
        await dragEffectDelay();
        await hoot.hover(element, {
            position: {
                top: 20,
                left: 20,
            },
            relative: true,
        });
        await dragEffectDelay();
        const target = await hoot.waitFor(selector, {
            visible: true,
            timeout: 500,
        });
        await moveTo(target, options);
        await dragEffectDelay();
        await drop();
        await dragEffectDelay();
    }

    /**
     * Edit input or textarea given by **{@link selector}**
     * @param {string} text
     * @param {Selector} selector
     * @example
     *  run: "edit Hello Mr. Doku",
     */
    async edit(text, selector) {
        const element = this._get_action_element(selector);
        await hoot.click(element);
        await hoot.edit(text);
    }

    /**
     * Edit only editable wysiwyg element given by **{@link Selector}**
     * @param {string} text
     * @param {Selector} selector
     */
    async editor(text, selector) {
        const element = this._get_action_element(selector);
        const InEditor = Boolean(element.closest(".odoo-editor-editable"));
        if (!InEditor) {
            throw new Error("run 'editor' always on an element in an editor");
        }
        this._ensureEnabled(element, "edit wysiwyg");
        await hoot.click(element);
        this._set_range(element, "start");
        await hoot.keyDown("_");
        element.textContent = text;
        await hoot.manuallyDispatchProgrammaticEvent(element, "input");
        this._set_range(element, "stop");
        await hoot.keyUp("_");
        await hoot.manuallyDispatchProgrammaticEvent(element, "change");
    }

    /**
     * Fills the **{@link Selector}** with the given `value`.
     * @description This helper is intended for `<input>` and `<textarea>` elements,
     * with the exception of `"checkbox"` and `"radio"` types, which should be
     * selected using the {@link check} helper.
     * In tour, it's mainly usefull for autocomplete components.
     * @param {string} value
     * @param {Selector} selector
     */
    async fill(value, selector) {
        const element = this._get_action_element(selector);
        await hoot.click(element);
        await hoot.fill(value);
    }

    /**
     * Performs a hover sequence on the given **{@link Selector}**.
     * @param {Selector} selector
     * @example
     *  run: "hover",
     */
    async hover(selector) {
        const element = this._get_action_element(selector);
        await hoot.hover(element);
    }

    /**
     * Only for input[type="range"]
     * @param {string|number} value
     * @param {Selector} selector
     */
    async range(value, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "range");
        await hoot.click(element);
        await hoot.setInputRange(element, value);
    }

    /**
     * Performs a keyboard event sequence.
     * @example
     *  run : "press Enter",
     */
    press(...args) {
        return hoot.press(args.flatMap((arg) => typeof arg === "string" && arg.split("+")));
    }

    /**
     * Performs a selection event sequence on **{@link Selector}**. This helper is intended
     * for `<select>` elements only.
     * @description Select the option by its value
     * @param {string} value
     * @param {Selector} selector
     * @example
     * run(helpers) => {
     *  helpers.select("Kevin17", "select#mySelect");
     * },
     * @example
     * run: "select Foden47",
     */
    async select(value, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "select");
        await hoot.click(element);
        await hoot.select(value, { target: element });
    }

    /**
     * Performs a selection event sequence on **{@link Selector}**
     * @description Select the option by its index
     * @param {number} index starts at 0
     * @param {Selector} selector
     * @example
     *  run: "selectByIndex 2", //Select the third option
     */
    async selectByIndex(index, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "selectByIndex");
        await hoot.click(element);
        const value = hoot.queryValue(`option:eq(${index})`, { root: element });
        if (value) {
            await hoot.select(value, { target: element });
            await hoot.manuallyDispatchProgrammaticEvent(element, "input");
        }
    }

    /**
     * Performs a selection event sequence on **{@link Selector}**
     * @description Select option(s) by there labels
     * @param {string|RegExp} contains
     * @param {Selector} selector
     * @example
     *  run: "selectByLabel Jeremy Doku", //Select all options where label contains Jeremy Doku
     */
    async selectByLabel(contains, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "selectByLabel");
        await hoot.click(element);
        const values = hoot.queryAllValues(`option:contains(${contains})`, { root: element });
        await hoot.select(values, { target: element });
    }

    /**
     * Ensures that the given {@link Selector} is unchecked.
     * @description
     * If it is checked, a click is triggered on the input.
     * If the input is still checked after the click, an error is thrown.
     *
     * @param {string|Node} selector
     * @example
     *  run: "uncheck", // Unchecks the action element
     * @example
     *  run: "uncheck input[type=checkbox]", // Unchecks the selector
     */
    uncheck(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "uncheck");
        hoot.uncheck(element);
    }

    /**
     * Navigate to {@link url}.
     *
     * @param {string} url
     * @example
     *  run: "goToUrl /shop", // Go to /shop
     */
    goToUrl(url) {
        const linkEl = document.createElement("a");
        linkEl.href = url;
        linkEl.click();
    }

    /**
     * Get Node for **{@link Selector}**
     * @param {Selector} selector
     * @returns {Node}
     * @default this.anchor
     */
    _get_action_element(selector) {
        if (typeof selector === "string" && selector.length) {
            const nodes = hoot.queryAll(selector);
            return nodes.find(hoot.isVisible) || nodes.at(0);
        } else if (typeof selector === "object" && Boolean(selector?.nodeType)) {
            return selector;
        }
        return this.anchor;
    }

    // Useful for wysiwyg editor.
    _set_range(element, start_or_stop) {
        function _node_length(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return node.nodeValue.length;
            } else {
                return node.childNodes.length;
            }
        }
        const selection = element.ownerDocument.getSelection();
        selection.removeAllRanges();
        const range = new Range();
        let node = element;
        let length = 0;
        if (start_or_stop === "start") {
            while (node.firstChild) {
                node = node.firstChild;
            }
        } else {
            while (node.lastChild) {
                node = node.lastChild;
            }
            length = _node_length(node);
        }
        range.setStart(node, length);
        range.setEnd(node, length);
        selection.addRange(range);
    }

    /**
     * Return true when element is not disabled
     * @param {Node} element
     */
    _ensureEnabled(element, action = "do action") {
        if (element.disabled) {
            throw new Error(
                `Element can't be disabled when you want to ${action} on it.
Tip: You can add the ":enabled" pseudo selector to your selector to wait for the element is enabled.`
            );
        }
    }
}
