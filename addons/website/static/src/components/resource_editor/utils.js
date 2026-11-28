import { _t } from "@web/core/l10n/translation";

const MAPPING = {
    "{": "}",
    "}": "{",
    "(": ")",
    ")": "(",
    "[": "]",
    "]": "[",
};
const OPENINGS = ["{", "(", "["];
const CLOSINGS = ["}", ")", "]"];

/**
 * Checks the syntax validity of some SCSS.
 *
 * @param {string} scss
 * @returns {Object} object with keys "isValid" and "error" if not valid
 */
export function checkSCSS(scss) {
    const stack = [];
    let line = 1;
    for (let i = 0; i < scss.length; i++) {
        if (OPENINGS.includes(scss[i])) {
            stack.push(scss[i]);
        } else if (CLOSINGS.includes(scss[i])) {
            if (stack.pop() !== MAPPING[scss[i]]) {
                return {
                    isValid: false,
                    error: {
                        line,
                        message: _t("Unexpected %(char)s", { char: scss[i] }),
                    },
                };
            }
        } else if (scss[i] === "\n") {
            line++;
        }
    }
    if (stack.length > 0) {
        return {
            isValid: false,
            error: {
                line,
                message: _t("Expected %(char)s", { char: MAPPING[stack.pop()] }),
            },
        };
    }
    return { isValid: true };
}

/**
 * Checks the syntax validity of some XML.
 *
 * @param {string} xml
 * @returns {Object} object with keys "isValid" and "error" if not valid
 */
export function checkXML(xml) {
    const xmlDoc = new window.DOMParser().parseFromString(xml, "text/xml");
    const errorEls = xmlDoc.getElementsByTagName("parsererror");
    if (errorEls.length > 0) {
        const errorEl = errorEls[0];
        const sourceTextEls = errorEl.querySelectorAll("sourcetext");
        let codeEls = null;
        if (sourceTextEls.length) {
            codeEls = [...sourceTextEls].map((el) => {
                const codeEl = document.createElement("code");
                codeEl.textContent = el.textContent;
                const brEl = document.createElement("br");
                brEl.classList.add("o_we_source_text_origin");
                el.parentElement.insertBefore(brEl, el);
                return codeEl;
            });
            for (const el of sourceTextEls) {
                el.remove();
            }
        }
        for (const el of [...errorEl.querySelectorAll(":not(code):not(pre):not(br)")]) {
            const pEl = document.createElement("p");
            for (const cEl of [...el.childNodes]) {
                pEl.appendChild(cEl);
            }
            el.parentElement.insertBefore(pEl, el);
            el.remove();
        }
        errorEl.querySelectorAll(".o_we_source_text_origin").forEach((el, i) => {
            el.after(codeEls[i]);
        });
        return {
            isValid: false,
            error: {
                line: parseInt(errorEl.innerHTML.match(/[Ll]ine[^\d]+(\d+)/)[1], 10),
                message: errorEl.textContent,
            },
        };
    }
    return { isValid: true };
}

/**
 * Formats some XML so that it has proper indentation and structure.
 *
 * @param {string} xml
 * @returns {string} formatted xml
 */
export function formatXML(xml) {
    // do nothing if an inline script is present to avoid breaking it
    if (/<script(?: [^>]*)?>[^<][\s\S]*<\/script>/i.test(xml)) {
        return xml;
    }
    return window.vkbeautify.xml(xml, 4);
}

/**
 * Parses the arch of a view. Returns the root of the parsed view and the list
 * of operations in it (if any).
 *
 * @param {{arch: string, inherit_id: Array|false}} view
 * @returns {{root: Element, operations: Element[]|null}|null} `operations` are
 *  the operations of the arch of a view with an `inherit_id` (its "xpath"
 *  elements and the elements located by tag name and attributes), null for a
 *  view without an `inherit_id`. Null if the arch is not well-formed.
 */
export function parseTargetArch(view) {
    const doc = new window.DOMParser().parseFromString(view.arch, "text/xml");
    if (doc.getElementsByTagName("parsererror").length) {
        return null;
    }
    const root = doc.documentElement;
    if (!view.inherit_id) {
        return { root, operations: null };
    }
    return { root, operations: root.tagName === "data" ? [...root.children] : [root] };
}

/**
 * Evaluate the expression of an "xpath" operation.
 *
 * The operation supports `hasclass`. Returns an array of items.
 *
 * @param {Element} root
 * @param {string} expr
 * @returns {Node[]}
 */
function evaluateXpath(root, expr) {
    // XPath does not have the hasclass function (it is defined server-side).
    // Replace it with an equivalent condition (see `getXpath` in
    // template_inheritance.js).
    const xpath = expr.replaceAll(/hasclass\(([^)]*)\)/g, (_, classes) =>
        classes
            .split(",")
            .map((c) => `contains(concat(' ', @class, ' '), ' ${c.trim().slice(1, -1)} ')`)
            .join(" and ")
    );
    let result;
    try {
        result = root.ownerDocument.evaluate(
            xpath,
            root,
            null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE
        );
    } catch {
        return [];
    }
    // Pack the `result.snapshotLength` items of `result` into an array.
    return Array.from({ length: result.snapshotLength }, (_, i) => result.snapshotItem(i));
}

