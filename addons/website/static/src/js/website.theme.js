(function () {
    'use strict';

    $(document).on('click', "#theme_customize a", function (event) {
        openerp.jsonRpc('/website/theme_customize_modal', 'call').then(function (modal) {
            var $modal = $(modal);
            $modal.appendTo("body").modal({backdrop: false});
            $modal.on('hidden.bs.modal', function () {
                $(this).remove();
            });
            $("body").removeClass("modal-open");

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
                    
                    $modal.addClass("loading");
                    openerp.jsonRpc('/website/theme_customize', 'call', {
                            'unable': unable,
                            'disable': disable
                        }).then(function () {
                            $('head link[href^="/web/css/website.assets_frontend"]').attr("disabled", false);

                            var url = '/web/css/website.assets_frontend?'+new Date().getTime();
                            if (!$style.size()) {
                                $style = $('<link rel="stylesheet">').appenTo('head');
                            }

                            var img = document.createElement('img');
                            img.onerror = function() {
                                $modal.removeClass("loading");
                            };
                            $style.attr("href", url);
                            img.src = url;

                            $.get(url, function (css) {
                                console.log(css);
                            });
                        });
                },0);
            });
        });
    });

})();