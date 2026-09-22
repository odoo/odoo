"""A TypeScript client rendered from an OpenAPI document.

The point is not to compete with a generator: it is that the document says
enough to write a client from, and that this stays true. What the document
states -- the path and its parameters, the body's schema, the response's,
and which door each operation is -- becomes a typed method; what it does not
state becomes `unknown`, which is honest and which a caller must narrow.
"""

from __future__ import annotations

import json
import re
from typing import Any

HEADER = """// Generated from openapi.json; do not edit.
// Regenerate: ODOO_WRITE_OPENAPI=1 odoo-bin -d <db> --test-enable \\
//     --test-tags /rpc:TestOpenAPIContract.test_the_checked_in_client_is_current
"""

PREAMBLE = """
export interface OdooClientOptions {
    /** Where the server answers, without a trailing slash. */
    baseUrl: string;
    /** A res.users.apikeys key, for a door whose `x-odoo-auth` is bearer. */
    apiKey?: string;
    /** Injected in a test, or to add a proxy; defaults to global fetch. */
    fetch?: typeof fetch;
}

export class OdooApiError extends Error {
    constructor(
        readonly status: number,
        readonly body: unknown,
    ) {
        super(`Odoo answered ${status}`);
        this.name = "OdooApiError";
    }
}

export class OdooClient {
    private readonly baseUrl: string;
    private readonly apiKey?: string;
    private readonly doFetch: typeof fetch;

    constructor(options: OdooClientOptions) {
        this.baseUrl = options.baseUrl.replace(/\\/$/, "");
        this.apiKey = options.apiKey;
        this.doFetch = options.fetch ?? globalThis.fetch;
    }

    private async call<T>(
        method: string,
        path: string,
        body: unknown,
        authenticated: boolean,
    ): Promise<T> {
        const headers: Record<string, string> = {};
        if (body !== undefined) {
            headers["Content-Type"] = "application/json";
        }
        if (authenticated && this.apiKey) {
            headers["Authorization"] = `Bearer ${this.apiKey}`;
        }
        const response = await this.doFetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        const text = await response.text();
        const parsed: unknown = text ? JSON.parse(text) : undefined;
        if (!response.ok) {
            throw new OdooApiError(response.status, parsed);
        }
        return parsed as T;
    }

    private query(pairs: [string, unknown][]): string {
        const given = pairs.filter(([, value]) => value !== undefined);
        if (!given.length) {
            return "";
        }
        const encoded = given.map(
            ([key, value]) =>
                `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
        );
        return `?${encoded.join("&")}`;
    }"""

FOOTER = "}\n"

_PRIMITIVES = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
}

PRINT_WIDTH = 88  # .prettierrc

_IDENTIFIER = re.compile(r"[^0-9a-zA-Z]+")
_JS_NAME = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")


def _camel(name: str) -> str:
    parts = [part for part in _IDENTIFIER.split(name) if part]
    if not parts:
        return "call"
    return parts[0].lower() + "".join(part.title() for part in parts[1:])


def _property(name: str) -> str:
    """Quoted only where it has to be, as the formatter's `quoteProps` is."""
    return name if _JS_NAME.match(name) else json.dumps(name)


def _type_of(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "unknown"
    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])
    if "const" in schema:
        return json.dumps(schema["const"])
    if "oneOf" in schema or "anyOf" in schema:
        options = schema.get("oneOf") or schema["anyOf"]
        return " | ".join(_type_of(option) for option in options) or "unknown"
    declared = schema.get("type")
    if isinstance(declared, list):
        return " | ".join(_PRIMITIVES.get(one, "unknown") for one in declared)
    if declared == "array":
        return f"Array<{_type_of(schema.get('items'))}>"
    if declared == "object":
        properties = schema.get("properties") or {}
        if not properties:
            return "Record<string, unknown>"
        required = set(schema.get("required") or ())
        members = ", ".join(
            f"{_property(name)}{'' if name in required else '?'}: {_type_of(member)}"
            for name, member in sorted(properties.items())
        )
        return "{ " + members + " }"
    return _PRIMITIVES.get(declared, "unknown")


