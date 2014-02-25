(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.is_editable = true;
    website.is_editable_button = true;
    
    website.EditorBar.include({
        start: function() {
            var res = this._super();
            this.$("a[data-action=new_page]").parents("li").removeClass("hidden");
            this.$(".oe_content_menu li.divider").removeClass("hidden");
            return res;
        },
        edit: function () {
            this.on('rte:ready', this, function () {
                $('a:has(span[data-oe-model="website.menu"])').tooltip({
                    title: _t('Save this page and use the top "Content" menu to edit the menu.'),
                    placement: "bottom",
                    trigger: "hover",
                    show: 50,
                    hide: 100,
                    container: 'body'
                });
            });
            return this._super();
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_page]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_page",
                    window_title: _t("New Page"),
                    input: _t("Page Title"),
                    init: function () {
                        var $group = this.$dialog.find("div.form-group");
                        $group.removeClass("mb0");

                        var $add = $(
                            '<div class="form-group mb0">'+
                                '<label class="col-sm-offset-3 col-sm-9 text-left">'+
                                '    <input type="checkbox" checked="checked" required="required"/> '+
                                '</label>'+
                            '</div>');
                        $add.find('label').append(_t("Add page in menu"));
                        $group.after($add);
                    }
                }).then(function (val, field, $dialog) {
                    if (val) {
                        var url = '/website/add/' + encodeURI(val);
                        if ($dialog.find('input[type="checkbox"]').is(':checked')) url +="?add_menu=1";
                        document.location = url;
                    }
                });
            }
        }),
    });
})();