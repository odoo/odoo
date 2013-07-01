openerp.website = function(instance) {

instance.website.EditorBar = instance.web.Widget.extend({
    template: 'Website.EditorBar',
    events: {
        'click button[data-action=save]': 'save',
        'click button[data-action=cancel]': 'cancel',
    },
    container: 'body',
    start: function() {
        var self = this;
        var r = this._super.apply(this, arguments);
        this.$container = $(this.container);
        this.$container.addClass('oe_website_editor_container');
        this.$container.find('[data-oe-model]').attr('contentEditable', 'true').addClass('oe_editable');
        this.$('button').prop('disabled', true);
        // .click(function (e) {
        //     e.stopPropagation();
        //     e.preventDefault();
        // });
        $('body').on("keypress.oe_webeditor", ".oe_editable", function(e) {
            var $e = $(e.currentTarget);
            if (!$e.is('.oe_dirty')) {
                $e.addClass('oe_dirty');
                self.$('button').prop('disabled', false);
                // TODO: Are we going to use a meta-data flag in order to know if the field shall be text or html ?
                $e.data('original', $e.text());
            }
            if (e.which == 13) {
                $e.blur();
                e.preventDefault();
            }
        });
        return r;
    },
    save: function () {
        var self = this;
        var defs = [];
        this.$container.find('.oe_dirty').each(function () {
            var $el = $(this);
            var def = self.saveElement($el).then(function () {
                $el.removeClass('oe_dirty');
            }).fail(function () {
                var data = $el.data();
                self.do_warn('Error', _.str.sprintf('Could not save %s#%d#%s', data.model, data.id, data.field));
            });
            defs.push(def);
        });
        return $.when.apply(null, defs).then(function () {
            self.$('button').prop('disabled', true);
        });
    },
    saveElement: function ($el) {
        var data = $el.data();
        var update = {};
        update[data.field] = $el.text();
        return (new instance.web.DataSet(this, data.model)).write(data.id, update);
    },
    cancel: function () {
        this.$container.find('.oe_dirty').each(function () {
            $(this).removeClass('oe_dirty').text($(this).data('original'));
        });
        this.$('button').prop('disabled', true);
    },
    destroy: function () {
        this._super.apply(this, arguments);
        this.$container.removeClass('oe_website_editor_container');
        this.$container.find('.oe_editable').removeAttr('contentEditable');
    }
});

};
