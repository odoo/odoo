// todo: replace this file with the actual code of the lib.
odoo.define('web_editor.jabberwock', function(require) {
    'use strict';

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = 'http://localhost:8080/odoo-integration.js';
    document.getElementsByTagName('head')[0].appendChild(script);
    return new Promise(resolve => {
        script.onload = () => {
            resolve(JWEditor);
        };
    });
});
