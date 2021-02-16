// Copyright Nova Code (http://www.novacode.nl)
// See LICENSE file for full licensing details.

import { OdooFormioForm } from "./formio_form.js";

/**
FIX / WORKAROUND browser compatibility error.
Wrap Component class and bootstrap into functions and put template in
Component env.

OS/platform: browsers
=====================
- Mac: Safari 13.1
- iOS: Safari, Firefox

Error
=====
- Safari 13.1 on Mac experiences error:
  unexpected token '='. expected an opening '(' before a method's parameter list
- iOS not debugged yet. Dev Tools not present in browser.

More info
=========
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes#Browser_compatibility
*/

function app() {
    class App extends OdooFormioForm {
        initForm() {
            if (!!document.getElementById('formio_builder_uuid')) {
                this.builderUuid = document.getElementById('formio_builder_uuid').value;
            }
            this.configUrl = '/formio/public/form/create/' + this.builderUuid + '/config';
            this.submissionUrl = false;
            this.submitUrl = '/formio/public/form/create/' + this.builderUuid + '/submit';
        }

        publicSubmitDoneUrl() {
            return this.params.hasOwnProperty('public_submit_done_url') && this.params.public_submit_done_url;
        }

        submitDone(submission) {
            if (submission.state == 'submitted') {
                if (this.publicSubmitDoneUrl()) {
                    const params = {submit_done_url: this.publicSubmitDoneUrl()};
                    window.parent.postMessage({odooFormioMessage: 'formioSubmitDone', params: params});
                }
            }
            // If the window.parent doesn't receive and handle the postMessage.
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        }
    }

    const app = new App();
    app.mount(document.getElementById('formio_form_app'));
}

async function start() {
    const templates = await owl.utils.loadFile('/formio/static/src/js/form/public_create_app.xml');
    const env = { qweb: new owl.QWeb({templates})};
    owl.Component.env = env;
    await owl.utils.whenReady();
    app();
}

start();
