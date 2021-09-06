odoo.define('flexipharmacy.AuditReportPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class AuditReportPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }
        mounted() {
            var self = this;
            $('button.tablinks').click(function(event){
                var cityName = $(event.currentTarget).attr('value');
                var i, tab_content, tab_links;
                tab_content = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tab_content.length; i++) {
                    tab_content[i].style.display = "none";
                }
                tab_links = document.getElementsByClassName("tablinks");
                for (i = 0; i < tab_links.length; i++) {
                    tab_links[i].className = tab_links[i].className.replace(" active", "");
                }
                document.getElementById(cityName).style.display = "block";
                event.currentTarget.className += " active";
            });
            $('.report_pdf.session').click(function(e){
                var session_id = $(e.currentTarget).data('id');
                self.env.pos.do_action('flexipharmacy.report_pos_inventory_session_pdf_front',{additional_context:{
                    active_ids:[session_id],
                }}).then(function () {
                    console.log("Report Printed.")
                }).guardedCatch(function (error) {
                    console.log("Report Not Printed.")
                });
            });
            $('.report_pdf.location').click(function(e){
                var location_id = $(e.currentTarget).data('id');
                self.env.pos.do_action('flexipharmacy.report_pos_inventory_location_pdf_front',{additional_context:{
                    active_ids:[location_id],
                }}).then(function () {
                    console.log("Report Printed.")
                }).guardedCatch(function (error) {
                    console.log("Report Not Printed.")
                });
            });
        }
        getPayload() {
            return null;
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    AuditReportPopup.template = 'AuditReportPopup';
    AuditReportPopup.defaultProps = {
        confirmText: '',
        cancelText: 'Close',
        title: '',
        body: '',
    };

    Registries.Component.add(AuditReportPopup);

    return AuditReportPopup;
});
