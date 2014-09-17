(function () {
    'use strict';

    openerp.jsonRpc('/web/dataset/call', 'call', {
            'model': 'ir.ui.view',
            'method': 'read_template',
            'args': ['website.theme_customize', openerp.website.get_context()]
        }).done(function (data) {
        openerp.qweb.add_template(data);
    });
    openerp.jsonRpc('/web/dataset/call', 'call', {
            'model': 'ir.ui.view',
            'method': 'read_template',
            'args': ['website.colorpicker', openerp.website.get_context()]
        }).done(function (data) {
        openerp.qweb.add_template(data);
    });

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
            this.$inputs = $("input[data-xmlid],input[data-enable],input[data-disable]");
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
                        $option.attr('selected', $(this).prop("checked"));
                    });
                    self.$el.append($input);
                });
                $select.data("value", $options.first());
                $options.first().attr("selected", true);
            });
            $selects.change(function () {
                var $option = $(this).find('option:selected');
                $(this).data("value").data("input").prop("checked", true).change();
                $(this).data("value", $option);
                $option.data("input").change();
            });
        },
        load_xml_data: function (xml_ids) {
            var self = this;
            $('#theme_error').remove();
            return openerp.jsonRpc('/website/theme_customize_get', 'call', {
                    'xml_ids': this.get_xml_ids(this.$inputs)
                }).done(function (data) {
                    self.$inputs.filter('[data-xmlid=""]').prop("checked", true).change();
                    self.$inputs.filter('[data-xmlid]:not([data-xmlid=""])').each(function () {
                        if (!_.difference(self.get_xml_ids($(this)), data[1]).length) {
                            $(this).prop("checked", false).change();
                        }
                        if (!_.difference(self.get_xml_ids($(this)), data[0]).length) {
                            $(this).prop("checked", true).change();
                        }
                    });
                }).fail(function (d, error) {
                    $('body').prepend($('<div id="theme_error"/>').text(error.data.message));
                });
        },
        get_inputs: function (string) {
            return this.$inputs.filter('#'+string.split(",").join(", #"));
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
            self.has_error = false;
            $('link[href*=".assets_"]').attr('data-loading', true);
            function theme_customize_css_onload() {
                if ($('link[data-loading]').size()) {
                    $('body').toggleClass('theme_customize_css_loading');
                    setTimeout(theme_customize_css_onload, 50);
                } else {
                    $('body').removeClass('theme_customize_css_loading');
                    self.$el.removeClass("loading");

                    if (window.getComputedStyle($('button[data-toggle="collapse"]:first')[0]).getPropertyValue('position') === 'static' ||
                        window.getComputedStyle($('#theme_customize_modal')[0]).getPropertyValue('display') === 'none') {
                        if (self.has_error) {
                            window.location.hash = "theme=true";
                            window.location.reload();
                        } else {
                            self.has_error = true;
                            $('link[href*=".assets_"][data-error]').removeAttr('data-error').attr('data-loading', true);
                            self.update_stylesheets();
                            setTimeout(theme_customize_css_onload, 50);
                        }
                    }
                }
            }
            theme_customize_css_onload();
        },
        update_stylesheets: function () {
            $('link[href*=".assets_"]').each(function update () {
                var $style = $(this);
                var href = $style.attr("href").replace(/[^\/]+$/, new Date().getTime());
                var $asset = $('<link rel="stylesheet" href="'+href+'"/>');
                $asset.attr("onload", "$(this).prev().attr('disable', true).remove(); $(this).removeAttr('onload').removeAttr('onerror');");
                $asset.attr("onerror", "$(this).prev().removeAttr('data-loading').attr('data-error','loading'); $(this).attr('disable', true).remove();");
                $style.after($asset);
            });
        },
        update_style: function (enable, disable, reload) {
            var self = this;
            if (this.$el.hasClass("loading")) return;
            this.$el.addClass("loading");

            if (!reload && $('link[href*=".assets_"]').size()) {
                this.compute_stylesheets();
                return openerp.jsonRpc('/website/theme_customize', 'call', {
                        'enable': enable,
                        'disable': disable
                    }).then(function () {
                        self.update_stylesheets();
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
                var check = $(this).prop("checked");
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
                checked = $option.prop("checked");

            if (checked) {
                this.enable_disable($option.data('enable'), true);
                this.enable_disable($option.data('disable'), false);
                $option.closest("label").addClass("checked");
            } else {
                $option.closest("label").removeClass("checked");
            }
            $option.prop("checked", checked);

            var $enable = this.$inputs.filter('[data-xmlid]:checked');
            $enable.closest("label").addClass("checked");
            var $disable = this.$inputs.filter('[data-xmlid]:not(:checked)');
            $disable.closest("label").removeClass("checked");

            var $sets = this.$inputs.filter('input[data-enable]:not([data-xmlid]), input[data-disable]:not([data-xmlid])');
            $sets.each(function () {
                var $set = $(this);
                var checked = true;
                if ($set.data("enable")) {
                    self.get_inputs($(this).data("enable")).each(function () {
                        if (!$(this).prop("checked")) checked = false;
                    });
                }
                if ($set.data("disable")) {
                    self.get_inputs($(this).data("disable")).each(function () {
                        if ($(this).prop("checked")) checked = false;
                    });
                }
                if (checked) {
                    $set.prop("checked", true).closest("label").addClass("checked");
                } else {
                    $set.prop("checked", false).closest("label").removeClass("checked");
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
            $('#theme_error').remove();
            $('link[href*=".assets_"]').removeAttr('data-loading');
            this.$el.removeClass('in');
            this.$el.addClass('out');
            setTimeout(function () {self.destroy();}, 500);
        }
    });

    function themeError(message) {
        var _t = openerp._t;

        if (message.indexOf('lessc')) {
            message = '<span class="text-muted">' + message + "</span><br/><br/>" + _t("Please install or update node-less");
        }

        var $error = $( openerp.qweb.render('website.error_dialog', {
            title: _t("Theme Error"),
            message: message
        }));
        $error.appendTo("body").modal();
        $error.on('hidden.bs.modal', function () {
            $(this).remove();
        });
    }


    openerp.website.ready().done(function() {
        function theme_customize() {
            var Theme = openerp.website.Theme;
            if (Theme.open && !Theme.open.isDestroyed()) return;
            Theme.open = new Theme();
            Theme.open.appendTo("body");
            
            var error = window.getComputedStyle(document.body, ':before').getPropertyValue('content');
            if (error && error !== 'none') {
                themeError(eval(error));
            }
        }
        $(document).on('click', "#theme_customize a",theme_customize);
        if ((window.location.hash || "").indexOf("theme=true") !== -1) {
            theme_customize();
            window.location.hash = "";
        }
    });

})();
