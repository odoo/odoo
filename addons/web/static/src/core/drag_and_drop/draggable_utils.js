/**
 * @typedef {{
 *  color?: string;
 *  label?: string;
 *  once?: boolean;
 * }} DebugItemOptions
 */

/**
 * Transforms a camelCased string to return its kebab-cased version.
 * Typically used to generate CSS properties from JS objects.
 *
 * @param {string} str
 * @returns {string}
 */
function camelToKebab(str) {
    return str.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase();
}

const R_BANG = /\s*!\s*/;

/**
 * @param {HTMLElement} element
 * @param {Iterable<[string, string | number]>} styleEntries
 */
export function setStyleFromEntries(element, styleEntries) {
    for (const [property, valueAndPriority] of styleEntries) {
        const [value, priority] = String(valueAndPriority).split(R_BANG);
        element.style.setProperty(camelToKebab(property), value, priority);
    }
}

export class AttributeManager {
    /** @type {WeakMap<HTMLElement, [string, string][]>} */
    cache = new WeakMap();

    /**
     * @param {HTMLElement} element
     */
    restore(element) {
        if (!this.cache.has(element)) {
            return;
        }
        const attributeCache = this.cache.get(element);
        for (const attributeName of element.getAttributeNames()) {
            if (attributeName in attributeCache) {
                element.setAttribute(attributeName, attributeCache[attributeName]);
                delete attributeCache[attributeName];
            } else {
                element.removeAttribute(attributeName);
            }
        }
        for (const [attribute, value] of Object.entries(attributeCache)) {
            element.setAttribute(attribute, value);
        }
        this.cache.delete(element);
    }

    /**
     * @param {HTMLElement} element
     */
    save(element) {
        if (this.cache.has(element)) {
            return;
        }
        const attributeCache = Object.create(null);
        for (const { name, value } of element.attributes) {
            attributeCache[name] = value;
        }
        this.cache.set(element, attributeCache);
        return this.restore.bind(this, element);
    }
}

export class DraggableDebugManager {
    /**
     * @param {{
     *  color?: string;
     * }} [params]
     */
    constructor(params) {
        this.canvas = document.createElement("canvas");
        Object.assign(this.canvas.style, {
            width: "100vw",
            height: "100vh",
            pointerEvents: "none",
            position: "fixed",
            top: 0,
            left: 0,
            zIndex: 2 ** 31 - 1, // maximum z-index
        });

        this.params = params || {};
        this.handle = 0;
        /** @type {CSSStyleSheet} */
        this.sheet = null;
        /** @type {[type: string, args: ...(string | number)[], options?: DebugItemOptions][]} */
        this.items = [];
    }

    /**
     * @param {HTMLElement} target
     */
    attach(target) {
        /**
         * @param {Event & { currentTarget: Window }} ev
         */
        const onWindowResize = ({ currentTarget }) => {
            this.canvas.width = currentTarget.innerWidth;
            this.canvas.height = currentTarget.innerHeight;
        };
        const { defaultView: view, styleSheets } = target.ownerDocument;
        this.canvas.width = view.innerWidth;
        this.canvas.height = view.innerHeight;
        view.addEventListener("resize", onWindowResize);
        target.appendChild(this.canvas);

        this.sheet = styleSheets[styleSheets.length - 1];
        this.ruleIndex = this.sheet.insertRule(
            `* { cursor: crosshair !important; }`,
            this.sheet.cssRules.length
        );

        this.handle = requestAnimationFrame(this._drawItems.bind(this));
    }

    detach() {
        if (this.handle) {
            cancelAnimationFrame(this.handle);
            this.handle = 0;
        }
        if (this.sheet) {
            this.sheet.deleteRule(this.ruleIndex);
            this.sheet = null;
            this.ruleIndex = 0;
        }

        this.canvas.remove();
    }

    /**
     * @param {number} x
     * @param {number} y
     * @param {number} radius
     * @param {DebugItemOptions} [options]
     */
    drawCircle(x, y, radius, options) {
        this.items.push(["circle", +x, +y, +radius, Math.PI * 2, options]);
    }

    /**
     * @param {number} x
     * @param {number} y
     * @param {number} radius
     * @param {number} duration
     */
    drawLoadingCircle(x, y, radius, duration) {
        const maxAngle = Math.PI * 2;
        const interval = duration / 10;
        const step = maxAngle / interval;
        const circle = ["circle", +x, +y, +radius, step];
        this.items.push(circle);

        const handle = setInterval(function grow() {
            if (circle[4] >= maxAngle) {
                return clearInterval(handle);
            }
            circle[4] = Math.min(circle[4] + step, maxAngle);
        }, 10);
    }

