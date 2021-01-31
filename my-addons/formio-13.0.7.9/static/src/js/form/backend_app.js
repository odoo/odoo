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
            if (!!document.getElementById('formio_form_uuid')) {
                this.formUuid = document.getElementById('formio_form_uuid').value;
            }
            this.configUrl = '/formio/form/' + this.formUuid + '/config';
            this.submissionUrl = '/formio/form/' + this.formUuid + '/submission';
            this.submitUrl = '/formio/form/' + this.formUuid + '/submit';
        }

        portalSubmitDoneUrl() {
            return this.params.hasOwnProperty('portal_submit_done_url') && this.params.portal_submit_done_url;
        }

        submitDone(submission) {
            if (submission.state == 'submitted') {
                if (this.urlParams.get('portal') === 'true' && this.portalSubmitDoneUrl()) {
                    const params = {submit_done_url: this.portalSubmitDoneUrl()};
                    window.parent.postMessage({odooFormioMessage: 'formioSubmitDone', params: params});
                }
            }
            // If the window.parent doesn't receive and handle the postMessage.
            setTimeout(function() {
                window.location.reload();
            }, 500);
        }
    }

    const app = new App();
    app.mount(document.getElementById('formio_form_app'));
}

async function start() {
    const templates = await owl.utils.loadFile('/formio/static/src/js/form/backend_app.xml');
    const env = { qweb: new owl.QWeb({templates})};
    owl.Component.env = env;
    await owl.utils.whenReady();
    app();
}

start();
