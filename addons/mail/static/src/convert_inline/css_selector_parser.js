/**
 * Selector level 4 parser for the purposes of specificity computation.
 * @see https://www.w3.org/TR/selectors-4/
 */

const R_CHAR = /[\w-]/;
const R_HEX = /[0-9a-fA-F]/;
const CSS_WHITESPACE = new Set([" ", "\t", "\n", "\r", "\f"]);
const QUOTE_DELIMITER = new Set(["'", '"']);
const COMPUTED_ADD_PSEUDO_CLASSES = new Set(["nth-child", "nth-last-child"]);
const COMPUTED_REPLACE_PSEUDO_CLASSES = new Set(["has", "not", "is"]);
const COMPUTED_PSEUDO_CLASSES = COMPUTED_ADD_PSEUDO_CLASSES.union(COMPUTED_REPLACE_PSEUDO_CLASSES);
const ZEROED_PSEUDO_CLASSES = new Set(["where"]);
const LEGACY_PSEUDO_ELEMENTS = new Set(["before", "after", "first-line", "first-letter"]);

const selectorListCache = new Map();
const selectorSpecificityCache = new Map();

/**
 * @abstract
 */
class Selector extends Array {
    get selector() {
        return this.toString();
    }
    get specificity() {
        return computeSpecificity(this.selector);
    }
    toString() {
        return this.join("");
    }
}

class SelectorList extends Selector {
    toString() {
        return this.join(",");
    }
}

class ComplexSelector extends Selector {}
class CompoundSelector extends Selector {}

class Combinator {
    constructor({ combinator } = {}) {
        this.combinator = combinator;
    }
    toString() {
        return this.combinator;
    }
}

class SimpleSelector {
    constructor({
        prefix = "",
        content = "",
        argument = "",
        suffix = "",
        specificity = [0, 0, 0],
    } = {}) {
        this.prefix = prefix;
        this.suffix = suffix;
        this.content = content;
        this.argument = argument;
        this._argumentPrefix = undefined;
        this._argumentSelector = undefined;
        this._specificity = specificity;
    }
    get selector() {
        return this.toString();
    }
    get hasFixedSpecificity() {
        return Boolean(this._specificity) || !this.argument;
    }
    get argumentTokens() {
        const tokens = { prefix: this._argumentPrefix, selector: this._argumentSelector };
        if (!this.argument || !COMPUTED_PSEUDO_CLASSES.has(this.content)) {
            return tokens;
        } else if (
            COMPUTED_REPLACE_PSEUDO_CLASSES.has(this.content) &&
            tokens.selector === undefined
        ) {
            this._argumentSelector = this.argument;
        } else if (COMPUTED_ADD_PSEUDO_CLASSES.has(this.content) && tokens.prefix === undefined) {
            ({ prefix: this._argumentPrefix, selector: this._argumentSelector } =
                parseNthChildArgument(this.argument));
        } else {
            return tokens;
        }
        return { prefix: this._argumentPrefix, selector: this._argumentSelector };
    }
    get argumentPrefix() {
        return this.argumentTokens.prefix;
    }
    get argumentSelector() {
        return this.argumentTokens.selector;
    }
    set specificity(value) {
        this._specificity = value;
    }
    get specificity() {
        let specificity = this._specificity;
        if (!this.hasFixedSpecificity) {
            try {
                specificity = [0, 0, 0];
                if (COMPUTED_ADD_PSEUDO_CLASSES.has(this.content)) {
                    specificity = sumSpecificities(specificity, [0, 1, 0]);
                }
                const argumentSelector = this.argumentSelector;
                if (argumentSelector) {
                    specificity = sumSpecificities(
                        specificity,
                        computeSpecificity(argumentSelector)
                    );
                }
            } catch {
                // ignore invalid argument for the specificity computation
            }
        }
        return [...(specificity || [0, 0, 0])];
    }
    toString() {
        return `${this.prefix}${this.content}${this.argument ? `(${this.argument})` : ""}${
            this.suffix
        }`;
    }
}

/**
 * @see https://www.w3.org/TR/selectors-4/#specificity
 *
 * @param {string} selector
 * @returns {Array<number>} [A, B, C]
 */
function computeSpecificity(selector) {
    selector = selector.trim();
    if (selectorSpecificityCache.has(selector)) {
        return selectorSpecificityCache.get(selector);
    }
    const selectorList = parseSelector(selector);
    const specificities = [];
    for (const complexSelector of selectorList) {
        let specificity = [0, 0, 0];
        for (const compoundSelector of complexSelector.filter(
            (s) => s instanceof CompoundSelector
        )) {
            for (const simpleSelector of compoundSelector) {
                specificity = sumSpecificities(specificity, simpleSelector.specificity);
            }
        }
        specificities.push(specificity);
    }
    specificities.sort((a, b) => {
        for (let i = 0; i < 3; i++) {
            const diff = a[i] - b[i];
            if (diff !== 0) {
                return diff;
            }
        }
        return 0;
    });
    selectorSpecificityCache.set(selector, specificities.at(-1));
    return selectorSpecificityCache.get(selector);
}

