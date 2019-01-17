odoo.define('web_editor.wysiwyg.translation', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;

$.summernote.lang.odoo = {
    font: {
        bold: _t('Bold'),
        italic: _t('Italic'),
        underline: _t('Underline'),
        clear: _t('Remove Font Style'),
        height: _t('Line Height'),
        name: _t('Font Family'),
        strikethrough: _t('Strikethrough'),
        subscript: _t('Subscript'),
        superscript: _t('Superscript'),
        size: _t('Font Size')
    },
    image: {
        image: _t('Picture'),
        insert: _t('Insert Image'),
        resizeFull: _t('Resize Full'),
        resizeHalf: _t('Resize Half'),
        resizeQuarter: _t('Resize Quarter'),
        floatLeft: _t('Float Left'),
        floatRight: _t('Float Right'),
        floatNone: _t('Float None'),
        shapeRounded: _t('Shape: Rounded'),
        shapeCircle: _t('Shape: Circle'),
        shapeThumbnail: _t('Shape: Thumbnail'),
        shapeNone: _t('Shape: None'),
        dragImageHere: _t('Drag image or text here'),
        dropImage: _t('Drop image or Text'),
        selectFromFiles: _t('Select from files'),
        maximumFileSize: _t('Maximum file size'),
        maximumFileSizeError: _t('Maximum file size exceeded.'),
        url: _t('Image URL'),
        remove: _t('Remove Image'),
        original: _t('Original')
    },
    video: {
        video: _t('Video'),
        videoLink: _t('Video Link'),
        insert: _t('Insert Video'),
        url: _t('Video URL'),
        providers: _t('(YouTube, Vimeo, Vine, Instagram, DailyMotion or Youku)')
    },
    link: {
        link: _t('Link'),
        insert: _t('Insert Link'),
        unlink: _t('Unlink'),
        edit: _t('Edit'),
        textToDisplay: _t('Text to display'),
        url: _t('To what URL should this link go?'),
        openInNewWindow: _t('Open in new window')
    },
    table: {
        table: _t('Table'),
        addRowAbove: _t('Add row above'),
        addRowBelow: _t('Add row below'),
        addColLeft: _t('Add column left'),
        addColRight: _t('Add column right'),
        delRow: _t('Delete row'),
        delCol: _t('Delete column'),
        delTable: _t('Delete table')
    },
    hr: {
        insert: _t('Insert Horizontal Rule')
    },
    style: {
        style: _t('Style'),
        p: _t('Normal'),
        blockquote: _t('Quote'),
        pre: _t('Code'),
        h1: _t('Header 1'),
        h2: _t('Header 2'),
        h3: _t('Header 3'),
        h4: _t('Header 4'),
        h5: _t('Header 5'),
        h6: _t('Header 6')
    },
    lists: {
        unordered: _t('Unordered list'),
        ordered: _t('Ordered list')
    },
    options: {
        help: _t('Help'),
        fullscreen: _t('Full Screen'),
        codeview: _t('Code View')
    },
    paragraph: {
        paragraph: _t('Paragraph'),
        outdent: _t('Outdent'),
        indent: _t('Indent'),
        left: _t('Align left'),
        center: _t('Align center'),
        right: _t('Align right'),
        justify: _t('Justify full')
    },
    color: {
        recent: _t('Recent Color'),
        more: _t('More Color'),
        background: _t('Background Color'),
        foreground: _t('Foreground Color'),
        transparent: _t('Transparent'),
        setTransparent: _t('Set transparent'),
        reset: _t('Reset'),
        resetToDefault: _t('Reset to default')
    },
    shortcut: {
        shortcuts: _t('Keyboard shortcuts'),
        close: _t('Close'),
        textFormatting: _t('Text formatting'),
        action: _t('Action'),
        paragraphFormatting: _t('Paragraph formatting'),
        documentStyle: _t('Document Style'),
        extraKeys: _t('Extra keys')
    },
    help: {
        insertParagraph: _t('Insert Paragraph'),
        undo: _t('Undoes the last command'),
        redo: _t('Redoes the last command'),
        tab: _t('Tab'),
        untab: _t('Outdent (when at the start of a line)'),
        bold: _t('Set a bold style'),
        italic: _t('Set a italic style'),
        underline: _t('Set a underline style'),
        strikethrough: _t('Set a strikethrough style'),
        removeFormat: _t('Clean a style'),
        justifyLeft: _t('Set left align'),
        justifyCenter: _t('Set center align'),
        justifyRight: _t('Set right align'),
        justifyFull: _t('Set full align'),
        insertUnorderedList: _t('Toggle unordered list'),
        insertOrderedList: _t('Toggle ordered list'),
        outdent: _t('Outdent current paragraph'),
        indent: _t('Indent current paragraph'),
        formatPara: _t('Change current block\'s format as a paragraph(P tag)'),
        formatH1: _t('Change current block\'s format as H1'),
        formatH2: _t('Change current block\'s format as H2'),
        formatH3: _t('Change current block\'s format as H3'),
        formatH4: _t('Change current block\'s format as H4'),
        formatH5: _t('Change current block\'s format as H5'),
        formatH6: _t('Change current block\'s format as H6'),
        insertHorizontalRule: _t('Insert horizontal rule'),
        'linkDialog.show': _t('Show Link Dialog')
    },
    history: {
        undo: _t('Undo'),
        redo: _t('Redo')
    },
    specialChar: {
        specialChar: _t('SPECIAL CHARACTERS'),
        select: _t('Select Special characters')
    }
};

return $.summernote.lang.odoo;

});
