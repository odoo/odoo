/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import rpc from '@web/core/network/rpc';

publicWidget.registry.BioEditorModal = publicWidget.Widget.extend({
    selector: '#open_bio_modal',

    events: {
        click: '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();

        const modalElement = document.getElementById('bio_modal');

        // Mostrar el modal usando jQuery
        $(modalElement).modal('show');

        // Manejar el click en el botón "Guardar"
        modalElement.querySelector('#save_bio_btn').onclick = () => {
            const newBio = modalElement.querySelector('#bio_textarea').value;

            rpc('/abrir_bio_editor', {
                bio: newBio,
            }).then(() => {
                // Cierra el modal con jQuery
                $(modalElement).modal('hide');
                alert('Biografía actualizada correctamente');
            }).catch(() => {
                alert('Error al actualizar la biografía');
            });
        };
    },
});
