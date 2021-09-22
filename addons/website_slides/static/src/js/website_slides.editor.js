/** @odoo-module **/

import { _t } from 'web.core';
import Dialog from 'web.Dialog';
import WebsiteNewMenu from 'website.newMenu';
import SlidesCourseTagAdd from '@website_slides/js/slides_course_tag_add';

const TagCourseDialog = SlidesCourseTagAdd.TagCourseDialog;

var ChannelCreateDialog = Dialog.extend({
    template: 'website.slide.channel.create',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slides_channel.xml',
         '/website_slides/static/src/xml/website_slides_channel_tag.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'change input#tag_ids' : '_onChangeTag',
    }),
    custom_events: _.extend({}, Dialog.prototype.custom_events, {
        'tag_refresh': '_onTagRefresh',
        'tag_remove_new': '_onTagRemoveNew',
    }),
    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("New Course"),
            size: 'medium',
            buttons: [{
                text: _t("Create"),
                classes: 'btn-primary',
                click: this._onClickFormSubmit.bind(this)
            }, {
                text: _t("Discard"),
                close: true
            },]
        });
        this._super(parent, options);
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $input = self.$('#tag_ids');
            $input.select2({
                width: '100%',
                allowClear: true,
                formatNoMatches: false,
                multiple: true,
                selection_data: false,
                formatSelection: function (data) {
                    if (data.tag) {
                        data.text = data.tag;
                    }
                    return data.text;
                },
                createSearchChoice: function(term, data) {
                    var addedTags = $(this.opts.element).select2('data');
                    if (_.filter(_.union(addedTags, data), function (tag) {
                        return tag.text.toLowerCase().localeCompare(term.toLowerCase()) === 0;
                    }).length === 0) {
                        if (this.opts.can_create) {
                            return {
                                id: _.uniqueId('tag_'),
                                create: true,
                                tag: term,
                                text: _.str.sprintf(_t("Create new Tag '%s'"), term),
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
                        if (that.matcher(query.term, obj.name)) {
                            tags.results.push({id: obj.id, text: obj.name});
                        }
                    });
                    query.callback(tags);
                },
                query: function (query) {
                    var that = this;
                    // fetch data only once and store it
                    if (!this.selection_data) {
                        self._rpc({
                            route: '/slides/channel/tag/search_read',
                            params: {
                                fields: ['name'],
                                domain: [],
                            }
                        }).then(function (data) {
                            that.can_create = data.can_create;
                                that.fill_data(query, data.read_results);
                                that.selection_data = data.read_results;
                        });
                    } else {
                        this.fill_data(query, this.selection_data);
                    }
                }
            });
        });
    },
    _onClickFormSubmit: function (ev) {
        var $form = this.$("#slide_channel_add_form");
        var $title = this.$("#title");
        if (!$title[0].value){
            $title.addClass('border-danger');
            this.$("#title-required").removeClass('d-none');
        } else {
            $form.submit();
        }
    },
    _onChangeTag: function (ev) {
        var self = this;
        var tags = $(ev.currentTarget).select2('data');
        tags.forEach(function (element) {
            if (element.create) {
                new TagCourseDialog(self, { defaultTag: element.text }).open();
            }
        });
    },
    /**
     * Replace the new tag ID by its real ID
     * @param ev
     * @private
     */
    _onTagRefresh: function (ev) {
        var $tag_ids = $('#tag_ids');
        var tags = $tag_ids.select2('data');
        tags.forEach(function (element) {
            if (element.create) {
                element.id = ev.data.tag_id;
                element.create = false;
            }
        });
        $tag_ids.select2('data', tags);
        // Set selection_data to false to force tag reload
        $tag_ids.data('select2').opts.selection_data = false;
    },
    /**
     * Remove the created tag if the user clicks on 'Discard' on the create tag Dialog
     * @private
     */
    _onTagRemoveNew: function () {
        var tags = $('#tag_ids').select2('data');
        tags = tags.filter(function (value) {
            return !value.create;
        });
        $('#tag_ids').select2('data', tags);
    },
});

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide_channel: '_createNewSlideChannel',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Displays the popup to create a new slide channel,
     * and redirects the user to this channel.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
     _createNewSlideChannel: function () {
        var self = this;
        var def = new Promise(function (resolve) {
            var dialog = new ChannelCreateDialog(self, {});
            dialog.open();
            dialog.on('closed', self, resolve);
        });
        return def;
     },
});
