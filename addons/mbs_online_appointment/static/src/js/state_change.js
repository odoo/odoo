odoo.define('mbs_online_appointment.state_change', function (require) {
    'use strict';

    var core = require('web.core');
    
   $(document).ready(function() {
        // On change event for the country dropdown
        $('#country_id').on('change', function() {
            var countryId = $(this).val();

            // Make an AJAX request to retrieve the states based on the selected country
            $.ajax({
                url: '/get_states',
                type: 'POST',
                dataType: 'json',
                data: {
                    'country_id': countryId,
                },
                success: function(response) {
                    var states = response.states;

                    // Clear existing options
                    $('#state_id').empty();

                    // Add new options based on the retrieved states
                    $.each(states, function(index, state) {
                        $('#state_id').append($('<option>', {
                            value: state.id,
                            text: state.name
                        }));
                    });
                }
            });
        });
    });
});