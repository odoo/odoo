(function () {
    'use strict';

    function theme_customize () {
        var uniqueID = 0;
        openerp.jsonRpc('/website/theme_customize_modal', 'call').then(function (modal) {
            if ($('.theme_customize_modal').size()) return false;

            var $modal = $(modal);
            $modal.addClass("theme_customize_modal")
                .appendTo("body")
                .on('click', '.close', function () {
                    $modal.removeClass('in');
                    $modal.addClass('out');
                    setTimeout(function () {$modal.remove();}, 1000);
                });

            function get_inputs (string) {
                return $modal.find('#'+string.split(",").join(", #"));
            }
            function get_xml_ids ($inputs) {
                var xml_ids = [];
                $inputs.each(function () {
                    if ($(this).data('xmlid') && $(this).data('xmlid').length) {
                        xml_ids = xml_ids.concat($(this).data('xmlid').split(","));
                    }
                });
                return xml_ids;
            }
            // force the browse to re-compute the stylesheets
            function stylesheet() {
                $('body').css("margin-top", "0.1px");
                setTimeout(function () {
                    $('body').css("margin-top", "0px");
                }, 0);
            }

            function update_style(enable, disable, reload) {
                $modal.addClass("loading");
                var req = openerp.jsonRpc('/website/theme_customize', 'call', {
                        'enable': enable,
                        'disable': disable
                    });
                var $assets = $('link[href*=".assets_"]');
                if (!reload && $assets.size()) {
                    req.then(function () {
                        $assets.each(function () {
                            var href = $(this).attr("href").split("?")[0]+"?v="+new Date().getTime();
                            var $asset = $('<link rel="stylesheet" href="'+href+'"/>');
                            $asset.attr("onload", "$(this).prev().attr('disable', true).remove();");
                            $(this).after($asset);
                        });
                        $modal.removeClass("loading");
                        stylesheet();
                    });
                } else {
                    setTimeout(function () {
                        window.location.hash = "theme=true";
                        window.location.reload();
                    },25);
                }
            }

            function enable_disable (data, enable) {
                if (!data) return;
                $modal.find('#'+data.split(",").join(", #")).each(function () {
                    var check = $(this).is(":checked");
                    var $label = $(this).closest("label");
                    $(this).attr("checked", enable);
                    if (enable) $label.addClass("checked");
                    else $label.removeClass("checked");
                    if (check != enable) {
                        $(this).change();
                    }
                });
            }

            var run = false;
            var reload = false;
            var time;
            $modal.on('change', 'input[data-xmlid],input[data-enable],input[data-disable]', function () {
                var $option = $(this), checked = $(this).is(":checked");

                if (checked) {
                    enable_disable($option.data('enable'), true);
                    enable_disable($option.data('disable'), false);
                    $option.closest("label").addClass("checked");
                } else {
                    $option.closest("label").removeClass("checked");
                }
                $option.attr("checked", checked);

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
                    $set.trigger('update');
                });

                if (run && $(this).data('reload') && document.location.href.match(new RegExp( $(this).data('reload') ))) {
                    reload = true;
                }

                clearTimeout(time);
                if (run) {
                    time = setTimeout(function () {
                        update_style(get_xml_ids($enable), get_xml_ids($disable), reload);
                        reload = false;
                    },0);
                } else {
                    time = setTimeout(function () { reload = false; },0);
                }
            });

            // feature to use select field
            var $selects = $modal.find('select:has(option[data-xmlid],option[data-enable],option[data-disable])');
            $selects.each(function () {
                uniqueID++;
                var $select = $(this);
                var $options = $select.find('option[data-xmlid], option[data-enable], option[data-disable]');
                $options.each(function () {
                    var $option = $(this);
                    var $input = $('<input style="display: none;" type="radio" name="theme_customize_modal-select-'+uniqueID+'"/>');
                    $input.attr('id', $option.attr('id'));
                    $input.attr('data-xmlid', $option.data('xmlid'));
                    $input.attr('data-enable', $option.data('enable'));
                    $input.attr('data-disable', $option.data('disable'));
                    $option.removeAttr('id');
                    $option.data('input', $input);
                    $input.on('update', function () {
                        $option.attr('selected', $(this).is(":checked"));
                    });
                    $modal.append($input);
                });
                $select.data("value", $options.first());
                $options.first().attr("selected", true);
            });
            $selects.change(function () {
                var $option = $(this).find('option:selected');
                $(this).data("value").data("input").attr("checked", true).change();
                $(this).data("value", $option);
                $option.data("input").change();
            });

            var $inputs = $("input[data-xmlid]");
            openerp.jsonRpc('/website/theme_customize_get', 'call', {
                    'xml_ids': get_xml_ids($inputs)
                }).then(function (data) {
                    $inputs.each(function () {
                        if (!_.difference(get_xml_ids($(this)), data[0]).length) {
                            $(this).attr("checked", true).change();
                        }
                    });
                    run = true;
                });

            $('a').each(function () {
                var href = $(this).attr("href") || "";
                if (href.match(/^[^#]*\//) && href.indexOf('theme=true') === -1) {
                    $(this).attr("href", href + (href.indexOf("#") === -1 ? '#' : '&' ) + 'theme=true');
                }
            });

            setTimeout(function () {$modal.addClass('in');}, 0);
        });
    }

    openerp.website.ready().done(function() {
        $(document).on('click', "#theme_customize a",theme_customize);
        if ((window.location.hash || "").indexOf("theme=true") !== -1) {
            theme_customize();
            window.location.hash = "";
        }
    });

})();
