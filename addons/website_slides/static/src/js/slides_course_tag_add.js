/** @odoo-module **/

import { _t } from 'web.core';
import Dialog from 'web.Dialog';
import publicWidget from 'web.public.widget';

var TagCourseDialog = Dialog.extend({
    template: 'website.slides.tag.add',
    events: _.extend({}, Dialog.prototype.events, {
        'change input#tag_id' : '_onChangeTag',
    }),

    /**
    * @override
    * @param {Object} parent
    * @param {Object} options holding channelId
    *      
    */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("Add a tag"),
            size: 'medium',
            buttons: [{
                text: _t("Add"),
                classes: 'btn-primary',
                click: this._onClickFormSubmit.bind(this)
            }, {
                text: _t("Discard"),
                click: this._onClickClose.bind(this)
            }]
        });

        this.channelID = parseInt(options.channelId, 10);
        this.tagIds = options.channelTagIds || [];
        // Open with a tag name as default
        this.defaultTag = options.defaultTag;
        this._super(parent, options);
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._bindSelect2Dropdown();
            self._hideTagGroup();
            if (self.defaultTag) {
                self._setDefaultSelection();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * 'Tag' and 'Tag Group' management for select2
     *
     * @private
     */
    _bindSelect2Dropdown: function () {
        var self = this;
        this.$('#tag_id').select2(this._select2Wrapper(_t('Tag'),
            function () {
                return self._rpc({
                    route: '/slides/channel/tag/search_read',
                    params: {
                        fields: ['name'],
                        domain: [['id', 'not in', self.tagIds], ['color', '!=', 0]],
                    }
                });
            })
        );
        this.$('#tag_group_id').select2(this._select2Wrapper(_t('Tag Group (required for new tags)'),
            function () {
                return self._rpc({
                    route: '/slides/channel/tag/group/search_read',
                    params: {
                        fields: ['name'],
                        domain: [],
                    }
                });
            })
        );
    },

    /**
     * Wrapper for select2 load data from server at once and store it.
     *
     * @private
     * @param {String} Placeholder for element.
     * @param {Function} Function to fetch data from remote location should return a Promise
     * resolved data should be array of object with id and name. eg. [{'id': id, 'name': 'text'}, ...]
     * @param {String} [nameKey='name'] (optional) the name key of the returned record
     *   ('name' if not provided)
     * @returns {Object} select2 wrapper object
    */
    _select2Wrapper: function (tag, fetchFNC, nameKey) {
        nameKey = nameKey || 'name';

        var values = {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: false,
            selection_data: false,
            fetch_rpc_fnc: fetchFNC,
            formatSelection: function (data) {
                if (data.tag) {
                    data.text = data.tag;
                }
                return data.text;
            },
            createSearchChoice: function (term, data) {
                var addedTags = $(this.opts.element).select2('data');
                if (_.filter(_.union(addedTags, data), function (tag) {
                    return tag.text.toLowerCase().localeCompare(term.toLowerCase()) === 0;
                }).length === 0) {
                    if (this.opts.can_create) {
                        return {
                            id: _.uniqueId('tag_'),
                            create: true,
                            tag: term,
                            text: _.str.sprintf(_t("Create new %s '%s'"), tag, term),
                        };
                    } else {
                        return undefined;
                    }
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj[nameKey])) {
                        tags.results.push({id: obj.id, text: obj[nameKey]});
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var that = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        that.can_create = data.can_create;
                        that.fill_data(query, data.read_results);
                        that.selection_data = data.read_results;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            }
        };
        return values;
    },

    _setDefaultSelection: function () {
        this.$('#tag_id').select2('data', {id: _.uniqueId('tag_'), text: this.defaultTag, create: true}, true);
        this.$('#tag_id').select2('readonly', true);
    },

    /**
     * Get value for tag_id and [when appropriate] tag_group_id to send to server
     *
     * @private
     */
    _getSelect2DropdownValues: function () {
        var result = {};
        var tag = this.$('#tag_id').select2('data');
        if (tag) {
            if (tag.create) {
                // new tag
                var group = this.$('#tag_group_id').select2('data');
                if(group) {
                    result['tag_id'] = [0, {'name': tag.text}]
                    if (group.create) {
                        // new tag group
                        result['group_id'] = [0, {'name': group.text}];
                    } else {
                        result['group_id'] = [group.id];
                    }
                }
            } else {
                result['tag_id'] = [tag.id];
            }
        }
        return result;
    },

    /**
     * Select2 fields makes the "required" input hidden on the interface.
     * Therefore we need to make a method to visually provide this requirement
     * feedback to users. "tag group" field should only need this when a new tag
     * is created.
     *
     * @private
     */
    _formValidate: function ($form) {
        $form.addClass('was-validated');
        var result = $form[0].checkValidity();
        
        var $tagInput = this.$('#tag_id');
        if ($tagInput.length !== 0){
            var $tagSelect2Container = $tagInput
                .closest('.form-group')
                .find('.select2-container');
            $tagSelect2Container.removeClass('is-invalid is-valid');
            if ($tagInput.is(':invalid')) {
                $tagSelect2Container.addClass('is-invalid');
            } else if ($tagInput.is(':valid')) {
                $tagSelect2Container.addClass('is-valid');
                var $tagGroupInput = this.$('#tag_group_id');
                if ($tagGroupInput.length !== 0){
                    var $tagGroupSelect2Container = $tagGroupInput
                        .closest('.form-group')
                        .find('.select2-container');
                    if ($tagGroupInput.is(':invalid')) {
                        $tagGroupSelect2Container.addClass('is-invalid');
                    } else if ($tagGroupInput.is(':valid')) {
                        $tagGroupSelect2Container.addClass('is-valid');
                    }
                }
            }
        }
        return result;
    },

    _alertDisplay: function (message) {
        this._alertRemove();
        $('<div/>', {
            "class": 'alert alert-warning',
            role: 'alert'
        }).text(message).insertBefore(this.$('form'));
    },
    _alertRemove: function () {
        this.$('.alert-warning').remove();
    },
    
    /**
     * When the user IS NOT creating a new tag, this function hides the group tag field
     * and makes it not required. Since the select2 field makes an extra container, this
     * needs to be hidden along with the group tag input field and its label.
     *
     * @private
     */
    _hideTagGroup: function () {
        var $tag_group_id = this.$('#tag_group_id');
        var $tagGroupSelect2Container = $tag_group_id.closest('.form-group');
        $tagGroupSelect2Container.hide();
        $tag_group_id.removeAttr("required");
        $tag_group_id.select2("val", "");
    },

    /**
     * When the user IS creating a new tag, this function shows the field and
     * makes it required. Since the select2 field makes an extra container, this
     * needs to be shown along with the group input field and its label.
     *
     * @private
     */
    _showTagGroup: function () {
        var $tag_group_id = this.$('#tag_group_id');
        var $tagGroupSelect2Container = $tag_group_id.closest('.form-group');
        $tagGroupSelect2Container.show();
        $tag_group_id.attr("required", "required");
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    _onClickFormSubmit: function () {
        if (this.defaultTag && !this.channelID) {
            this._createNewTag();
        } else {
            this._addTagToChannel();
        }
    },

    _addTagToChannel: function () {
        var self = this;
        var $form = this.$('#slides_channel_tag_add_form');
        if (this._formValidate($form)) {
            var values = this._getSelect2DropdownValues();
            return this._rpc({
                route: '/slides/channel/tag/add',
                params: {'channel_id': this.channelID,
                         'tag_id': values.tag_id,
                         'group_id': values.group_id},
            }).then(function (data) {
                if (data.error) {
                    self._alertDisplay(data.error);
                } else {
                    window.location = data.url;
                }
            });
        }
    },

    _createNewTag: function () {
        var self = this;
        var $form = this.$('#slides_channel_tag_add_form');
        this.$('#tag_id').select2('readonly', false);
        var valid = this._formValidate($form);
        this.$('#tag_id').select2('readonly', true);
        if (valid) {
            var values = this._getSelect2DropdownValues();
            return this._rpc({
                route: '/slide_channel_tag/add',
                params: {
                    'tag_id': values.tag_id,
                    'group_id': values.group_id
                },
            }).then(function (data) {
                self.trigger_up('tag_refresh', { tag_id: data.tag_id });
                self.close();
            });
        }
    },

    _onClickClose: function () {
        if (this.defaultTag && !this.channelID) {
            this.trigger_up('tag_remove_new');
        }
        this.close();
    },

    _onChangeTag: function (ev) {
        var self = this;
        var tag = $(ev.currentTarget).select2('data');
        if (tag && tag.create) {
            self._showTagGroup();
        } else {
            self._hideTagGroup();
        }
    },
});

publicWidget.registry.websiteSlidesTag = publicWidget.Widget.extend({
    selector: '.o_wslides_js_channel_tag_add',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides_channel_tag.xml'],
    events: {
        'click': '_onAddTagClick',
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($element) {
        var data = $element.data();
        return new TagCourseDialog(this, data).open();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onAddTagClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget));
    },
});

export default {
    TagCourseDialog: TagCourseDialog,
    websiteSlidesTag: publicWidget.registry.websiteSlidesTag
};