    /**
     * @param {number} x
     * @param {number} y
     */
    drawPath(x, y) {
        const path = this.items.find((item) => item[0] === "path");
        x = Math.max(Math.round(+x), 0);
        y = Math.max(Math.round(+y), 0);
        if (path) {
            const prevValues = path[1];
            path[1] = new Uint16Array(prevValues.length + 2);
            path[1].set(prevValues);
            path[1].set([x, y], prevValues.length);
        } else {
            this.items.push(["path", new Uint16Array([x, y])]);
        }
    }

    /**
     *
     * @param {number} x
     * @param {number} y
     * @param {number} width
     * @param {number} height
     * @param {DebugItemOptions} [options]
     */
    drawRect(x, y, width, height, options) {
        this.items.push([
            "rect",
            Math.floor(+x),
            Math.floor(+y),
            Math.ceil(+width),
            Math.ceil(+height),
            options,
        ]);
    }

    /**
     * @param {Draggable} instance
     * @param {string} label
     * @param {...unknown} args
     */
    log(instance, label, ...args) {
        if (!instance.params.debug) {
            return;
        }
        console.debug(
            `%c[%c${instance.constructor.name}%c::%c${label}%c]%c`,
            "font-weight: bold;",
            "color: #0c9; font-weight: bold;",
            "font-weight: bold;",
            "color: #fc6; font-weight: bold;",
            "font-weight: bold;",
            "",
            ...args
        );
    }

    /**
     * @param {string} color
     */
    setColor(color) {
        this.params.color = color;
    }

    /**
     * @private
     */
    _drawItems() {
        const ctx = this.canvas.getContext("2d");
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (let i = 0; i < this.items.length; i++) {
            const [type, ...args] = this.items[i];
            const options =
                Object.prototype.toString.call(args.at(-1)) === "[object Object]"
                    ? args.pop()
                    : null;

            let label = options?.label;
            if (options?.color) {
                ctx.fillStyle = options.color;
                ctx.strokeStyle = options.color;
            } else if (this.params.color) {
                ctx.fillStyle = this.params.color;
                ctx.strokeStyle = this.params.color;
            }
            switch (type) {
                case "circle": {
                    const [x, y, radius, angle] = args;
                    // Center dot
                    ctx.beginPath();
                    ctx.arc(x, y, 3, 0, 2 * Math.PI);
                    ctx.fill();
                    // Outer circle
                    ctx.beginPath();
                    ctx.arc(x, y, radius, 0, angle);
                    ctx.lineWidth = 2;
                    ctx.setLineDash([]);
                    ctx.stroke();
                    // Label
                    ctx.lineWidth = 1;
                    ctx.font = "16px sans-serif";
                    label ||= `X: ${Math.floor(x)}, Y: ${Math.floor(y)}`;
                    const metrics = ctx.measureText(label);
                    const textHeight =
                        metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent;
                    ctx.fillText(label, x + radius, y + radius + textHeight);
                    break;
                }
                case "path": {
                    const [coordinates] = args;
                    ctx.beginPath();
                    ctx.lineWidth = 2;
                    ctx.setLineDash([3, 6]);
                    if (coordinates.length > 2) {
                        ctx.moveTo(coordinates[0], coordinates[1]);
                        for (let j = 2; j < coordinates.length; j += 2) {
                            ctx.lineTo(coordinates[j], coordinates[j + 1]);
                        }
                        ctx.stroke();
                    }
                    break;
                }
                case "rect": {
                    const [x, y, w, h] = args;
                    ctx.lineWidth = 2;
                    ctx.setLineDash([3, 3]);
                    ctx.strokeRect(x, y, w, h);
                    if (label) {
                        if (typeof label !== "string") {
                            label = `X: ${Math.floor(x)}, Y: ${Math.floor(y)}`;
                        }
                        ctx.lineWidth = 1;
                        ctx.font = "16px sans-serif";
                        const metrics = ctx.measureText(label);
                        const textHeight =
                            metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent;
                        ctx.fillText(label, x + 5, y + textHeight + 5);
                    }
                    break;
                }
            }
            if (options?.once) {
                this.items.splice(i--, 1);
            }
        }

        this.handle = requestAnimationFrame(this._drawItems.bind(this));
    }
}
