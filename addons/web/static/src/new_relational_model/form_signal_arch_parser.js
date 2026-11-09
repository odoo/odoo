import { getActiveActions } from "@web/views/utils";

/**
 * @typedef {{ type: "field"; name: string; string: string | null; invisible: string | null; readonly: string | null; nolabel: boolean }} FieldNode
 * @typedef {{ type: "group"; string: string | null; invisible: string | null; children: ArchNode[] }} GroupNode
 * @typedef {{ type: "notebook"; invisible: string | null; pages: { string: string; invisible: string | null; children: ArchNode[] }[] }} NotebookNode
 * @typedef {{ type: "separator"; string: string | null; invisible: string | null }} SeparatorNode
 * @typedef {{ type: "label"; for: string; string: string | null; invisible: string | null }} LabelNode
 * @typedef {{ type: "sheet"; invisible: string | null; children: ArchNode[] }} SheetNode
 * @typedef {{ type: "element"; tag: string; className: string; invisible: string | null; children: ArchNode[] }} ElementNode
 * @typedef {{ type: "text"; value: string; invisible: null }} TextNode
 * @typedef {FieldNode | GroupNode | NotebookNode | SeparatorNode | LabelNode | SheetNode | ElementNode | TextNode} ArchNode
 *
 * @typedef {{
 *  activeActions: ReturnType<typeof getActiveActions>;
 *  header: ArchNode[];
 *  body: ArchNode[];
 *  fieldNames: string[];
 * }} FormSignalArchInfo
 */

/** elements not supported yet: they are not rendered */
const SKIPPED_TAGS = new Set(["button", "widget", "chatter", "footer", "newline"]);

/**
 * Turns the form arch into a tree of plain nodes (see {@link ArchNode}) that
 * the renderer walks, and collects the names of the fields to load.
 *
 * Modifiers (`invisible`, `readonly`) are kept as python expressions, the
 * renderer evaluates them against the record.
 *
 * The content of x2many fields (their sub views) is ignored, and so are
 * buttons, widgets and the chatter.
 */
export class FormSignalArchParser {
    /**
     * @param {Element} arch
     * @returns {FormSignalArchInfo}
     */
    parse(arch) {
        // always loaded, for the breadcrumbs
        const fieldNames = new Set(["display_name"]);

        /**
         * @param {Node} node
         * @returns {ArchNode | null}
         */
        const parseNode = (node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                const value = node.textContent.trim();
                return value ? { type: "text", value, invisible: null } : null;
            }
            if (node.nodeType !== Node.ELEMENT_NODE) {
                return null;
            }
            const el = /** @type {Element} */ (node);
            const tag = el.tagName;
            const invisible = el.getAttribute("invisible");
            if (SKIPPED_TAGS.has(tag) || el.getAttribute("name") === "button_box") {
                return null;
            }
            switch (tag) {
                case "field": {
                    const name = el.getAttribute("name");
                    if (name === "id") {
                        // the store exposes it as `record.id`, not as a field
                        return null;
                    }
                    fieldNames.add(name);
                    return {
                        type: "field",
                        name,
                        string: el.getAttribute("string"),
                        invisible,
                        readonly: el.getAttribute("readonly"),
                        nolabel: el.getAttribute("nolabel") === "1",
                    };
                }
                case "sheet":
                    return { type: "sheet", invisible, children: parseChildren(el) };
                case "group":
                    return {
                        type: "group",
                        string: el.getAttribute("string"),
                        invisible,
                        children: parseChildren(el),
                    };
                case "notebook":
                    return {
                        type: "notebook",
                        invisible,
                        pages: [...el.children]
                            .filter((page) => page.tagName === "page")
                            .map((page) => ({
                                string: page.getAttribute("string") || "",
                                invisible: page.getAttribute("invisible"),
                                children: parseChildren(page),
                            })),
                    };
                case "separator":
                    return { type: "separator", string: el.getAttribute("string"), invisible };
                case "label":
                    return {
                        type: "label",
                        for: el.getAttribute("for"),
                        string: el.getAttribute("string"),
                        invisible,
                    };
                default:
                    // div, h1, span...: rendered as is
                    return {
                        type: "element",
                        tag,
                        className: el.getAttribute("class") || "",
                        invisible,
                        children: parseChildren(el),
                    };
            }
        };

        /**
         * @param {Element} el
         * @returns {ArchNode[]}
         */
        const parseChildren = (el) => [...el.childNodes].map(parseNode).filter(Boolean);

        const header = arch.querySelector(":scope > header");
        const body = [...arch.childNodes].filter((node) => node !== header);
        return {
            activeActions: getActiveActions(arch),
            header: header ? parseChildren(header) : [],
            body: body.map(parseNode).filter(Boolean),
            fieldNames: [...fieldNames],
        };
    }
}
