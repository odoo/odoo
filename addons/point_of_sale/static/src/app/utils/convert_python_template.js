import { registerTemplate } from "@web/core/templates";

/**
 * This method allows templates initially intended to be rendered in Python to be converted into
 * templates that can be rendered in JavaScript.
 *
 * Be aware that this method only supports certain Python directives. If an unsupported directive
 * is found, an error will be raised.
 *
 * This can be useful for templates that directly take a data object without records.
 * For example, in PoS, we need to render the order ticket from the backend and frontend. This is
 * overridden in around 30 modules, and we don't want to duplicate the templates.
 *
 * Allowed backend directives:
 * t-if, t-elif, t-else, t-foreach, t-att, t-attf, t-call, t-out, t-set, t-as, t-name, t-value
 *
 * Unsported directives that have no effect (will be ignored if used):
 * t-inner-content, t-consumed-options, t-qweb-skip, t-else-valid, t-translation, t-title, t-ignore
 *
 * Unsupported backend directives (will raise an error if used):
 * t-groups, t-options, t-lang, t-call-assets, t-field, t-value, t-tag-open, t-tag-close
 *
 * @param {string} name
 * @param {string} url
 * @param {string} templateString: Must come from ``self.env['ir.qweb']._get_template()``
 */
export function registerPythonTemplate(name, url, templateString) {
    /**
     * Adds t-key to all t-foreach elements in a template string
     * using the t-as variable as prefix + "_index".
     */
    const addTKeyToForeach = (string) =>
        string.replace(
            /(<[^>]+t-foreach\s*=\s*["'][^"']+["'][^>]*t-as\s*=\s*["']([^"']+)["'][^>]*)(>)/g,
            (match, startTag, tAsVar, closing) => {
                // If t-key already exists, leave it
                if (/t-key\s*=/.test(match)) {
                    return match + closing;
                }
                const tKey = `${tAsVar}_index`;
                return `${startTag} t-key="${tKey}"${closing}`;
            }
        );

    /**
     * Replace .get('key') or .get("key") with ['key'] in a template string
     */
    function replaceDotGet(templateString) {
        return templateString.replace(
            /\.get\(\s*(['"])(.*?)\1\s*\)/g,
            (match, quote, key) => `['${key}']`
        );
    }

    /**
     * Converts Python-style expressions to JavaScript equivalents.
     * Used to pre-process Odoo QWeb-like template expressions before client-side rendering.
     */
    const translatePythonExprToJs = (template) => {
        const replacements = [
            { py: /\band\b/g, js: "&amp;&amp;" },
            { py: /\bor\b/g, js: "||" },
            { py: /\bnot\b/g, js: "!" },
            { py: /\bTrue\b/g, js: "true" },
            { py: /\bFalse\b/g, js: "false" },
            { py: /\bNone\b/g, js: "null" },
        ];

        // Matches t-*="..." or t-*='...' while capturing the directive and expression safely
        return template.replaceAll(
            /\bt-[a-zA-Z0-9_-]+\s*=\s*(["'])([\s\S]*?)\1/g,
            (match, quote, expr) => {
                let translated = expr;
                for (const { py, js } of replacements) {
                    translated = translated.replace(py, js);
                }
                return match.replace(expr, translated);
            }
        );
    };

    /**
     * Build a regex that matches t-directives safely even if the expression contains quotes.
     * Handles: t-out="data['x']" or t-if='user["active"]'
     */
    const buildDirectiveRegex = (directives) =>
        new RegExp(`\\b(${directives.join("|")})\\s*=\\s*(?:"([^"]*)"|'([^']*)')`, "g");

    const extractDirectives = (regex, template) => {
        const matches = [];
        for (const match of template.matchAll(regex)) {
            const [full, directive, expr] = match;
            matches.push({ directive, expr, full });
        }
        return matches;
    };

    /**
     * Replace len() with .length
     * E.g., len(data['items'])  => data['items'].length
     */
    const replaceLenWithLength = (template) =>
        template.replace(/len\(\s*([^)]+)\s*\)/g, (_, innerExpr) => `${innerExpr}.length`);

    const UNSUPPORTED_DIRECTIVES = [
        "t-groups",
        "t-options",
        "t-lang",
        "t-call-assets",
        "t-field",
        "t-tag-open",
        "t-tag-close",
    ];
    const templateWithKeys = addTKeyToForeach(templateString);
    const templateWithLenReplaced = replaceLenWithLength(templateWithKeys);
    const templateWithDotGetReplaced = replaceDotGet(templateWithLenReplaced);
    const translated = translatePythonExprToJs(templateWithDotGetReplaced);
    const UNSUPPORTED_REGEX = buildDirectiveRegex(UNSUPPORTED_DIRECTIVES);
    const unsupportedDirectives = extractDirectives(UNSUPPORTED_REGEX, translated);

    if (unsupportedDirectives.length > 0) {
        console.error("Unsupported directives", unsupportedDirectives);
    }

    return registerTemplate(name, url, translated);
}
