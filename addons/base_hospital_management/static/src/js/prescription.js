odoo.define('base_hospital_management.prescription', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
    var rpc = require('web.rpc');
    publicWidget.registry.prescriptionWidget = publicWidget.Widget.extend({
    //Extends the publicWidget.Widget class to hide and show the button and calculate the distance between locations.
        selector: '#my_prescriptions',
        events: {
            'click .pr_download': 'onDownloadClick',
        },
        onDownloadClick: function (ev) {
            var rec_id = $(ev.currentTarget).data('id');
            rpc.query({
                model: 'hospital.outpatient',
                method: 'create_file',
                args: [rec_id],
            }).then(function (result) {
                window.open(result['url']);
            });
        },
    });
    return publicWidget.registry.prescriptionWidget;
});
