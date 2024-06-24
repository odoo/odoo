import { Plugin } from "../plugin";

export class SanitizePlugin extends Plugin {
    static name = "sanitize";
    static shared = ["sanitize"];
    setup() {
        if (!window.DOMPurify) {
            throw new Error("DOMPurify is not available");
        }
        this.DOMPurify = DOMPurify(this.document.defaultView);
    }
    sanitize(...args) {
        return this.DOMPurify.sanitize(...args);
    }
}
