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

            function update_style(unable, disable) {
                $modal.addClass("loading");
                openerp.jsonRpc('/website/theme_customize', 'call', {
                        'unable': unable,
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
            $modal.on('change', 'input', function () {
                var $option = $(this), $group, checked = $(this).is(":checked");
                if (checked) {
                    if ($option.data('unable')) {
                        $group = $modal.find('#'+$option.data('unable').split(", #"));
                        $group.each(function () {
                            var check = $(this).is(":checked");
                            $(this).attr("checked", true).closest("label").addClass("checked");
                            if (!check) $(this).change();
                        });
                    }
                    if ($option.data('disable')) {
                        $group = $modal.find('#'+$option.data('disable').split(", #"));
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

                clearTimeout(time);
                time = setTimeout(function () {
                    var $unable = $modal.find('[data-xmlid]:checked');
                    $unable.closest("label").addClass("checked");
                    $unable = $unable.filter(function () { return $(this).data("xmlid") !== "";});
                    var unable = $.makeArray($unable.map(function () { return $(this).data("xmlid"); }));

                    var $disable = $modal.find('[data-xmlid]:not(:checked)');
                    $disable.closest("label").removeClass("checked");
                    $disable = $disable.filter(function () { return $(this).data("xmlid") !== "";});
                    var disable = $.makeArray($disable.map(function () { return $(this).data("xmlid"); }));
                    
                    if(run) update_style(unable, disable);
                },0);
            });

            var removed = [];
            for (var k=0; k<xmls.length; k++) {
                var $input = $modal.find('[data-xmlid="'+xmls[k][0]+'"]');
                if(!$input.size()) {
                    removed.push(xmls[k]);
                } else if(xmls[k][1] !== "disabled") {
                    $input.attr("checked", true).change();
                }
            }
            if (removed.length) {
                update_style([], removed);
            }
            run = true;
        });
    });

})();