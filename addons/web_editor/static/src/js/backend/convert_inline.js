/** @odoo-module alias=web_editor.convertInline */
'use strict';

import FieldHtml from 'web_editor.field.html';
import { isBlock, rgbToHex } from '../../../lib/odoo-editor/src/utils/utils';

const SELECTORS_IGNORE = /(^\*$|:hover|:before|:after|:active|:link|::|'|\([^(),]+[,(])/;

/**
 * Returns the css rules which applies on an element, tweaked so that they are
 * browser/mail client ok.
 *
 * @param {DOMElement} a
 * @returns {Object} css property name -> css property value
 */
function getMatchedCSSRules(a) {
    var i, r, k, l;
    var doc = a.ownerDocument;
    var rulesCache = a.ownerDocument._rulesCache || (a.ownerDocument._rulesCache = []);

    if (!rulesCache.length) {
        var sheets = doc.styleSheets;
        for (i = sheets.length-1 ; i >= 0 ; i--) {
            var rules;
            // try...catch because browser may not able to enumerate rules for cross-domain sheets
            try {
                rules = sheets[i].rules || sheets[i].cssRules;
            } catch (e) {
                console.log("Can't read the css rules of: " + sheets[i].href, e);
                continue;
            }
            if (rules) {
                for (r = rules.length-1; r >= 0; r--) {
                    const conditionText = rules[r].conditionText;
                    const minWidthMatch = conditionText && conditionText.match(/\(min-width *: *(\d+)/);
                    const minWidth = minWidthMatch && +(minWidthMatch[1] || '0');
                    if (minWidth && minWidth >= 1200) {
                        // Large min-width media queries should be included.
                        // eg., .container has a default max-width for all
                        // screens.
                        let mediaRules;
                        try {
                            mediaRules = rules[r].rules || rules[r].cssRules;
                        } catch (e) {
                            console.log(`Can't read the css rules of: ${sheets[i].href} (${conditionText})`, e);
                            continue;
                        }
                        if (mediaRules) {
                            for (k = mediaRules.length-1; k >= 0; k--) {
                                var selectorText = mediaRules[k].selectorText;
                                if (selectorText && !SELECTORS_IGNORE.test(selectorText)) {
                                    var st = selectorText.split(/\s*,\s*/);
                                    for (l = 0 ; l < st.length ; l++) {
                                        rulesCache.push({ 'selector': st[l], 'style': mediaRules[k].style });
                                    }
                                }
                            }
                        }
                    }
                    var selectorText = rules[r].selectorText;
                    if (selectorText && !SELECTORS_IGNORE.test(selectorText)) {
                        var st = selectorText.split(/\s*,\s*/);
                        for (l = 0 ; l < st.length ; l++) {
                            rulesCache.push({ 'selector': st[l], 'style': rules[r].style });
                        }
                    }
                }
            }
        }
        rulesCache.reverse();
    }

    var css = [];
    var style;
    a.matches = a.matches || a.webkitMatchesSelector || a.mozMatchesSelector || a.msMatchesSelector || a.oMatchesSelector;
    for (r = 0; r < rulesCache.length; r++) {
        // The top element of a mailing has the class 'o_layout'. Give it the
        // body's styles so they can trickle down.
        if (a.matches(rulesCache[r].selector) || (a.classList.contains('o_layout') && rulesCache[r].selector === 'body')) {
            style = rulesCache[r].style;
            if (style.parentRule) {
                var style_obj = {};
                var len;
                for (k = 0, len = style.length ; k < len ; k++) {
                    if (style[k].indexOf('animation') !== -1) {
                        continue;
                    }
                    style_obj[style[k]] = style[style[k].replace(/-(.)/g, function (a, b) { return b.toUpperCase(); })];
                    if (new RegExp(style[k] + '\s*:[^:;]+!important' ).test(style.cssText)) {
                        style_obj[style[k]] += ' !important';
                    }
                }
                rulesCache[r].style = style = style_obj;
            }
            css.push([rulesCache[r].selector, style]);
        }
    }

    function specificity(selector) {
        // http://www.w3.org/TR/css3-selectors/#specificity
        var a = 0;
        selector = selector.replace(/#[a-z0-9_-]+/gi, function () { a++; return ''; });
        var b = 0;
        selector = selector.replace(/(\.[a-z0-9_-]+)|(\[.*?\])/gi, function () { b++; return ''; });
        var c = 0;
        selector = selector.replace(/(^|\s+|:+)[a-z0-9_-]+/gi, function (a) { if (a.indexOf(':not(')===-1) c++; return ''; });
        return a*100 + b*10 + c;
    }
    css.sort(function (a, b) { return specificity(a[0]) - specificity(b[0]); });
    // Add inline styles at the highest specificity.
    if (a.style.length) {
        const inlineStyles = {};
        for (const styleName of a.style) {
            inlineStyles[styleName] = a.style[styleName];
        }
        css.push([a, inlineStyles]);
    }

    style = {};
    _.each(css, function (v,k) {
        _.each(v[1], function (v,k) {
            if (v && _.isString(v) && k.indexOf('-webkit') === -1 && (!style[k] || style[k].indexOf('important') === -1 || v.indexOf('important') !== -1)) {
                style[k] = v;
            }
        });
    });

    _.each(style, function (v,k) {
        if (v.indexOf('important') !== -1) {
            style[k] = v.slice(0, v.length-11);
        }
    });

    if (style.display === 'block' && !(a.classList && a.classList.contains('btn-block'))) {
        delete style.display;
    }
    if (!style['box-sizing']) {
        style['box-sizing'] = 'border-box'; // This is by default with Bootstrap.
    }

    // The css generates all the attributes separately and not in simplified form.
    // In order to have a better compatibility (outlook for example) we simplify the css tags.
    // e.g. border-left-style: none; border-bottom-s .... will be simplified in border-style = none
    _.each([
        {property: 'margin'},
        {property: 'padding'},
        {property: 'border', propertyEnd: '-style', defaultValue: 'none'},
    ], function (propertyInfo) {
        var p = propertyInfo.property;
        var e = propertyInfo.propertyEnd || '';
        var defVal = propertyInfo.defaultValue || 0;

        if (style[p+'-top'+e] || style[p+'-right'+e] || style[p+'-bottom'+e] || style[p+'-left'+e]) {
            if (style[p+'-top'+e] === style[p+'-right'+e] && style[p+'-top'+e] === style[p+'-bottom'+e] && style[p+'-top'+e] === style[p+'-left'+e]) {
                // keep => property: [top/right/bottom/left value];
                style[p+e] = style[p+'-top'+e];
            }
            else {
                // keep => property: [top value] [right value] [bottom value] [left value];
                style[p+e] = (style[p+'-top'+e] || defVal) + ' ' + (style[p+'-right'+e] || defVal) + ' ' + (style[p+'-bottom'+e] || defVal) + ' ' + (style[p+'-left'+e] || defVal);
                if (style[p+e].indexOf('inherit') !== -1 || style[p+e].indexOf('initial') !== -1) {
                    // keep => property-top: [top value]; property-right: [right value]; property-bottom: [bottom value]; property-left: [left value];
                    delete style[p+e];
                    return;
                }
            }
            delete style[p+'-top'+e];
            delete style[p+'-right'+e];
            delete style[p+'-bottom'+e];
            delete style[p+'-left'+e];
        }
    });

    if (style['border-bottom-left-radius']) {
        style['border-radius'] = style['border-bottom-left-radius'];
        delete style['border-bottom-left-radius'];
        delete style['border-bottom-right-radius'];
        delete style['border-top-left-radius'];
        delete style['border-top-right-radius'];
    }

    // if the border styling is initial we remove it to simplify the css tags for compatibility.
    // Also, since we do not send a css style tag, the initial value of the border is useless.
    _.each(_.keys(style), function (k) {
        if (k.indexOf('border') !== -1 && style[k] === 'initial') {
            delete style[k];
        }
    });

    // text-decoration rule is decomposed in -line, -color and -style. This is
    // however not supported by many browser/mail clients and the editor does
    // not allow to change -color and -style rule anyway
    if (style['text-decoration-line']) {
        style['text-decoration'] = style['text-decoration-line'];
        delete style['text-decoration-line'];
        delete style['text-decoration-color'];
        delete style['text-decoration-style'];
        delete style['text-decoration-thickness'];
    }

    // color and text-align inheritance do not seem to get past <td> elements on
    // some mail clients. TODO: This is hacky as it applies a color/text-align
    // style to all descendants of nodes with a color style. We can probably do
    // this more elegantly.
    if (style.color || style['text-align']) {
        function _styleDescendants(node, styleName) {
            const camelCased = styleName.replace(/-(\w)/g, match => match[1].toUpperCase());
            node.style[camelCased] = style[styleName];
            for (const child of $(node).children()) {
                if (child.style[camelCased] !== style[styleName]) {
                    break;
                }
                _styleDescendants(child, styleName);
            }
        }
        if (style.color) {
            _styleDescendants(a, 'color');
        }
        if (style['text-align']) {
            _styleDescendants(a, 'text-align');
        }
    }

    // flexboxes are not supported in Windows Outlook
    for (const styleName in style) {
        if (styleName.includes('flex') || `${style[styleName]}`.includes('flex')) {
            delete style[styleName];
        }
    }

    return style;
}

/**
 * Converts font icons to images.
 *
 * @param {jQuery} $editable - the element in which the font icons have to be
 *                           converted to images
 */
function fontToImg($editable) {
    var fonts = odoo.__DEBUG__.services["wysiwyg.fonts"];

    $editable.find('.fa').each(function () {
        var $font = $(this);
        var icon, content;
        _.find(fonts.fontIcons, function (font) {
            return _.find(fonts.getCssSelectors(font.parser), function (data) {
                if ($font.is(data.selector.replace(/::?before/g, ''))) {
                    icon = data.names[0].split('-').shift();
                    content = data.css.match(/content:\s*['"]?(.)['"]?/)[1];
                    return true;
                }
            });
        });
        if (content) {
            var color = $font.css('color').replace(/\s/g, '');
            let $backgroundColoredElement = $font;
            let bg, isTransparent;
            do {
                bg = $backgroundColoredElement.css('background-color').replace(/\s/g, '');
                isTransparent = bg === 'transparent' || bg === 'rgba(0,0,0,0)';
                $backgroundColoredElement = $backgroundColoredElement.parent();
            } while (isTransparent && $backgroundColoredElement[0]);
            if (bg === 'rgba(0,0,0,0)' && isTransparent) {
                // default on white rather than black background since opacity
                // is not supported.
                bg = 'rgb(255,255,255)';
            }
            const style = $font.attr('style');
            const width = $font.width();
            const height = $font.height();
            const lineHeight = $font.css('line-height');
            // Compute the padding.
            // First get the dimensions of the icon itself (::before)
            $font.css({height: 'fit-content', width: 'fit-content', 'line-height': 'normal'});
            const hPadding = width && (width - $font.width()) / 2;
            const vPadding = height && (height - $font.height()) / 2;
            let padding = '';
            if (hPadding || vPadding) {
                padding = vPadding ? vPadding + 'px ' : '0 ';
                padding += hPadding ? hPadding + 'px' : '0';
            }
            const $img = $('<img/>').attr({
                width, height,
                src: `/web_editor/font_to_img/${content.charCodeAt(0)}/${window.encodeURI(color)}/${window.encodeURI(bg)}/${Math.max(1, $font.height())}`,
                'data-class': $font.attr('class'),
                'data-style': style,
                class: $font.attr('class').replace(new RegExp('(^|\\s+)' + icon + '(-[^\\s]+)?', 'gi'), ''), // remove inline font-awsome style
                style,
            }).css({
                'box-sizing': 'border-box', // keep the fontawesome's dimensions
                'line-height': lineHeight,
                padding, width: width + 'px', height: height + 'px',
            });
            $font.replaceWith($img);
        } else {
            $font.remove();
        }
    });
}

/*
 * Utility function to apply function over descendants elements
 *
 * This is needed until the following issue of jQuery is solved:
 *  https://github.com./jquery/sizzle/issues/403
 *
 * @param {Element} node The root Element node
 * @param {Function} func The function applied over descendants
 */
function applyOverDescendants(node, func) {
    node = node.firstChild;
    while (node) {
        if (node.nodeType === 1) {
            func(node);
            applyOverDescendants(node, func);
        }
        var $node = $(node);
        if (node.nodeName === 'A' && $node.hasClass('btn') && !$node.children().length && $(node).parents('.o_outlook_hack').length)  {
            node = $(node).parents('.o_outlook_hack')[0];
        }
        else if (node.nodeName === 'IMG' && $node.parent('p').hasClass('o_outlook_hack')) {
            node = $node.parent()[0];
        }
        node = node.nextSibling;
    }
}

const reColMatch = /(^| )col(-[\w\d]+)*( |$)/;
const reOffsetMatch = /(^| )offset(-[\w\d]+)*( |$)/;
function _getColumnSize(column) {
    const colMatch = column.className.match(reColMatch);
    const colOptions = colMatch[2] && colMatch[2].substr(1).split('-');
    const colSize = colOptions && (colOptions.length === 2 ? +colOptions[1] : +colOptions[0]) || 0;
    const offsetMatch = column.className.match(reOffsetMatch);
    const offsetOptions = offsetMatch && offsetMatch[2] && offsetMatch[2].substr(1).split('-');
    const offsetSize = offsetOptions && (offsetOptions.length === 2 ? +offsetOptions[1] : +offsetOptions[0]) || 0;
    return colSize + offsetSize;
}


// Attributes all tables should have in a mailing.
const tableAttributes = {
    cellspacing: 0,
    cellpadding: 0,
    border: 0,
    width: '100%',
    align: 'center',
    role: 'presentation',
};
// Cancel tables default styles.
const tableStyles = {
    'border-collapse': 'collapse',
    'text-align': 'inherit',
    'font-size': 'unset',
    'line-height': 'unset',
};
function _createTable(attributes = []) {
    const $table = $('<table/>');
    $table.attr(tableAttributes);
    $table[0].style.setProperty('width', '100%', 'important');
    for (const attr of attributes) {
        if (!(attr.name === 'width' && attr.value === '100%')) {
            $table.attr(attr.name, attr.value);
        }
    }
    if ($table.hasClass('o_layout')) {
        // The top mailing element inherits the body's font size and line-height
        // and should keep them.
        const layoutStyles = {...tableStyles};
        delete layoutStyles['font-size'];
        delete layoutStyles['line-height'];
        $table.css(layoutStyles);
    } else {
        for (const styleName in tableStyles) {
            if (!('style' in attributes && attributes.style.value.includes(styleName + ':'))) {
                $table.css(styleName, tableStyles[styleName]);
            }
        }
    }
    return $table;
}
function _createColumnGrid() {
    return new Array(12).fill().map(() => $('<td/>'));
}
function _applyColspanToGridElement($gridElement, colspan) {
    $gridElement.attr('colspan', colspan);
    const width = Math.round(+$gridElement.attr('colspan') * 100 / 12) + '%';
    $gridElement.attr('width', width);
    $gridElement.css('width', width);
}

/**
 * Converts bootstrap rows and columns to actual tables.
 *
 * Note: Because of the limited support of media queries in emails, this doesn't
 * support the mixing and matching of column options (e.g., "col-4 col-sm-6" and
 * "col col-4" aren't supported).
 *
 * @param {jQuery} $editable
 */
function bootstrapToTable($editable) {
    // First give all rows in columns a separate container parent.
    $editable.find('.row').filter((i, row) => reColMatch.test(row.parentElement.className)).wrap('<div class="o_fake_table"/>');

    // These containers from the mass mailing masonry snippet require full
    // height contents, which is only possible if the table itself has a set
    // height. We also need to restyle it because of the change in structure.
    $editable.find('.o_masonry_grid_container').css('padding', 0)
    .find('> .o_fake_table').css('height', function() { return $(this).height() });
    for (const masonryRow of $editable.find('.o_masonry_grid_container > .o_fake_table > .row.h-100')) {
        masonryRow.style.removeProperty('height');
        masonryRow.parentElement.style.setProperty('height', '100%');
    }

    // Now convert all containers with rows to tables.
    for (const container of $editable.find('.container:has(.row), .container-fluid:has(.row), .o_fake_table:has(.row)')) {
        const $container = $(container);


        // TABLE
        const $table = _createTable(container.attributes);
        for (const child of [...container.childNodes]) {
            $table.append(child);
        }
        $table.removeClass('container container-fluid o_fake_table');
        if (!$table[0].className) {
            $table.removeAttr('class');
        }
        $container.before($table);
        $container.remove();


        // ROWS
        // First give all siblings of rows a separate row/col parent combo.
        $table.children().filter((i, child) => isBlock(child) && !$(child).hasClass('row')).wrap('<div class="row"><div class="col-12"/></div>');

        const $bootstrapRows = $table.children().filter('.row');
        for (const bootstrapRow of $bootstrapRows) {
            const $bootstrapRow = $(bootstrapRow);
            const $row = $('<tr/>');
            for (const attr of bootstrapRow.attributes) {
                $row.attr(attr.name, attr.value);
            }
            $row.removeClass('row');
            if (!$row[0].className) {
                $row.removeAttr('class');
            }
            for (const child of [...bootstrapRow.childNodes]) {
                $row.append(child);
            }
            $bootstrapRow.before($row);
            $bootstrapRow.remove();


            // COLUMNS
            const $bootstrapColumns = $row.children().filter((i, column) => column.className && column.className.match(reColMatch));

            // 1. Replace generic "col" classes with specific "col-n", computed
            //    by sharing the available space between them.
            const $flexColumns = $bootstrapColumns.filter((i, column) => !/\d/.test(column.className.match(reColMatch)[0] || '0'));
            const colTotalSize = $bootstrapColumns.toArray().map(child => _getColumnSize(child)).reduce((a, b) => a + b);
            const colSize = Math.round((12 - colTotalSize) / $flexColumns.length);
            for (const flexColumn of $flexColumns) {
                flexColumn.classList.remove(flexColumn.className.match(reColMatch)[0].trim());
                flexColumn.classList.add(`col-${colSize}`);
            }

            // 2. Create and fill up the row(s) with grid(s).
            let grid = _createColumnGrid();
            let gridIndex = 0;
            let $currentRow = $($row[0].cloneNode());
            $row.after($currentRow);
            let $currentCol;
            let columnIndex = 0;
            for (const bootstrapColumn of $bootstrapColumns) {
                const columnSize = _getColumnSize(bootstrapColumn);
                if (gridIndex + columnSize < 12) {
                    $currentCol = grid[gridIndex];
                    _applyColspanToGridElement($currentCol, columnSize);
                    if (columnIndex === $bootstrapColumns.length - 1) {
                        // We handled all the columns but there is still space
                        // in the row. Insert the columns and fill the row.
                        grid[gridIndex].attr('colspan', 12 - gridIndex);
                        $currentRow.append(...grid.filter(td => td.attr('colspan')));
                    }
                    gridIndex += columnSize;
                } else if (gridIndex + columnSize === 12) {
                    // Finish the row.
                    $currentCol = grid[gridIndex];
                    _applyColspanToGridElement($currentCol, columnSize);
                    $currentRow.append(...grid.filter(td => td.attr('colspan')));
                    if (columnIndex !== $bootstrapColumns.length - 1) {
                        // The row was filled before we handled all of its
                        // columns. Create a new one and start again from there.
                        const $previousRow = $currentRow;
                        $currentRow = $($currentRow[0].cloneNode());
                        $previousRow.after($currentRow);
                        grid = _createColumnGrid();
                        gridIndex = 0;
                    }
                } else {
                    // Fill the row with what was in the grid before it
                    // overflowed.
                    _applyColspanToGridElement(grid[gridIndex], 12 - gridIndex);
                    $currentRow.append(...grid.filter(td => td.attr('colspan')));
                    // Start a new row that starts with the current col.
                    const $previousRow = $currentRow;
                    $currentRow = $($currentRow[0].cloneNode());
                    $previousRow.after($currentRow);
                    grid = _createColumnGrid();
                    $currentCol = grid[0];
                    _applyColspanToGridElement($currentCol, columnSize);
                    gridIndex = columnSize;
                }
                if ($currentCol) {
                    for (const attr of bootstrapColumn.attributes) {
                        if (attr.name !== 'colspan') {
                            $currentCol.attr(attr.name, attr.value);
                        }
                    }
                    const colMatch = bootstrapColumn.className.match(reColMatch);
                    $currentCol.removeClass(colMatch[0]);
                    if (!$currentCol[0].className) {
                        $currentCol.removeAttr('class');
                    }
                    for (const child of [...bootstrapColumn.childNodes]) {
                        $currentCol.append(child);
                    }
                    // Adapt width to colspan.
                    _applyColspanToGridElement($currentCol, +$currentCol.attr('colspan'));
                }
                columnIndex++;
            }
            $row.remove(); // $row was cloned and inserted already
        }
    }
}

function cardToTable($editable) {
    for (const card of $editable.find('.card')) {
        const $card = $(card);
        // Table
        const $table = _createTable(card.attributes);
        for (const child of [...card.childNodes]) {
            if (child.nodeType === Node.TEXT_NODE) {
                $table.append(child);
            } else {
                const $row = $('<tr/>');
                const $col = $('<td/>');
                if (child.nodeName === 'IMG') {
                    $col.append(child);
                } else {
                    for (const attr of child.attributes) {
                        $col.attr(attr.name, attr.value);
                    }
                    for (const descendant of [...child.childNodes]) {
                        $col.append(descendant);
                    }
                    $(child).remove();
                }
                $row.append($col);
                $table.append($row);
            }
        }
        $card.before($table);
        $card.remove();
    }
}

function listGroupToTable($editable) {
    for (const listGroup of $editable.find('.list-group')) {
        const $listGroup = $(listGroup);
        // Table
        let $table;
        if ($listGroup.find('.list-group-item').length) {
            $table = _createTable(listGroup.attributes);
        } else {
            $table = $(listGroup.cloneNode());
            for (const attr of $listGroup.attributes) {
                $table.attr(attr.name, attr.value);
            }
        }
        for (const child of [...listGroup.childNodes]) {
            const $child = $(child);
            if ($child.hasClass('list-group-item')) {
                // List groups are <ul>s that render like tables. Their
                // li.list-group-item children should translate to tr > td.
                const $row = $('<tr/>');
                const $col = $('<td/>');
                for (const attr of child.attributes) {
                    $col.attr(attr.name, attr.value);
                }
                for (const descendant of [...child.childNodes]) {
                    $col.append(descendant);
                }
                $col.removeClass('list-group-item');
                $row.append($col);
                $table.append($row);
                $(child).remove();
            } else {
                $table.append(child);
            }
        }
        $table.removeClass('list-group');
        if ($listGroup.is('td')) {
            $listGroup.append($table);
            $listGroup.removeClass('list-group');
        } else {
            $listGroup.before($table);
            $listGroup.remove();
        }
    }
}

function addTables($editable) {
    for (const snippet of $editable.find('.o_mail_snippet_general, .o_layout')) {
        // Convert all snippets and the mailing itself into table > tr > td
        const $table = _createTable(snippet.attributes);
        const $row = $('<tr/>');
        const $col = $('<td/>');
        $row.append($col);
        $table.append($row);
        for (const child of [...snippet.childNodes]) {
            $col.append(child);
        }
        $(snippet).before($table);
        $(snippet).remove();

        // If snippet doesn't have a table as child, wrap its contents in one.
        if (!$col.children().filter('table')) {
            const $tableB = _createTable();
            $tableB[0].style.width
            const $rowB = $('<tr/>');
            const $colB = $('<td/>');
            $rowB.append($colB);
            $tableB.append($rowB);
            for (const child of [...$table[0].childNodes]) {
                $colB.append(child);
            }
            $col.append($tableB);
        }
    }
}

const rePadding = /(\d+)/;
function formatTables($editable) {
    for (const table of $editable.find('table.o_mail_snippet_general, .o_mail_snippet_general table')) {
        const $table = $(table);
        const tablePaddingTop = +$table.css('padding-top').match(rePadding)[1];
        const tablePaddingRight = +$table.css('padding-right').match(rePadding)[1];
        const tablePaddingBottom = +$table.css('padding-bottom').match(rePadding)[1];
        const tablePaddingLeft = +$table.css('padding-left').match(rePadding)[1];
        const $columns = $table.find('td').filter((i, td) => $(td).closest('table').is($table));
        let columnIndex = 0;
        for (const column of $columns) {
            const $column = $(column);
            if ($column.css('padding')) {
                const columnPaddingRight = +$column.css('padding-right').match(rePadding)[1];
                const columnPaddingLeft = +$column.css('padding-left').match(rePadding)[1];
                $column.css({
                    'padding-right': columnPaddingRight + tablePaddingRight,
                    'padding-left': columnPaddingLeft + tablePaddingLeft,
                });
                if (!columnIndex) {
                    const columnPaddingTop = +$column.css('padding-top').match(rePadding)[1];
                    $column.css({
                        'padding-top': columnPaddingTop + tablePaddingTop,
                    });
                }
                if (columnIndex === $columns.length - 1) {
                    const columnPaddingBottom = +$column.css('padding-bottom').match(rePadding)[1];
                    $column.css({
                        'padding-bottom': columnPaddingBottom + tablePaddingBottom,
                    });
                }
            }
            columnIndex += 1;
        }
        $table.css('padding', '');
    }
    // Ensure a tbody in every table and cancel its default style.
    for (const table of $editable.find('table:not(:has(tbody))')) {
        $(table).contents().wrap('<tbody style="vertical-align: top"/>');
    }
    // Children will only take 100% height if the parent has a height property.
    for (const node of $editable.find('*').filter((i, n) => (
        n.style && n.style.getPropertyValue('height') === '100%' && (
            !n.parentElement.style.getPropertyValue('height') ||
            n.parentElement.style.getPropertyValue('height').includes('%'))
    ))) {
        node.parentElement.style.setProperty('height', '0');
    }
}

/**
 * Converts css style to inline style (leave the classes on elements but forces
 * the style they give as inline style).
 *
 * @param {jQuery} $editable
 */
function classToStyle($editable) {
    applyOverDescendants($editable[0], function (node) {
        var $target = $(node);
        var css = getMatchedCSSRules(node);
        // Flexbox
        for (const styleName in node.style) {
            if (styleName.includes('flex') || `${node.style[styleName]}`.includes('flex')) {
                node.style[styleName] = '';
            }
        }

        // Do not apply css that would override inline styles (which are prioritary).
        var style = $target.attr('style') || '';
        _.each(css, function (v,k) {
            if (!(new RegExp('(^|;)\\s*' + k).test(style))) {
                style = k+':'+v+';'+style;
            }
        });
        if (_.isEmpty(style)) {
            $target.removeAttr('style');
        } else {
            $target.attr('style', style);
        }
        if ($target.get(0).style.width) {
            $target.attr('width', $target.css('width')); // Widths need to be applied as attributes as well.
        }

        // Media list images should not have an inline height
        if (node.nodeName === 'IMG' && $target.hasClass('s_media_list_img')) {
            $target.css('height', '');
        }
        // Apple Mail
        if (node.nodeName === 'TD' && !node.childNodes.length) {
            $(node).html('&nbsp;');
        }

        // Outlook
        if (node.nodeName === 'A' && $target.hasClass('btn') && !$target.hasClass('btn-link') && !$target.children().length) {
            $target.prepend(`<!--[if mso]><i style="letter-spacing: 25px; mso-font-width: -100%; mso-text-raise: 30pt;">&nbsp;</i><![endif]-->`);
            $target.append(`<!--[if mso]><i style="letter-spacing: 25px; mso-font-width: -100%;">&nbsp;</i><![endif]-->`);
        }
        else if (node.nodeName === 'IMG' && $target.is('.mx-auto.d-block')) {
            $target.wrap('<p class="o_outlook_hack" style="text-align:center;margin:0"/>');
        }
    });
}

// Note: ignores rgba colors, which are not supported in Outlook.
function normalizeColors($editable) {
    for (const node of $editable.find('[style*="rgb"]')) {
        const rgbMatch = node.getAttribute('style').match(/rgb?\(([\d\.]*,?\s?){3,4}\)/g);
        for (const rgb of rgbMatch || []) {
            node.setAttribute('style', node.getAttribute('style').replace(rgb, rgbToHex(rgb)));
        }
    }
}

/**
 * Converts all css values that use the rem unit to px.
 *
 * @param {JQuery} $editable
 */
function normalizeRem($editable) {
    const rootFontSizeProperty = $editable.closest('html').css('font-size');
    const rootFontSize = parseFloat(rootFontSizeProperty.replace(/[^\d\.]/g, ''));
    for (const node of $editable.find('[style*="rem"]')) {
        const remMatch = node.getAttribute('style').match(/[\d\.]+\s*rem/g);
        for (const rem of remMatch || []) {
            const remValue = parseFloat(rem.replace(/[^\d\.]/g, ''));
            node.setAttribute('style', node.getAttribute('style').replace(rem, remValue * rootFontSize + 'px'));
        }
    }
}

/**
 * Converts css display for attachment link to real image.
 * Without this post process, the display depends on the css and the picture
 * does not appear when we use the html without css (to send by email for e.g.)
 *
 * @param {jQuery} $editable
 */
function attachmentThumbnailToLinkImg($editable) {
    $editable.find('a[href*="/web/content/"][data-mimetype]').filter(':empty, :containsExact( )').each(function () {
        var $link = $(this);
        var $img = $('<img/>')
            .attr('src', $link.css('background-image').replace(/(^url\(['"])|(['"]\)$)/g, ''))
            .css('height', Math.max(1, $link.height()) + 'px')
            .css('width', Math.max(1, $link.width()) + 'px');
        $link.prepend($img);
    });
}


//--------------------------------------------------------------------------
//--------------------------------------------------------------------------


FieldHtml.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    commitChanges: function () {
        if (this.nodeOptions['style-inline'] && this.mode === "edit") {
            this._toInline();
        }
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Converts CSS dependencies to CSS-independent HTML.
     * - CSS display for attachment link -> real image
     * - Font icons -> images
     * - CSS styles -> inline styles
     *
     * @private
     */
    _toInline: function () {
        var $editable = this.wysiwyg.getEditable();
        var html = this.wysiwyg.getValue();
        const $odooEditor = $editable.closest('.odoo-editor');
        // Remove temporarily the class so that css editing will not be converted.
        $odooEditor.removeClass('odoo-editor');
        $editable.html(html);

        attachmentThumbnailToLinkImg($editable);
        fontToImg($editable);
        classToStyle($editable);
        bootstrapToTable($editable);
        cardToTable($editable);
        listGroupToTable($editable);
        addTables($editable);
        formatTables($editable);
        normalizeColors($editable);
        normalizeRem($editable);

        // fix outlook image rendering bug
        _.each(['width', 'height'], function(attribute) {
            $editable.find('img').attr(attribute, function(){
                return $(this)[attribute]();
            }).css(attribute, function(){
                return $(this).get(0).style[attribute] || attribute === 'width' ? $(this)[attribute]() + 'px' : '';
            });
        });
        $odooEditor.addClass('odoo-editor');

        this.wysiwyg.setValue($editable.html(), {
            notifyChange: false,
        });
    },
});

export default {
    fontToImg: fontToImg,
    bootstrapToTable: bootstrapToTable,
    cardToTable: cardToTable,
    listGroupToTable: listGroupToTable,
    addTables: addTables,
    formatTables: formatTables,
    classToStyle: classToStyle,
    normalizeColors: normalizeColors,
    normalizeRem: normalizeRem,
    attachmentThumbnailToLinkImg: attachmentThumbnailToLinkImg,
};
