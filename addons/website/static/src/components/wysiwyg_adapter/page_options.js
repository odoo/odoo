/** @odoo-module **/
export const pageOptionsCallbacks = {
    header_overlay: function (value) {
        this.document.getElementById('wrapwrap').classList.toggle('o_header_overlay', value);
    },
    header_visible: function (value) {
        const headerEl = this.document.querySelector('#wrapwrap > header');
        headerEl.classList.toggle('d-none', !value);
        headerEl.classList.toggle('o_snippet_invisible', !value);
    },
    footer_visible: function (value) {
        const footerEl = this.document.querySelector('#wrapwrap > footer');
        footerEl.classList.toggle('d-none', !value);
        footerEl.classList.toggle('o_snippet_invisible', !value);
    },
};
export class PageOption {
    /***
     * Some page options are defined with an input el hidden inside the content that we're editing.
     *
     * @param {HTMLInputElement} el The element holding the value of the page option
     * @param {Document} document The document on which the option applies.
     * @param {string} name The name of the method to be called before applying an option.
     * @param {boolean} isDirty true when it has been modified during an edit session.
     */
    constructor(el, document, name, isDirty = false) {
        this.el = el;
        this.isDirty = isDirty;
        this.document = document;
        this.name = name;
        if (pageOptionsCallbacks[name]) {
            this.callback = pageOptionsCallbacks[name].bind(this);
        }
    }
    get value() {
        if (this.el.value.toLowerCase() === 'true') {
            return true;
        } else if (this.el.value.toLowerCase() === 'false') {
            return false;
        }
        return this.el.value;
    }
    set value(value) {
        if (this.callback) {
            this.callback(value);
        }
        this.el.value = value;
        this.isDirty = true;
    }
}
