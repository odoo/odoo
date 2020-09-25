odoo.define('auth_totp_portal.button', function (require) {
'use strict';

const {_t} = require('web.core');
const publicWidget = require('web.public.widget');
const Dialog = require('web.Dialog');
const {handleCheckIdentity} = require('portal.portal');

/**
 * Replaces specific <field> elements by normal HTML, strip out the rest entirely
 */
function fromField(f, record) {
    switch (f.getAttribute('name')) {
    case 'qrcode':
        const qrcode = document.createElement('img');
        qrcode.setAttribute('class', 'img img-fluid offset-1');
        qrcode.setAttribute('src', 'data:image/png;base64,' + record['qrcode']);
        return qrcode;
    case 'url':
        const url = document.createElement('a');
        url.setAttribute('href', record['url']);
        url.textContent = f.getAttribute('text') || record['url'];
        return url;
    case 'code':
        const code = document.createElement('input');
        code.setAttribute('name', 'code');
        code.setAttribute('class', 'form-control col-10 col-md-6');
        code.setAttribute('placeholder', '6-digit code');
        code.required = true;
        code.maxLength = 6;
        code.minLength = 6;
        return code;
    default: // just display the field's data
        return document.createTextNode(record[f.getAttribute('name')] || '');
    }
}

/**
 * Apparently chrome literally absolutely can't handle parsing XML and using
 * those nodes in an HTML document (even when parsing as application/xhtml+xml),
 * this results in broken rendering and a number of things not working (e.g.
 * classes) without any specific warning in the console or anything, things are
 * just broken with no indication of why.
 *
 * So... rebuild the entire f'ing body using document.createElement to ensure
 * we have HTML elements.
 *
 * This is a recursive implementation so it's not super efficient but the views
 * to fixup *should* be relatively simple.
 */
function fixupViewBody(oldNode, record) {
    let qrcode = null, code = null, node = null;

    switch (oldNode.nodeType) {
        case 1: // element
            if (oldNode.tagName === 'field') {
                node = fromField(oldNode, record);
                switch (oldNode.getAttribute('name')) {
                case 'qrcode':
                    qrcode = node;
                    break;
                case 'code':
                    code = node;
                    break
                }
                break; // no need to recurse here
            }
            node = document.createElement(oldNode.tagName);
            for(let i=0; i<oldNode.attributes.length; ++i) {
                const attr = oldNode.attributes[i];
                node.setAttribute(attr.name, attr.value);
            }
            for(let j=0; j<oldNode.childNodes.length; ++j) {
                const [ch, qr, co] = fixupViewBody(oldNode.childNodes[j], record);
                if (ch) { node.appendChild(ch); }
                if (qr) { qrcode = qr; }
                if (co) { code = co; }
            }
            break;
        case 3: case 4: // text, cdata
            node = document.createTextNode(oldNode.data);
            break;
        default:
            // don't care about PI & al
    }

    return [node, qrcode, code]
}

/**
 * Converts a backend <button> element and a bunch of metadata into a structure
 * which can kinda be of use to Dialog.
 */
class Button {
    constructor(parent, model, record_id, input_node, button_node) {
        this._parent = parent;
        this.model = model;
        this.record_id = record_id;
        this.input = input_node;
        this.text = button_node.getAttribute('string');
        this.classes = button_node.getAttribute('class') || null;
        this.action = button_node.getAttribute('name');
        if (button_node.getAttribute('special') === 'cancel') {
            this.close = true;
            this.click = null;
        } else {
            this.close = false;
            // because Dialog doesnt' call() click on the descriptor object
            this.click = this._click.bind(this);
        }
    }
    async _click() {
        if (!this.input.reportValidity()) {
            this.input.classList.add('is-invalid');
            return;
        }

        try {
            await this.callAction(this.record_id, {code: this.input.value});
        } catch (e) {
            this.input.classList.add('is-invalid');
            // show custom validity error message
            this.input.setCustomValidity(e.message);
            this.input.reportValidity();
            return;
        }
        this.input.classList.remove('is-invalid');
        // reloads page, avoid window.location.reload() because it re-posts forms
        window.location = window.location;
    }
    async callAction(id, update) {
        try {
            await this._parent._rpc({model: this.model, method: 'write', args: [id, update]});
            await handleCheckIdentity(
                this._parent.proxy('_rpc'),
                this._parent._rpc({model: this.model, method: this.action, args: [id]})
            );
        } catch(e) {
            // avoid error toast (crashmanager)
            e.event.preventDefault();
            // try to unwrap mess of an error object to a usable error message
            throw new Error(
                !e.message ? e.toString()
              : !e.message.data ? e.message.message
              : e.message.data.message || _t("Operation failed for unknown reason.")
            );
        }
    }
}

publicWidget.registry.TOTPButton = publicWidget.Widget.extend({
    selector: '#auth_totp_portal_enable',
    events: {
        click: '_onClick',
    },

    async _onClick(e) {
        e.preventDefault();

        const w = await handleCheckIdentity(this.proxy('_rpc'), this._rpc({
            model: 'res.users',
            method: 'totp_enable_wizard',
            args: [this.getSession().user_id]
        }));

        if (!w) {
            // TOTP probably already enabled, just reload page
            window.location = window.location;
            return;
        }

        const {res_model: model, res_id: wizard_id} = w;

        const record = await this._rpc({
            model, method: 'read', args: [wizard_id, []]
        }).then(ar => ar[0]);

        const doc = new DOMParser().parseFromString(
            document.getElementById('totp_wizard_view').textContent,
            'application/xhtml+xml'
        );

        const xmlBody = doc.querySelector('sheet *');
        const [body, , codeInput] = fixupViewBody(xmlBody, record);
        // remove custom validity error message any time the field changes
        // otherwise it sticks and browsers suppress submit
        codeInput.addEventListener('input', () => codeInput.setCustomValidity(''));

        const buttons = [];
        for(const button of doc.querySelectorAll('footer button')) {
            buttons.push(new Button(this, model, record.id, codeInput, button));
        }

        // wrap in a root host of .modal-body otherwise it breaks our neat flex layout
        const $content = document.createElement('form');
        $content.appendChild(body);
        // implicit submission by pressing [return] from within input
        $content.addEventListener('submit', (e) => {
            e.preventDefault();
            // sadness: footer not available as normal element
            dialog.$footer.find('.btn-primary').click();
        });
        var dialog = new Dialog(this, {$content, buttons}).open();
    }
});
publicWidget.registry.DisableTOTPButton = publicWidget.Widget.extend({
    selector: '#auth_totp_portal_disable',
    events: {
        click: '_onClick'
    },

    async _onClick(e) {
        e.preventDefault();
        await handleCheckIdentity(
            this.proxy('_rpc'),
            this._rpc({model: 'res.users', method: 'totp_disable', args: [this.getSession().user_id]})
        )
        window.location = window.location;
    }
});
});
