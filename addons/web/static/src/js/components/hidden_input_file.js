odoo.define('web.HiddenInputFile', function (require) {
    "use strict";

    // TODO: convert to RPC
    class HiddenInputFile extends owl.Component {
        constructor() {
            super(...arguments);
            this.targetID = `${this.constructor.name}_${this.constructor._nextID++}`;
            this.fileInputRef = owl.hooks.useRef('fileInputRef');
            this.formRef =owl.hooks.useRef('formRef');
            this.csrfToken = odoo.csrf_token;
            this._active = false;
        }
        _onFileLoaded(ev) {
            if (!this._active) {return;}
            let result;
            try {
                result = JSON.parse(ev.target.contentDocument.body.innerText);
                if (!this.props.multiUpload) {
                    result = result[0];
                }
            } catch (e) {
                result = {error: e};
            }
            this._active = false;
            this.trigger('file-ready', result);
        }
        _onChangedFile() {
            this._active = true;
            this.formRef.el.submit();
        }
        chooseFile() {
            // no other solution than to manually
            // click to open the file selection dialog
            // must be done in a user interaction stack
            this.fileInputRef.el.click();
        }
    }
    HiddenInputFile.template = 'web.OwlHiddenInputFile';
    HiddenInputFile._nextID = 0;

    return HiddenInputFile;
});
