import { init, parse } from "es-module-lexer";
import { createInterface } from "node:readline";

await init;

const rl = createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
    let req;
    try {
        req = JSON.parse(line);
    } catch {
        return;
    }
    const out = { id: req.id };
    try {
        const src = String(req.src ?? "");
        const [imports, exports] = parse(src);
        const names = [];
        let hasDefault = false;
        for (const e of exports) {
            if (e.n === "default") {
                hasDefault = true;
            } else if (e.n) {
                names.push(e.n);
            }
        }
        const starFrom = [];
        const reexportFrom = [];
        const reexports = [];
        const importRecords = [];
        for (const i of imports) {
            if (i.d >= 0 || !i.n) {
                continue;
            }
            const stmt = src.slice(i.ss, i.se);
            if (/^\s*export\b/.test(stmt)) {
                if (/^\s*export\s*\*\s*from\b/.test(stmt)) {
                    starFrom.push(i.n);
                } else {
                    reexportFrom.push(i.n);
                }
                let kind = "named";
                if (/^\s*export\s*\*/.test(stmt)) {
                    kind = "star";
                } else if (/\bdefault\b/.test(stmt)) {
                    kind = "default";
                }
                reexports.push({ n: i.n, kind });
                continue;
            }
            let kind = "named";
            if (/^\s*import\s*\*/.test(stmt)) {
                kind = "star";
            } else if (/^\s*import\s+[\w$]/.test(stmt)) {
                kind = "default";
            } else if (/^\s*import\s*["']/.test(stmt)) {
                kind = "side";
            }
            importRecords.push({ n: i.n, kind });
        }
        out.ok = true;
        out.names = names;
        out.hasDefault = hasDefault;
        out.starFrom = starFrom;
        out.reexportFrom = reexportFrom;
        out.reexports = reexports;
        out.imports = importRecords;
        // Dependency checks also need literal dynamic imports, without
        // confusing source-like text in comments or strings with code.
        out.specifiers = [...new Set(imports.map((i) => i.n).filter(Boolean))];
    } catch (err) {
        out.ok = false;
        out.error = String((err && err.message) || err);
    }
    process.stdout.write(JSON.stringify(out) + "\n");
});
