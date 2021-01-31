// Copyright Nova Code (http://www.novacode.nl)
// See LICENSE file for full licensing details.

$(document).ready(function() {
    iFrameResize({}, '.formio_form_embed');

    window.addEventListener('message', function(event) {
        const baseUrl = window.location.protocol + '//' + window.location.host;

        if (event.data.hasOwnProperty('odooFormioMessage')) {
            const msg = event.data.odooFormioMessage,
                  params = event.data.params,
                  submitDoneUrl = params.hasOwnProperty('submit_done_url') && params.submit_done_url;

            if (event.origin == baseUrl && msg == 'formioSubmitDone' && submitDoneUrl) {
                window.location = submitDoneUrl;
            }
        }
    }, false);
});
