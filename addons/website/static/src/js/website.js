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
        Aloha.ready(function() {
            Aloha.jQuery('[data-oe-model]').aloha(); //.attr('contentEditable', 'true').addClass('oe_editable');
            self.$('button').prop('disabled', true);
            Aloha.bind('aloha-editable-activated', function (ev, args) {
                var $e = args.editable.obj;
                if (!$e.is('.oe_dirty')) {
                    $e.addClass('oe_dirty');
                    self.$('button').prop('disabled', false);
                    // TODO: Are we going to use a meta-data flag in order to know if the field shall be text or html ?
                    $e.data('original', $e.html());
                }
            });
        });
        return r;
    },
    save: function () {
        var self = this;
        var defs = [];
        $('.oe_dirty').each(function () {
            var $el = $(this);
            var def = self.saveElement($el).then(function () {
                $el.removeClass('oe_dirty');
            }).fail(function () {
                var data = $el.data();
                console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
            });
            defs.push(def);
        });
        return $.when.apply(null, defs).then(function () {
            self.$('button').prop('disabled', true);
        });
    },
    saveElement: function ($el) {
        var data = $el.data();
        return (new instance.web.DataSet(this, 'ir.ui.view')).call('save', [data.oeModel, data.oeId, data.oeField, $el.html()/*, data.oeXpath*/]);
    },
    cancel: function () {
        $('.oe_dirty').each(function () {
            $(this).removeClass('oe_dirty').html($(this).data('original'));
        });
        this.$('button').prop('disabled', true);
    }
});

};