function consumeEscaped(text, i) {
    const current = text[i];
    const next = text[i + 1];
    if (current !== "\\" || !next) {
        return { escaped: current, lastIndexConsumed: i }; // no escape
    } else if (next === "\r" && text[i + 2] === "\n") {
        return { escaped: "", lastIndexConsumed: i + 2 }; // line continuation
    } else if (next === "\n" || next === "\r" || next === "\f") {
        return { escaped: "", lastIndexConsumed: i + 1 }; // line continuation
    } else if (R_HEX.test(next)) {
        // hex escape
        let hex = next;
        let j = i + 2;
        while (text[j] && hex.length < 6 && R_HEX.test(text[j])) {
            hex += text[j++];
        }
        if (CSS_WHITESPACE.has(text[j])) {
            if (text[j] === "\r" && text[j + 1] === "\n") {
                hex += text[j++];
            }
            hex += text[j++];
        }
        return { escaped: current + hex, lastIndexConsumed: j - 1 };
    }
    return { escaped: current + next, lastIndexConsumed: i + 1 }; // simple escape
}

function isChar(char) {
    return Boolean(char) && R_CHAR.test(char);
}

function sumSpecificities(s1, s2) {
    const specificity = [0, 0, 0];
    for (const s of [s1, s2]) {
        s.forEach((v, i) => (specificity[i] += v));
    }
    return specificity;
}

/**
 * Parse a nth-child or nth-last-child argument to isolate the potential
 * selectorList after the optional `of`.
 *
 * @param {string} argument
 * @returns {Object} { prefix: {string}, selector: {string} }
 *   prefix the irrelevant string part for specificity computation
 *   selector is the selectorList string after `of`.
 */
function parseNthChildArgument(argument) {
    const tokens = { prefix: "", selector: undefined };
    loopArgument: for (let i = 0; i < argument.length; i++) {
        const char = argument[i];
        let escaped = undefined;
        switch (char) {
            case "\\": {
                ({ escaped, lastIndexConsumed: i } = consumeEscaped(argument, i));
                break;
            }
            case "[":
            case "(":
            case "'":
            case '"': {
                tokens.prefix = argument;
                break loopArgument;
            }
            case "O":
            case "o": {
                if (argument.slice(i, i + 2).toLowerCase() === "of") {
                    const before = argument[i - 1];
                    const after = argument[i + 2];
                    if (CSS_WHITESPACE.has(before) && after) {
                        const selector = argument.slice(i + 2).trim();
                        if (selector) {
                            tokens.prefix = `${argument.slice(0, i - 1).trim()} of `;
                            tokens.selector = selector;
                            break loopArgument;
                        }
                    }
                }
                break;
            }
        }
        tokens.prefix += escaped ?? argument[i];
    }
    return tokens;
}

/**
 * Parses a given selector string into a @see SelectorList .
 *
 * - returns an Array of @see ComplexSelector objects (implicit `,` separation)
 * - a ComplexSelector is composed of one or more @see CompoundSelector objects
 *   separated by @see Combinator [" ", "~", ">", "+"] objects
 * - a CompoundSelector is composed of one or more @see SimpleSelector objects
 *   which are weighted according to the specificity algorithm.
 * @see https://www.w3.org/TR/selectors-4/
 *
 * @param {string} selector
 * @returns {SelectorList}
 */
