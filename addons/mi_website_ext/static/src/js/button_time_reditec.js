
odoo.define('mi_website_ext.btn_time_redirect', function (require) {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.querySelector('.btn-time');
        if (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault(); 
                var href = btn.getAttribute('href');
                if (href) {
                    window.location.href = href; 
                }
            });
        }
    });
});