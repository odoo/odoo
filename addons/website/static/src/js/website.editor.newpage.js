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
                        console.log('/website/add/' + encodeURI(val) + "?add_menu=" + $dialog.find('input[type="checkbox"]').is(':checked'));
                        document.location = '/website/add/' + encodeURI(val) + "?add_menu=" + $dialog.find('input[type="checkbox"]').is(':checked');
                    }
                });
            }
        }),
    });
})();