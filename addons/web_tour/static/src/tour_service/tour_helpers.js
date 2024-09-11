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
    check(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "check");
        this._ensureElementIsInModal(element, "check");
        hoot.check(element);
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
    clear(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "clear");
        this._ensureElementIsInModal(element, "clear");
        hoot.click(element);
        hoot.clear();
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
    click(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "click");
        this._ensureElementIsInModal(element, "click");
        hoot.click(element);
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
    dblclick(selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "dblclick");
        this._ensureElementIsInModal(element, "dblclick");
        hoot.dblclick(element);
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
        const { drop, moveTo } = hoot.drag(element);
        await dragEffectDelay();
        hoot.hover(element, {
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
        moveTo(target, options);
        await dragEffectDelay();
        drop();
        await dragEffectDelay();
    }

    /**
     * Edit input or textarea given by **{@link selector}**
     * @param {string} text
     * @param {Selector} selector
     * @example
     *  run: "edit Hello Mr. Doku",
     */
    edit(text, selector) {
        const element = this._get_action_element(selector);
        this._ensureElementIsInModal(element, "edit");
        hoot.click(element);
        hoot.edit(text);
    }

    /**
     * Edit only editable wysiwyg element given by **{@link Selector}**
     * @param {string} text
     * @param {Selector} selector
     */
    editor(text, selector) {
        const element = this._get_action_element(selector);
        this._ensureElementIsInModal(element, "editor");
        const InEditor = !!element.closest(".odoo-editor-editable");
        if (!InEditor) {
            throw new Error("run 'editor' always on an element in an editor");
        }
        this._ensureEnabled(element, "edit wysiwyg");
        hoot.click(element);
        this._set_range(element, "start");
        hoot.keyDown("_");
        element.textContent = text;
        hoot.manuallyDispatchProgrammaticEvent(element, "input");
        this._set_range(element, "stop");
        hoot.keyUp("_");
        hoot.manuallyDispatchProgrammaticEvent(element, "change");
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
    fill(value, selector) {
        const element = this._get_action_element(selector);
        this._ensureElementIsInModal(element, "fill");
        hoot.click(element);
        hoot.fill(value);
    }

    /**
     * Performs a hover sequence on the given **{@link Selector}**.
     * @param {Selector} selector
     * @example
     *  run: "hover",
     */
    hover(selector) {
        const element = this._get_action_element(selector);
        this._ensureElementIsInModal(element, "hover");
        hoot.hover(element);
    }

    /**
     * Only for input[type="range"]
     * @param {string|number} value
     * @param {Selector} selector
     */
    range(value, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "range");
        this._ensureElementIsInModal(element, "range");
        hoot.click(element);
        hoot.setInputRange(element, value);
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
    select(value, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "select");
        this._ensureElementIsInModal(element, "select");
        hoot.click(element);
        hoot.select(value, { target: element });
    }

    /**
     * Performs a selection event sequence on **{@link Selector}**
     * @description Select the option by its index
     * @param {number} index starts at 0
     * @param {Selector} selector
     * @example
     *  run: "selectByIndex 2", //Select the third option
     */
    selectByIndex(index, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "selectByIndex");
        this._ensureElementIsInModal(element, "selectByIndex");
        hoot.click(element);
        const value = hoot.queryValue(`option:eq(${index})`, { root: element });
        if (value) {
            hoot.select(value, { target: element });
            element.dispatchEvent(new Event("input"));
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
    selectByLabel(contains, selector) {
        const element = this._get_action_element(selector);
        this._ensureEnabled(element, "selectByLabel");
        this._ensureElementIsInModal(element, "selectByLabel");
        hoot.click(element);
        const values = hoot.queryAllValues(`option:contains(${contains})`, { root: element });
        hoot.select(values, { target: element });
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
        } else if (selector instanceof Node) {
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
     * Throw an error when element is disabled
     * @param {Node} element
     */
    _ensureEnabled(element, action = "an action") {
        if (element.disabled) {
            throw new Error(
                `TourHelpers: Element can't be disabled when you want to run **${action}** on it.
TIP: You can use the pseudo selector **:enabled** to your selector to wait for the element is enabled.`
            );
        }
    }

    /**
     * Throw an error when element is below a modal or not in backdrop
     * @param {Node} element
     */
    _ensureElementIsInModal(element, action = "an action") {
        const root = hoot.queryFirst(".modal:not(.o_inactive_modal)");
        if (root && !root.contains(element)) {
            throw new Error(
                `TourHelpers: It is forbidden to run **${action}** on an element that is not in the active modal.
TIP: When a modal is closed in a tour, create a step that ensure it is really closed, e.g. { trigger: "body:not(:has(.modal:contains(my title)))" }.
TIP: To only check if an element is in DOM without doing an action on it, create a step without run key.`
            );
        }
    }
}
