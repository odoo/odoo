// Backported from 52ca425

(function () {
    'use strict';

    var website = openerp.website;

    function load_called_template () {
        var ids_or_xml_ids = _.uniq($("[data-oe-call]").map(function () {return $(this).data('oe-call');}).get());
        if (ids_or_xml_ids.length) {
            openerp.jsonRpc('/website/multi_render', 'call', {
                'ids_or_xml_ids': ids_or_xml_ids
            }).then(function (data) {
                for (var k in data) {
                    var $data = $(data[k]).addClass('o_block_'+k);
                    $("[data-oe-call='"+k+"']").each(function () {
                        $(this).replaceWith($data.clone());
                    });
                }
            });
        }
    }

    $(document).ready(load_called_template);
})();