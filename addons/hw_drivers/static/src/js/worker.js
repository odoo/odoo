    $(function() {
        "use strict";
        // mergedHead will be turned to true the first time we receive something from a new host
        // It allows to transform the <head> only once
        var mergedHead = false;
        var current_client_url = "";

        function longpolling() {
            $.ajax({
                type: 'POST',
                url: window.location.origin + '/point_of_sale/get_serialized_order/' + display_identifier,
                dataType: 'json',
                beforeSend: function(xhr){xhr.setRequestHeader('Content-Type', 'application/json');},
                data: JSON.stringify({jsonrpc: '2.0'}),

                success: function(data) {
                    if (data.result.error) {
                        $('.error-message').text(data.result.error);
                        $('.error-message').removeClass('d-none');
                        setTimeout(longpolling, 5000);
                        return;
                    }
                    if (data.result.rendered_html) {
                        var trimmed = $.trim(data.result.rendered_html);
                        var $parsedHTML = $('<div>').html($.parseHTML(trimmed,true)); // WARNING: the true here will executes any script present in the string to parse
                        var new_client_url = $parsedHTML.find(".resources > base").attr('href');

                        if (!mergedHead || (current_client_url !== new_client_url)) {

                            mergedHead = true;
                            current_client_url = new_client_url;
                            $("head").children().not('.origin').remove();
                            $("head").append($parsedHTML.find(".resources").html());
                        }

                        $(".container-fluid").html($parsedHTML.find('.pos-customer_facing_display').html());
                        $(".container-fluid").attr('class', 'container-fluid').addClass($parsedHTML.find('.pos-customer_facing_display').attr('class'));

                        var d = $('.pos_orderlines_list');
                        d.scrollTop(d.prop("scrollHeight"));

                        // Here we execute the code coming from the pos, apparently $.parseHTML() executes scripts right away,
                        // Since we modify the dom afterwards, the script might not have any effect
                        if (typeof foreign_js !== 'undefined' && $.isFunction(foreign_js)) {
                            foreign_js();
                        }
                    }
                    longpolling();
                },

                error: function (jqXHR, status, err) {
                    setTimeout(longpolling, 5000);
                },

                timeout: 30000,
            });
        };

        longpolling();
    });