def _body_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    content = (operation.get("requestBody") or {}).get("content") or {}
    for media in ("application/json", "*/*"):
        if media in content:
            return content[media].get("schema")
    return None


def _response_type(operation: dict[str, Any]) -> str:
    responses = operation.get("responses") or {}
    for status in sorted(responses):
        if not status.startswith("2"):
            continue
        content = (responses[status] or {}).get("content") or {}
        for media in ("application/json", "*/*"):
            if media in content:
                return _type_of(content[media].get("schema"))
        return "void"
    return "unknown"


def _path_expression(path: str, parameters: list[dict[str, Any]]) -> str:
    expression = path
    for parameter in parameters:
        if parameter["in"] != "path":
            continue
        name = parameter["name"]
        expression = expression.replace(
            "{" + name + "}", "${encodeURIComponent(String(" + _camel(name) + "))}"
        )
    return f"`{expression}`"


def _query_lines(query_params: list[dict[str, Any]]) -> list[str]:
    """The pairs, given to the client's own encoder, which drops the ones
    the caller left out."""
    pairs = [f"[{json.dumps(p['name'])}, {_camel(p['name'])}]" for p in query_params]
    one_line = f"        const suffix = this.query([{', '.join(pairs)}]);"
    if len(one_line) <= PRINT_WIDTH:
        return [one_line]
    return (
        ["        const suffix = this.query(["]
        + [f"            {pair}," for pair in pairs]
        + ["        ]);"]
    )


def _method(path: str, verb: str, operation: dict[str, Any]) -> str:
    name = _camel(operation.get("operationId") or f"{verb}_{path}")
    parameters = operation.get("parameters") or []
    path_params = [p for p in parameters if p["in"] == "path"]
    query_params = [p for p in parameters if p["in"] == "query"]
    body = _body_schema(operation)
    signature = [
        f"{_camel(p['name'])}: {_type_of(p.get('schema'))}" for p in path_params
    ]
    signature += [
        f"{_camel(p['name'])}{'' if p.get('required') else '?'}: "
        f"{_type_of(p.get('schema'))}"
        for p in query_params
    ]
    if body is not None:
        # A body whose every member is optional is itself optional: the
        # document says nothing must be sent, so the method must not ask.
        optional = "" if body.get("required") else "?"
        signature.append(f"body{optional}: {_type_of(body)}")
    authenticated = any(
        name_ == "bearerAuth"
        for requirement in operation.get("security") or ()
        for name_ in requirement
    )
    door = operation.get("x-odoo-auth", "unspecified")
    lines = [
        "",
        f"    /** {verb.upper()} {path} (auth: {door}) */",
        f"    async {name}({', '.join(signature)}): Promise<{_response_type(operation)}> {{",
    ]
    if query_params:
        lines.append(f"        const path = {_path_expression(path, parameters)};")
        lines.extend(_query_lines(query_params))
        target = "`${path}${suffix}`"
    else:
        target = _path_expression(path, parameters)
    payload = "body" if body is not None else "undefined"
    arguments = [json.dumps(verb.upper()), target, payload, json.dumps(authenticated)]
    lines.extend(_call(arguments))
    lines.append("    }")
    return "\n".join(lines)


def _call(arguments: list[str]) -> list[str]:
    """One line while it fits the printed width, wrapped the way the
    formatter would wrap it once it does not."""
    one_line = f"        return this.call({', '.join(arguments)});"
    if len(one_line) <= PRINT_WIDTH:
        return [one_line]
    return (
        ["        return this.call("]
        + [f"            {argument}," for argument in arguments]
        + ["        );"]
    )


def render_typescript(document: dict[str, Any]) -> str:
    """The document as a client: one method per operation, in path order."""
    info = document.get("info") or {}
    title = info.get("title", "Odoo")
    version = info.get("version", "")
    body = [HEADER, f"// {title} {version}".rstrip(), PREAMBLE]
    for path in sorted(document.get("paths") or {}):
        item = document["paths"][path]
        body.extend(_method(path, verb, item[verb]) for verb in sorted(item))
    body.append(FOOTER)
    return "\n".join(body)