export function parseSelector(selector) {
    selector = selector.trim();
    if (selectorListCache.has(selector)) {
        return selectorListCache.get(selector);
    }

    const firstCompound = new CompoundSelector();
    const firstComplex = new ComplexSelector(firstCompound);
    const selectorList = new SelectorList(firstComplex);
    const parens = [0, 0]; // parentheses [opening, closing]

    let currentComplex = selectorList.at(-1);
    let currentCompound = currentComplex.at(-1);
    let currentSimple = null;
    let currentPseudo = null;
    let currentQuote = null;
    let currentSpace = false;
    let pendingSpace = false;
    let registerChar = true;

    const addCombinator = (combinator) => {
        if (currentCompound.length === 0) {
            // Handle relative selectors (starting with a combinator)
            currentComplex.pop();
        }
        currentComplex.push(combinator);
        currentComplex.push(new CompoundSelector());
        currentCompound = currentComplex.at(-1);
        currentSimple = null;
    };

    const addSimple = (simpleSelector) => {
        if (pendingSpace && currentCompound.length > 0) {
            pendingSpace = false;
            addCombinator(new Combinator({ combinator: " " }));
        }
        currentSimple = simpleSelector;
        currentCompound.push(currentSimple);
    };

    for (let i = 0; i < selector.length; i++) {
        currentSpace = false;
        const char = selector[i];
        let escaped = undefined;
        registerChar = true;
        switch (char) {
            // Escaped sequence
            case "\\": {
                ({ escaped, lastIndexConsumed: i } = consumeEscaped(selector, i));
                break;
            }
            // Group separator (comma)
            case ",": {
                if (!currentQuote && !currentPseudo) {
                    selectorList.push(new ComplexSelector(new CompoundSelector()));
                    currentComplex = selectorList.at(-1);
                    currentCompound = currentComplex.at(-1);
                    currentSimple = null;
                    registerChar = false;
                }
                break;
            }
            // Part separator (Combinators)
            case ">":
            case "+":
            case "~": {
                if (!currentQuote && !currentPseudo) {
                    addCombinator(new Combinator({ combinator: char }));
                    while (CSS_WHITESPACE.has(selector[i + 1])) {
                        i++;
                    }
                    registerChar = false;
                }
                break;
            }
            // Space (combinator or filler)
            case " ":
            case "\t":
            case "\n":
            case "\r":
            case "\f": {
                if (!currentQuote && !currentPseudo) {
                    // Space combinator may be added during the next addSimple
                    currentSpace = true;
                    registerChar = false;
                }
                break;
            }
            // Quote delimiters
            case `'`:
            case `"`: {
                if (char === currentQuote) {
                    currentQuote = null;
                } else if (!currentQuote) {
                    currentQuote = char;
                }
                break;
            }
            // ID
            case "#": {
                if (!currentQuote && !currentPseudo) {
                    addSimple(new SimpleSelector({ prefix: "#", specificity: [1, 0, 0] }));
                    registerChar = false;
                }
                break;
            }
            // Class
            case ".": {
                if (!currentQuote && !currentPseudo) {
                    addSimple(new SimpleSelector({ prefix: ".", specificity: [0, 1, 0] }));
                    registerChar = false;
                }
                break;
            }
            case "*": {
                if (!currentQuote && !currentPseudo) {
                    addSimple(new SimpleSelector());
                }
                break;
            }
            // Attribute
            case "[": {
                if (!currentQuote && !currentPseudo) {
                    addSimple(
                        new SimpleSelector({ prefix: "[", suffix: "]", specificity: [0, 1, 0] })
                    );
                    // The attribute expression is not parsed because it does
                    // not impact the specificity, it is aggregated in content:
                    // attributeName [operator value]
                    let attrQuote = null;
                    while (selector[i + 1] && (attrQuote || selector[i + 1] !== "]")) {
                        const attrChar = selector[i + 1];
                        if (attrChar === "\\") {
                            let content;
                            ({ escaped: content, lastIndexConsumed: i } = consumeEscaped(
                                selector,
                                i + 1
                            ));
                            currentSimple.content += content;
                            continue;
                        }
                        if (QUOTE_DELIMITER.has(attrChar)) {
                            if (attrChar === attrQuote) {
                                attrQuote = null;
                            } else if (!attrQuote) {
                                attrQuote = attrChar;
                            }
                        }
                        currentSimple.content += selector[++i];
                    }
                    i++; // account for the `]` character
                    registerChar = false;
                }
                break;
            }
            // Pseudo classes (:) and elements (::)
            case ":": {
                if (!currentQuote && !currentPseudo) {
                    addSimple(new SimpleSelector({ prefix: ":" }));
                    if (selector[i + 1] === ":") {
                        i++;
                        currentSimple.prefix = "::";
                    }
                    while (isChar(selector[i + 1])) {
                        currentSimple.content += selector[++i];
                    }
                    if (LEGACY_PSEUDO_ELEMENTS.has(currentSimple.content)) {
                        currentSimple.prefix = "::";
                    }
                    if (currentSimple.prefix === "::") {
                        currentSimple.specificity = [0, 0, 1];
                    } else if (COMPUTED_PSEUDO_CLASSES.has(currentSimple.content)) {
                        // Specificity must be computed from the pseudo-class selector argument.
                        currentSimple.specificity = undefined;
                    } else if (!ZEROED_PSEUDO_CLASSES.has(currentSimple.content)) {
                        currentSimple.specificity = [0, 1, 0];
                    }
                    if (selector[i + 1] === "(") {
                        parens[0]++;
                        i++;
                        registerChar = false;
                    }
                    currentPseudo = currentSimple;
                }
                break;
            }
            // Parentheses
            case "(": {
                if (!currentQuote) {
                    parens[0]++;
                }
                break;
            }
            case ")": {
                if (!currentQuote) {
                    parens[1]++;
                }
                break;
            }
        }

        if (currentPseudo) {
            if (parens[0] === parens[1]) {
                currentPseudo = null;
            } else if (registerChar) {
                currentPseudo.argument += escaped ?? selector[i];
            }
        } else if (registerChar) {
            if (!currentSimple || (pendingSpace && currentCompound.length > 0)) {
                // Type selector (e.g. "p", "h1", "td")
                addSimple(new SimpleSelector({ specificity: [0, 0, 1] }));
            }
            currentSimple.content += escaped ?? selector[i];
        }
        pendingSpace = currentSpace;
    }

    selectorListCache.set(selector, selectorList);
    return selectorList;
}
