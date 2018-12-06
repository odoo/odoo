odoo.define('mail.document_viewer_tests', function (require) {
"use strict";

var DocumentViewer = require('mail.DocumentViewer');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

/**
 * @param {Object} params
 * @param {Object[]} params.attachments
 * @param {int} params.attachmentID
 * @param {function} [params.mockRPC]
 * @param {boolean} [params.debug]
 * @returns {DocumentViewer}
 */
var createViewer = function (params) {
    var parent = new Widget();
    var viewer = new DocumentViewer(parent, params.attachments, params.attachmentID);

    var mockRPC = function (route) {
        if (route === '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/1?model%3Dir.attachment') {
            return $.when();
        }
        if (route === 'https://www.youtube.com/embed/FYqW0Gdwbzk') {
            return $.when();
        }
        if (route === '/web/content/4?model%3Dir.attachment') {
            return $.when();
        }
        if (route === '/web/image/6?unique=1&signature=999&model=ir.attachment') {
            return $.when();
        }
    };
    testUtils.mock.addMockEnvironment(parent, {
        mockRPC: function () {
            if (params.mockRPC) {
                var _super = this._super;
                this._super = mockRPC;
                var def = params.mockRPC.apply(this, arguments);
                this._super = _super;
                return def;
            } else {
                return mockRPC.apply(this, arguments);
            }
        },
        intercepts: params.intercepts || {},
    });
    var $target = $("#qunit-fixture");
    if (params.debug) {
        $target = $('body');
        $target.addClass('debug');
    }
    viewer.appendTo($target);

    // actually destroy the parent when the viewer is destroyed
    viewer.destroy = function () {
        delete viewer.destroy;
        parent.destroy();
    };
    return viewer;
};

QUnit.module('DocumentViewer', {
    beforeEach: function () {
        this.attachments = [
            {id: 1, datas_fname: 'filePdf.pdf', type: 'binary', mimetype: 'application/pdf', datas:'R0lGOP////ywAADs='},
            {id: 2, name: 'urlYoutubeName', type: 'url', mimetype: '', url: 'https://youtu.be/FYqW0Gdwbzk', datas_fname: 'urlYoutube'},
            {id: 3, name: 'urlGoogle', type: 'url', mimetype: '', url: 'https://www.google.com', datas_fname: 'urlRandom'},
            {id: 4, name: 'text.html', datas_fname: 'text.html', type: 'binary', mimetype: 'text/html', datas:'testee'},
            {id: 5, name: 'video.mp4', datas_fname: 'video.mp4', type: 'binary', mimetype: 'video/mp4', datas:'R0lDOP////ywAADs='},
            {id: 6, name: 'image.jpg', datas_fname: 'image.jpg', type: 'binary', mimetype: 'image/jpeg', checksum: 999, datas:'R0lVOP////ywAADs='},
        ];
    },
}, function () {

    QUnit.test('basic rendering', function (assert) {
        assert.expect(7);

        var viewer = createViewer({
            attachmentID: 1,
            attachments: this.attachments,
        });

        assert.containsOnce(viewer, '.o_viewer_content',
            "there should be a preview");
        assert.containsOnce(viewer, '.o_close_btn',
            "there should be a close button");
        assert.containsOnce(viewer, '.o_viewer-header',
            "there should be a header");
        assert.containsOnce(viewer, '.o_image_caption',
            "there should be an image caption");
        assert.containsOnce(viewer, '.o_viewer_zoomer',
            "there should be a zoomer");
        assert.containsOnce(viewer, '.fa-chevron-right',
            "there should be a right nav icon");
        assert.containsOnce(viewer, '.fa-chevron-left',
            "there should be a left nav icon");

        viewer.destroy();
    });

    QUnit.test('Document Viewer Youtube', function (assert) {
        assert.expect(3);

        var youtubeURL = 'https://www.youtube.com/embed/FYqW0Gdwbzk';
        var viewer = createViewer({
            attachmentID: 2,
            attachments: this.attachments,
            mockRPC: function (route) {
                if (route === youtubeURL) {
                    assert.ok(true, "should have called youtube URL");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(viewer.$(".o_image_caption:contains('urlYoutubeName')").length, 1,
            "the viewer should be on the right attachment");
        assert.containsOnce(viewer, '.o_viewer_text[data-src="' + youtubeURL + '"]',
            "there should be a video player");

        viewer.destroy();
    });

    QUnit.test('Document Viewer html/(txt)', function (assert) {
        assert.expect(2);

        var viewer = createViewer({
            attachmentID: 4,
            attachments: this.attachments,
        });

        assert.strictEqual(viewer.$(".o_image_caption:contains('text.html')").length, 1,
            "the viewer be on the right attachment");
        assert.containsOnce(viewer, 'iframe[data-src="/web/content/4?model%3Dir.attachment"]',
            "there should be an iframe with the right src");

        viewer.destroy();
    });

    QUnit.test('Document Viewer mp4', function (assert) {
        assert.expect(2);

        var viewer = createViewer({
            attachmentID: 5,
            attachments: this.attachments,
        });

        assert.strictEqual(viewer.$(".o_image_caption:contains('video.mp4')").length, 1,
            "the viewer be on the right attachment");
        assert.containsOnce(viewer, '.o_viewer_video',
            "there should be a video player");

        viewer.destroy();
    });

    QUnit.test('Document Viewer jpg', function (assert) {
        assert.expect(2);

        var viewer = createViewer({
            attachmentID: 6,
            attachments: this.attachments,
        });

        assert.strictEqual(viewer.$(".o_image_caption:contains('image.jpg')").length, 1,
            "the viewer be on the right attachment");
        assert.containsOnce(viewer, 'img[data-src="/web/image/6?unique=1&signature=999&model=ir.attachment"]',
            "there should be a video player");

        viewer.destroy();
    });

    QUnit.test('is closable by button', function (assert) {
        assert.expect(3);

        var viewer = createViewer({
            attachmentID: 6,
            attachments: this.attachments,
        });

        assert.containsOnce(viewer, '.o_viewer_content',
            "should have a document viewer");
        assert.containsOnce(viewer, '.o_close_btn',
            "should have a close button");

        testUtils.dom.click(viewer.$('.o_close_btn'));

        assert.ok(viewer.isDestroyed(), 'viewer should be destroyed');
    });

    QUnit.test('is closable by clicking on the wrapper', function (assert) {
        assert.expect(3);

        var viewer = createViewer({
            attachmentID: 6,
            attachments: this.attachments,
        });

        assert.containsOnce(viewer, '.o_viewer_content',
            "should have a document viewer");
        assert.containsOnce(viewer, '.o_viewer_img_wrapper',
            "should have a wrapper");

        testUtils.dom.click(viewer.$('.o_viewer_img_wrapper'));

        assert.ok(viewer.isDestroyed(), 'viewer should be destroyed');
    });
});
});