/**
 * Tells whether an element is part of the template.
 *
 * Returns false if the element describes an operation, true if it is a real
 * part of the template. Used to ignore the elements that are not part of the
 * template when looking for a target. For example, when looking for the
 * target of `//header`, it prevents a match on `<header position="attributes">`,
 * which describes an operation and is not part of the template.
 *
 * @param {Element} element
 * @param {Element[]|null} operations the operations of the arch, or null if
 *  it is the arch of a view without an `inherit_id`
 */
function isTemplateElement(element, operations) {
    if (!operations) {
        return true;
    }
    const operation = operations.find((op) => op !== element && op.contains(element));
    if (!operation || (operation.getAttribute("position") || "inside") === "attributes") {
        // The element is not inside an operation: it is an operation (for
        // example `<header position="attributes">`) or the "data" root. Or
        // the element is inside a position="attributes" operation: it is an
        // "attribute" instruction.
        return false;
    }
    // An element with position="move" inside an operation is an instruction.
    return !element.closest("[position='move']");
}

// Each ancestor arch is searched alone. The arch that results from the whole
// inheritance is not computed: the other ancestors and the views out of the
// ancestor line can change it. Absolute paths and positions depend on that
// arch, thus they cannot be located reliably.
const UNRELIABLE_EXPR_REGEX = /^\/(?!\/)|\[\s*\d+\s*\]|position\(\)|last\(\)/;

/**
 * Finds the target of an operation in an arch, as the first matching element
 * that is part of the template. The server looks for the target in the arch
 * that results from the whole inheritance. This function looks only in one
 * arch, thus it is a best effort.
 *
 * @param {Element} root the root element of the arch
 * @param {Element[]|null} operations the operations of the arch, or null if
 *  it is the arch of a view without an `inherit_id`
 * @param {Element} operation
 * @returns {Element|null}
 */
export function findOperationTarget(root, operations, operation) {
    let candidates;
    if (operation.tagName === "xpath") {
        const expr = operation.getAttribute("expr");
        if (!expr || UNRELIABLE_EXPR_REGEX.test(expr)) {
            return null;
        }
        candidates = evaluateXpath(root, expr);
    } else {
        const attributes = [...operation.attributes].filter(({ name }) => name !== "position");
        candidates = [root, ...root.getElementsByTagName(operation.tagName)].filter(
            (el) =>
                el.tagName === operation.tagName &&
                attributes.every(({ name, value }) => el.getAttribute(name) === value)
        );
    }
    return (
        candidates.find(
            (node) => node.nodeType === Node.ELEMENT_NODE && isTemplateElement(node, operations)
        ) || null
    );
}

// Matches opening tags and captures their name. Also matches the markup that
// can look like an opening tag (comments, CDATA sections, processing
// instructions, doctypes and closing tags) so that it is not counted. Quoted
// attribute values can contain ">".
const MARKUP_REGEX =
    /<!--[\s\S]*?-->|<!\[CDATA\[[\s\S]*?\]\]>|<[?!][^>]*>|<\/[^>]*>|<([^\s/>]+)(?:"[^"]*"|'[^']*'|[^"'>])*>/g;

/**
 * Finds the row where the opening tag of elements of an arch ends. Each
 * element is matched to its opening tag in the arch text through its
 * occurrence index among the elements sharing its tag name: in document
 * order, elements follow the order of their opening tags in the source.
 *
 * @param {string} arch
 * @param {Element} root the root element of the parsed arch
 * @param {(Element|null)[]} elements elements of the parsed arch
 * @returns {(number|null)[]} for each element, the 0-based row (null if the
 *  element is null or its opening tag is not found)
 */
export function getElementRows(arch, root, elements) {
    const openingTags = [...arch.matchAll(MARKUP_REGEX)].filter((match) => match[1]);
    return elements.map((element) => {
        if (!element) {
            return null;
        }
        const sameTagElements = [...root.getElementsByTagName(element.tagName)];
        if (root.tagName === element.tagName) {
            sameTagElements.unshift(root);
        }
        const occurrenceIndex = sameTagElements.indexOf(element);
        const openingTag = openingTags.filter((match) => match[1] === element.tagName)[
            occurrenceIndex
        ];
        if (!openingTag) {
            return null;
        }
        const end = openingTag.index + openingTag[0].length;
        // Get the 0-based row of `end`.
        return arch.slice(0, end).split(/\r\n|\r|\n/).length - 1;
    });
}

/**
 * Locates the targets of operations in the arch of a view, as the row where
 * the opening tag of each target ends (see `getElementRows`). The target is
 * resolved with `findOperationTarget`.
 *
 * @param {{arch: string, inherit_id: Array|false}} view
 * @param {Element[]} operations the operations to locate (from other views)
 * @returns {(number|null)[]|null} for each operation, the 0-based row of the
 *  end of its target's opening tag (null if it has no target), or null if
 *  the arch is not well-formed (e.g. while it is being typed)
 */
export function getOperationTargetRows(view, operations) {
    const parsed = parseTargetArch(view);
    if (!parsed) {
        return null;
    }
    const targets = operations.map((operation) =>
        findOperationTarget(parsed.root, parsed.operations, operation)
    );
    return getElementRows(view.arch, parsed.root, targets);
}

/**
 * @param {{arch: string, inherit_id: Array|false}} view
 * @returns {number[]|null} the 0-based row where the opening tag of each of
 *  its operations ends (see `parseTargetArch`), an empty array for a view
 *  without an `inherit_id` (it has no operations), or null if the arch is not
 *  well-formed
 */
export function getOperationRows(view) {
    const parsed = parseTargetArch(view);
    return parsed && getElementRows(view.arch, parsed.root, parsed.operations || []);
}
