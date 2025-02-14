import { highlightjs } from "@web/doc/highlightjs/highlightjs";
import { Component, xml, useRef, onWillUpdateProps, onMounted } from "@odoo/owl";

function memoize(func) {
    const cache = new Map();
    const funcName = func.name ? func.name + " (memoized)" : "memoized";
    return {
        [funcName](...args) {
            if (!cache.has(args[0])) {
                cache.set(args[0], func(...args));
            }
            return cache.get(...args);
        },
    }[funcName];
}

const memoizedHighlight = memoize(highlightjs.highlight);
const memoizedHighlightAuto = memoize(highlightjs.highlightAuto);

function copyToClipboard(event, value) {
    navigator?.clipboard?.writeText(value);

    const div = document.createElement("div");
    div.className = "position-fixed bg-default rounded";
    div.style.color = "var(--text)";
    div.style.padding = ".25rem .5rem";
    div.style.fontSize = ".8em";
    div.style.zIndex = 100;
    div.innerText = "Copied!";
    document.body.appendChild(div);

    const rect = div.getBoundingClientRect();
    div.style.left = event.clientX - rect.width / 2.0 + "px";
    div.style.top = event.clientY - rect.height + "px";

    div.animate(
        [
            { transform: "translateY(0px)", opacity: 1 },
            { transform: "translateY(-20px)", opacity: 0 },
        ],
        {
            duration: 1000,
            iterations: 1,
        }
    );

    setTimeout(() => {
        div.remove();
    }, 990);
}

function getCursorPos(target) {
    if (target.getRootNode().activeElement !== target) {
        return null;
    }

    const rrange = window.getSelection().getRangeAt(0);
    const path = [];
    let cur = rrange.startContainer;

    while (cur !== target) {
        path.push(cur);
        cur = cur.parentNode;
    }

    let cursor = 0;
    let children = target.childNodes;
    for (let i = path.length - 1; i >= 0; --i) {
        for (let j = 0; j < children.length; ++j) {
            if (children[j] === path[i]) {
                break;
            }
            cursor += children[j].textContent.length;
        }
        children = path[i].childNodes;
    }

    const offset = rrange.startOffset;

    if (rrange.startContainer.nodeType === Node.TEXT_NODE) {
        cursor += offset;
    } else {
        for (let i = 0; i < offset; ++i) {
            cursor += rrange.startContainer.childNodes[i].textContent.length;
        }
    }

    return cursor;
}

function setCursorPos(target, cursor) {
    if (cursor === null) {
        return;
    }

    let cur = target;
    while (cur.nodeType !== Node.TEXT_NODE) {
        if (cur.childNodes.length === 0) {
            break;
        }

        for (let i = 0; i < cur.childNodes.length; ++i) {
            const clen = cur.childNodes[i].textContent.length;
            if (cursor <= clen) {
                cur = cur.childNodes[i];
                break;
            }
            cursor -= clen;
        }
    }

    const range = document.createRange();
    const sel = window.getSelection();
    range.setStart(cur, cursor);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
}

export class CodeViewer extends Component {
    static template = xml`
        <div class="o-doc-code-viewer position-relative">
            <pre class="p-0" t-att-class="props.class" t-ref="preRef"><code
                class="hljs"
                t-ref="codeRef"
                spellcheck="false"
                t-att-contenteditable="props.editable"
                t-on-input="onInput"
                t-on-keydown="onKeydown"
            ></code></pre>
            <div class="o-doc-code-viewer-floating position-absolute flex align-items-center top-1 right-1">
                <t t-slot="default"/>
                <i class="o-copy-btn cursor-pointer fa fa-clipboard" t-on-click="copyToClipboard">
                </i>
            </div>
        </div>
    `;
    static props = {
        value: { type: String },
        class: { type: String, optional: true },
        language: { type: String, optional: true },
        editable: { type: Boolean, optional: true },
        noHighlight: { type: Boolean, optional: true },
        onChange: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        class: "",
        slots: {},
        noHighlight: false,
    };

    setup() {
        this.codeRef = useRef("codeRef");

        onWillUpdateProps((props) => this.updateValue(props.value, props.language));
        onMounted(() => {
            this.updateValue(this.props.value, this.props.language);
        });
    }

    updateValue(value, language) {
        if (!this.codeRef.el || value === this.value) {
            return;
        }

        if (!this.props.noHighlight) {
            if (value) {
                let result = undefined;
                if (language) {
                    result = memoizedHighlight(value, { language });
                } else {
                    result = memoizedHighlightAuto(value);
                }
                this.codeRef.el.innerHTML = result.value;
                this.codeRef.el.dataset.language = result.language;
            } else {
                this.codeRef.el.innerHTML = "";
                this.codeRef.el.dataset.language = language;
            }
        }
    }

    onInput(event) {
        if (!this.props.editable) {
            return;
        }

        const pos = getCursorPos(this.codeRef.el);
        const code = this.codeRef.el.textContent;
        this.codeRef.el.innerHTML = highlightjs.highlight(code, {
            language: this.props.language,
        }).value;
        setCursorPos(this.codeRef.el, pos);

        this.value = event.target.innerText;
        this.props.onChange?.(event.target.innerText);
    }

    onKeydown(event) {
        if (!this.props.editable) {
            return;
        }

        let char = null;
        if (event.code === "Tab") {
            char = "    ";
        } else if (event.code === "Enter") {
            char = "\n";
        }

        if (char !== null) {
            event.preventDefault();
            const doc = this.codeRef.el.ownerDocument.defaultView;
            const selection = doc.getSelection();
            const range = selection.getRangeAt(0);
            const tabNode = document.createTextNode(char);
            range.insertNode(tabNode);

            range.setStartAfter(tabNode);
            range.setEndAfter(tabNode);
            selection.removeAllRanges();
            selection.addRange(range);
            this.codeRef.el.dispatchEvent(new Event("input"));
        }
    }

    copyToClipboard(event) {
        copyToClipboard(event, this.props.value);
    }
}
