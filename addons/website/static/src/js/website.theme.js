(function () {
    'use strict';

    $(document).on('click', "#theme_customize a", function (event) {
        openerp.jsonRpc('/website/theme_customize_modal', 'call').then(function (data) {
            var xmls = data[1];
            var modal = data[0];
            var $modal = $(modal);
            $modal.appendTo("body").modal({backdrop: false});
            $modal.on('hidden.bs.modal', function () {
                $(this).remove();
            });
            $("body").removeClass("modal-open");

            function get_inputs (string) {
                return $modal.find('#'+string.split(",").join(", #"));
            }
            function get_xml_ids ($inputs) {
                var xml_ids = [];
                $inputs.each(function () {
                    if ($(this).data('xmlid') && $(this).data('xmlid').length) {
                        xml_ids.push($(this).data('xmlid'));
                    }
                });
                return xml_ids;
            }

            function update_style(enable, disable) {
                $modal.addClass("loading");
                openerp.jsonRpc('/website/theme_customize', 'call', {
                        'enable': enable,
                        'disable': disable
                    }).then(function () {
                        var $style = $('style#theme_style');
                        if (!$style.size()) {
                            $style = $('<style id="theme_style">').appendTo('head');
                        }
                        $.get('/web/css/website.assets_frontend?'+new Date().getTime(), function (css) {
                            $('head link[href^="/web/css/website.assets_frontend"]').attr("disabled", false).remove();
                            $style.html(css);
                            $modal.removeClass("loading");
                        });
                    });
            }

            var run = false;
            var time;
            $modal.on('change', 'input[data-xmlid],input[data-enable],input[data-disable]', function () {
                var $option = $(this), $group, checked = $(this).is(":checked");
                if (checked) {
                    if ($option.data('enable')) {
                        $group = $modal.find('#'+$option.data('enable').split(",").join(", #"));
                        $group.each(function () {
                            var check = $(this).is(":checked");
                            $(this).attr("checked", true).closest("label").addClass("checked");
                            if (!check) $(this).change();
                        });
                    }
                    if ($option.data('disable')) {
                        $group = $modal.find('#'+$option.data('disable').split(",").join(", #"));
                        $group.each(function () {
                            var check = $(this).is(":checked");
                            $(this).attr("checked", false).closest("label").removeClass("checked");
                            if (check) $(this).change();
                        });
                    }
                    $(this).closest("label").addClass("checked");
                } else {
                    $(this).closest("label").removeClass("checked");
                }
                $(this).attr("checked", checked);

                var $enable = $modal.find('[data-xmlid]:checked');
                $enable.closest("label").addClass("checked");
                var $disable = $modal.find('[data-xmlid]:not(:checked)');
                $disable.closest("label").removeClass("checked");

                var $sets = $modal.find('input[data-enable]:not([data-xmlid]), input[data-disable]:not([data-xmlid])');
                $sets.each(function () {
                    var $set = $(this);
                    var checked = true;
                    if ($set.data("enable")) {
                        get_inputs($(this).data("enable")).each(function () {
                            if ($(this).is(":not(:checked)")) checked = false;
                        });
                    }
                    if ($set.data("disable")) {
                        get_inputs($(this).data("disable")).each(function () {
                            if ($(this).is(":checked")) checked = false;
                        });
                    }
                    if (checked) {
                        $set.attr("checked", true).closest("label").addClass("checked");
                    } else {
                        $set.attr("checked", false).closest("label").removeClass("checked");
                    }
                });

                clearTimeout(time);
                if (run) time = setTimeout(function () {
                    update_style(get_xml_ids($enable), get_xml_ids($disable));
                },0);
            });

            var removed = [];
            _.each(xmls, function (xml) {
                var $input = $modal.find('[data-xmlid="'+xml[0]+'"]');
                if(!$input.size()) {
                    removed.push(xml);
                } else if(xml[1] !== "disabled") {
                    $input.attr("checked", true).change();
                }
            });
            if (removed.length) {
                update_style([], removed);
            }
            run = true;
        });
    });

})();
