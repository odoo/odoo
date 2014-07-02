(function () {
    'use strict';

    openerp.website.add_template_file('/website/static/src/xml/website.theme.xml');

    openerp.website.Theme = openerp.Widget.extend({
        template: 'website.theme_customize',
        events: {
            'change input[data-xmlid],input[data-enable],input[data-disable]': 'change_selection',
            'click .close': 'close',
        },
        start: function () {
            var self = this;
            this.timer = null;
            this.reload = false;
            this.flag = false;
            this.$el.addClass("theme_customize_modal");
            this.active_select_tags();
            this.$inputs = $("input[data-xmlid]");
            setTimeout(function () {self.$el.addClass('in');}, 0);
            return this.load_xml_data().then(function () {
                self.flag = true;
            });
        },
        active_select_tags: function () {
            var uniqueID = 0;
            var self = this;
            var $selects = this.$('select:has(option[data-xmlid],option[data-enable],option[data-disable])');
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
                    self.$el.append($input);
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
        },
        load_xml_data: function (xml_ids) {
            var self = this;
            return openerp.jsonRpc('/website/theme_customize_get', 'call', {
                    'xml_ids': this.get_xml_ids(this.$inputs)
                }).then(function (data) {
                    self.$inputs.each(function () {
                        if (!_.difference(self.get_xml_ids($(this)), data[1]).length) {
                            $(this).attr("checked", false).change();
                        }
                        if (!_.difference(self.get_xml_ids($(this)), data[0]).length) {
                            $(this).attr("checked", true).change();
                        }
                    });
                });
        },
        get_xml_ids: function ($inputs) {
            var xml_ids = [];
            $inputs.each(function () {
                if ($(this).data('xmlid') && $(this).data('xmlid').length) {
                    xml_ids = xml_ids.concat($(this).data('xmlid').split(","));
                }
            });
            return xml_ids;
        },
        compute_stylesheets: function () {
            var self = this;
            $('link[href*=".assets_"]').attr('data-loading', true);
            function theme_customize_css_onload() {
                if ($('link[data-loading]').size()) {
                    $('body').toggleClass('theme_customize_css_loading');
                    setTimeout(theme_customize_css_onload, 50);
                } else {
                    $('body').removeClass('theme_customize_css_loading');
                    self.$el.removeClass("loading");
                }
            }
            theme_customize_css_onload();
        },
        update_style: function (enable, disable, reload) {
            if (this.$el.hasClass("loading")) return;
            this.$el.addClass("loading");

            var $assets = $('link[href*=".assets_"]');
            if (!reload && $assets.size()) {
                this.compute_stylesheets();

                return openerp.jsonRpc('/website/theme_customize', 'call', {
                        'enable': enable,
                        'disable': disable
                    }).then(function () {
                    $assets.each(function () {
                        var href = $(this).attr("href").replace(/[^\/]+$/, new Date().getTime());
                        var $asset = $('<link rel="stylesheet" href="'+href+'"/>');
                        var clear_link = "$(this).prev().attr('disable', true).remove(); $(this).removeAttr('onload').removeAttr('onerror');";
                        $asset.attr("onload", clear_link);
                        $asset.attr("onerror", clear_link);
                        $(this).after($asset);
                    });
                });
            } else {
                var href = '/website/theme_customize_reload'+
                    '?href='+encodeURIComponent(window.location.href)+
                    '&enable='+encodeURIComponent(enable.join(","))+
                    '&disable='+encodeURIComponent(disable.join(","));
                window.location.href = href;
                return $.Deferred();
            }
        },
        enable_disable: function (data, enable) {
            if (!data) return;
            this.$('#'+data.split(",").join(", #")).each(function () {
                var check = $(this).is(":checked");
                var $label = $(this).closest("label");
                $(this).attr("checked", enable);
                if (enable) $label.addClass("checked");
                else $label.removeClass("checked");
                if (check != enable) {
                    $(this).change();
                }
            });
        },
        change_selection: function (event) {
            var self = this;
            if (this.$el.hasClass("loading")) return;

            var $option = $(event.target),
                checked = $option.is(":checked");

            if (checked) {
                this.enable_disable($option.data('enable'), true);
                this.enable_disable($option.data('disable'), false);
                $option.closest("label").addClass("checked");
            } else {
                $option.closest("label").removeClass("checked");
            }
            $option.attr("checked", checked);

            var $enable = this.$('[data-xmlid]:checked');
            $enable.closest("label").addClass("checked");
            var $disable = this.$('[data-xmlid]:not(:checked)');
            $disable.closest("label").removeClass("checked");

            var $sets = this.$('input[data-enable]:not([data-xmlid]), input[data-disable]:not([data-xmlid])');
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

            if (this.flag && $option.data('reload') && document.location.href.match(new RegExp( $option.data('reload') ))) {
                this.reload = true;
            }

            clearTimeout(this.timer);
            if (this.flag) {
                this.timer = setTimeout(function () {
                    self.update_style(self.get_xml_ids($enable), self.get_xml_ids($disable), self.reload);
                    self.reload = false;
                },0);
            } else {
                this.timer = setTimeout(function () { self.reload = false; },0);
            }
        },
        close: function () {
            var self = this;
            $('link[href*=".assets_"]').removeAttr('data-loading');
            this.$el.removeClass('in');
            this.$el.addClass('out');
            setTimeout(function () {self.destroy();}, 500);
        }
    });

    openerp.website.ready().done(function() {
        function theme_customize() {
            var Theme = openerp.website.Theme;
            if (Theme.open && !Theme.open.isDestroyed()) return;
            Theme.open = new Theme();
            Theme.open.appendTo("body");
        }
        $(document).on('click', "#theme_customize a",theme_customize);
        if ((window.location.hash || "").indexOf("theme=true") !== -1) {
            theme_customize();
            window.location.hash = "";
        }
    });

})();
