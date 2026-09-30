export const LANGUAGES = {
    json: "json",
    javascript: "javascript",
    python: "python",
    cURL: "bash",
};

function noQuotesStringify(obj) {
    var json = JSON.stringify(obj, null, 4);
    return json.replace(/^[\t ]*"[^:\n\r]+(?<!\\)":/gm, (m) => m.replace(/"/g, ""));
}

export function createRequestCode({ language, url, requestObj }) {
    if (LANGUAGES[language] === LANGUAGES.json) {

        // Display the domain inline
        const replacer = (key, value) => {
            if (key === "domain" && Array.isArray(value)) {
                return { __inline_json__: JSON.stringify(value) };
            }
            return value;
        };
        let json = JSON.stringify(requestObj, replacer, 4);
        json = json.replace(
            /{\s*"__inline_json__":\s*"(.+?)"\s*}/g,
            (match, p1) => JSON.parse(`"${p1}"`)
        );
        return json;

    } else if (LANGUAGES[language] === LANGUAGES.javascript) {
        const objStr = noQuotesStringify(requestObj).replace(/\n/gm, "\n    ");

        return `\
(async () => {
    // You MUST store this key securely. Place it in an
    // environment variable or in in a file outside of
    // git (e.g. your home directory).
    const apiKey = "YOUR_API_KEY";

    const request = {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + apiKey,
            // "X-Odoo-Database": "...",
        },
        body: JSON.stringify(${objStr}),
    };

    const response = await fetch("${url}", request);
    if (response.ok) {
        const data = await response.json();
        console.log(data)
    } else {
        // Handle errors
    }
})();`;
    } else if (LANGUAGES[language] === LANGUAGES.cURL) {
        const objStr = JSON.stringify(requestObj);

        return `\
curl '${url}'\\
  -X POST \\
  --oauth2-bearer YOUR_API_KEY \\
# -H "X-Odoo-Database: ..." \\
  -H "Content-Type: application/json" \\
  -d '${objStr}'
`;
    } else if (LANGUAGES[language] === LANGUAGES.python) {
        const objStr = JSON.stringify(requestObj, null, 4)
            .replace(/\bnull\b/g, "None")
            .replaceAll("\n", "\n    ")
            .trim();

        return `\
# You MUST store this key securely. Place it in an
# environment variable or in in a file outside of
# git (e.g. your home directory).
api_key = "YOUR_API_KEY"

${"import"} requests
response = requests.post(
    "${url}",
    headers={
        "Authorization": f"Bearer {api_key}",
        # "X-Odoo-Database": "...",
    },
    json=${objStr},
)
response.raise_for_status()
data = response.json()
print(data)
`;
    }
}
