/**
 * This is a mini framework designed to make it easy to describe the dynamic
 * content of a "interaction".
 */

let owl = null;
let Markup = null;

export class Colibri {
    compiledFns = new Map();
    frame = null;
    queue = new Set(); // interactions to update next frame

    constructor(env) {
        this.env = env;
    }

     attach(el, I) {
        const interaction = new I(el, this.env, this);
        // patch destroy to cleanup colibri stuff
        const destroy = interaction.destroy;
        interaction.destroy = function () {
            if (!this.isDestroyed) {
                this.__colibri__.cleanup?.();
                for (let [el, ev, fn, options] of this.__colibri__.handlers) {
                    el.removeEventListener(ev, fn, options);
                }
                this.isDestroyed = true;
                destroy.call(this);
            }
        };
        interaction.setup();
        const prom = (interaction.willStart() || Promise.resolve()).then(() => {
            if (interaction.isDestroyed) {
                return;
            }
            const content = I.dynamicContent;
            if (content) {
                this.applyContent(interaction, content);
            }
            interaction.start();
        });
        interaction.__colibri__.startProm = prom;
        return interaction;
    }

    applyContent(interaction, content) {
        let fn;
        if (!this.compiledFns.has(content)) {
            fn = this.compile(content);
            this.compiledFns.set(content, fn);
        } else {
            fn = this.compiledFns.get(content);
        }
        const update = fn(this, interaction);
        interaction.__colibri__.update = update.bind(interaction);
        update.call(interaction);
    }

    compile(content) {
        let nextId = 1;
        let selectors = {}; // sel => variable name
        let attrs = [],
            handlers = [],
            tOuts = [];
        // preprocess content
        for (let [sel, directive, value] of generateEntries(content)) {
            if (!(sel in selectors)) {
                if (sel !== "_root" && sel !== "_body") {
                    selectors[sel] = `nodes_${nextId++}`;
                }
            }
            if (directive.startsWith("t-att-")) {
                attrs.push([sel, directive.slice(6), value]);
            } else if (directive.startsWith("t-on-")) {
                handlers.push([sel, directive.slice(5), value]);
            } else if (directive === "t-out") {
                tOuts.push([sel, value]);
            } else {
                const suffix = directive.startsWith("t-") ? "" : " (should start with t-)"
                throw new Error(`Invalid directive: '${directive}'${suffix}`);
            }
        }
        // generate function code
        let fnStr = "    const root = interaction.el;\n";
        let indent = 1;
        const addLine = (txt) =>
            (fnStr += new Array(indent + 2).join("  ") + txt);
        const applyToSelector = (sel, fn) => {
            if (sel === "_root" || sel === "_body") {
                addLine(`${fn(sel.slice(1))};\n`);
            } else {
                addLine(`for (let node of ${selectors[sel]}) {\n`);
                addLine(`  ${fn("node")}\n`);
                addLine("}\n");
            }
        };
        // nodes
        for (let sel in selectors) {
            addLine(
                `const ${selectors[sel]} = root.querySelectorAll(\`${sel}\`);\n`,
            );
        }

        // start function
        fnStr += "\n";
        for (let [sel, event, expr] of handlers) {
            const nodes = sel === "_root" || sel === "_body" ? `[${sel.slice(1)}]` : selectors[sel];
            addLine(`framework.addDomListener(interaction, ${nodes}, \`${event}\`, interaction[\`${expr}\`]);`)
        }

        // update function
        fnStr += "\n";
        addLine("function update() {\n");
        indent++;
        for (let [sel, attr, expr] of attrs) {
            const varName = `value_${nextId++}`;
            addLine(`const ${varName} = ${expr};\n`);
            applyToSelector(
                sel,
                (el) => `${el}.setAttribute(\`${attr}\`, ${varName});`,
            );
        }
        for (let [sel, expr] of tOuts) {
            const varName = `value_${nextId++}`;
            addLine(`const ${varName} = ${expr};\n`);
            applyToSelector(
                sel,
                (el) => `framework.applyTOut(${el}, ${varName});`,
            );
        }
        indent--;
        addLine("}\n");

        addLine("return update;");
        const fn = new Function("framework", "interaction", fnStr);
        // console.log(fn.toString());
        return fn;
    }

    addDomListener(interaction, nodes, event, fn, options) {
        const handler = ev => {
            fn.call(interaction, ev);
            this.schedule(interaction);
        }
        for (let node of nodes) {
            node.addEventListener(event, handler, options);
            interaction.__colibri__.handlers.push([node, event, handler, options])
        }
    }

    applyTOut(el, value) {
        if (!Markup) {
            owl = odoo.loader.modules.get("@odoo/owl");
            if (owl) {
                Markup = owl.markup("").constructor;
            }
        }
        if (Markup && value instanceof Markup) {
            el.innerHTML = value;
        } else {
            el.textContent = value;
        }
        return this.markup;
    }
    schedule(interaction) {
        this.queue.add(interaction);
        if (!this.frame) {
            this.frame = requestAnimationFrame(() => {
                this.flush();
                this.frame = null;
            });
        }
    }

    flush() {
        for (let interaction of this.queue) {
            if (!interaction.isDestroyed) {
                interaction.__colibri__.update();
            }
        }
        this.queue.clear();
    }
}

function* generateEntries(content) {
    for (let key in content) {
        const value = content[key];
        if (typeof value === "string") {
            const [selector, directive] = key.split(":");
            yield [selector, directive, value];
        } else {
            for (let directive in value) {
                yield [key, directive, value[directive]];
            }
        }
    }
}
